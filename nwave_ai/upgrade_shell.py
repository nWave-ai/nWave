"""Read installation snapshots, interpret a pure cleanup plan, replace files atomically."""

from __future__ import annotations

import base64
import ctypes
import errno
import hashlib
import importlib.util
import json
import os
import re
import shlex
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

from nwave_ai import upgrade as core
from nwave_ai.platform.locations import Failure


if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class Replaced:
    pass


@dataclass(frozen=True)
class Removed:
    pass


@dataclass(frozen=True)
class Changed:
    current_bytes: bytes


@dataclass(frozen=True)
class Written:
    pass


@dataclass(frozen=True)
class Renamed:
    pass


@dataclass(frozen=True)
class Occupied:
    pass


@dataclass(frozen=True)
class FileSystemPort:
    list_tree: Callable[[str], tuple[core.Node, ...]]
    read_bytes: Callable[[str], bytes]
    resolve: Callable[[str], str]
    remove_file: Callable[[str], None]
    remove_dir: Callable[[str], None]
    replace_if_unchanged: Callable[[str, bytes, bytes], Replaced | Changed]
    remove_if_unchanged: Callable[[str, bytes], Removed | Changed]
    write_new: Callable[[str, bytes], Written | Occupied]
    rename_noreplace: Callable[[str, str], Renamed | Occupied]


def _read_regular(path: str) -> bytes:
    """Return the exact bytes of a regular file; a symlink is never followed.

    POSIX binds the no-follow check to the open itself through ``O_NOFOLLOW``.
    A platform whose ``os`` module lacks it (Windows) refuses non-regular paths
    from an ``lstat`` taken before the open, then rechecks the opened
    descriptor. That pair leaves a race window a same-account writer could use;
    the POSIX open does not. ``O_BINARY`` keeps CRLF bytes unchanged.
    """
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        descriptor = os.open(path, flags | os.O_NOFOLLOW)
    else:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            raise ValueError(f"{path}: not a regular file")
        descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError(f"{path}: not a regular file")
        return stream.read()


def _list_tree(path: str) -> tuple[core.Node, ...]:
    root = Path(path)
    if not os.path.lexists(root):
        return ()
    built = {}
    pending = [(root, False)]
    while pending:
        current, visited = pending.pop()
        info = current.lstat()
        name = str(current)
        if stat.S_ISLNK(info.st_mode):
            built[name] = core.SymlinkLeaf(name, str(current.readlink()))
        elif stat.S_ISDIR(info.st_mode):
            if not visited:
                children = sorted(current.iterdir())
                pending.append((current, True))
                pending.extend((child, False) for child in reversed(children))
            else:
                built[name] = core.Dir(
                    name,
                    tuple(built[str(child)] for child in sorted(current.iterdir())),
                )
        elif stat.S_ISREG(info.st_mode):
            data = _read_regular(str(current))
            if current.parent.name == "__pycache__" and current.suffix == ".pyc":
                try:
                    source = Path(importlib.util.source_from_cache(str(current)))
                except ValueError:
                    source = current.parent.parent / (current.stem + ".py")
                try:
                    source_hash = (
                        importlib.util.source_hash(_read_regular(str(source)))
                        if source.is_file() and not source.is_symlink()
                        else None
                    )
                except OSError:
                    source_hash = None
                header = core.SourceHash(b"")
                if len(data) >= 16 and data[2:4] == b"\r\n":
                    flags = int.from_bytes(data[4:8], "little")
                    if flags in (1, 3):
                        header = core.SourceHash(data[8:16])
                    elif flags == 0:
                        header = core.SizeMtime(
                            int.from_bytes(data[12:16], "little"),
                            int.from_bytes(data[8:12], "little"),
                        )
                built[name] = core.PycacheLeaf(
                    name,
                    str(source),
                    header,
                    source_hash,
                    hashlib.md5(data).hexdigest(),
                )
            else:
                built[name] = core.FileLeaf(
                    name,
                    hashlib.sha256(data).hexdigest(),
                    info.st_size,
                    info.st_mtime_ns,
                    hashlib.md5(data).hexdigest(),
                )
        else:
            # A socket/device/FIFO is never read or removed as a regular artifact.
            built[name] = core.SymlinkLeaf(name, "<non-regular artifact>")
    return (built[str(root)],)


def _set_descriptor_mode(descriptor: int, path: str, mode: int) -> None:
    """Apply mode to the open temporary; by name where os.fchmod is absent."""
    if hasattr(os, "fchmod"):
        os.fchmod(descriptor, mode)
    else:
        Path(path).chmod(mode)


def _replace_if_unchanged(
    path: str, read_bytes: bytes, new_bytes: bytes
) -> Replaced | Changed:
    target = Path(path)
    descriptor, temporary = tempfile.mkstemp(
        prefix="." + target.name + ".", dir=target.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            _set_descriptor_mode(
                descriptor, temporary, stat.S_IMODE(target.stat().st_mode)
            )
            stream.write(new_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            current = target.read_bytes()
        except FileNotFoundError:
            return Changed(b"")
        if current != read_bytes:
            return Changed(current)
        Path(temporary).replace(target)
        _sync_parent(path)
        return Replaced()
    finally:
        if os.path.lexists(temporary):
            Path(temporary).unlink()


def _remove_if_unchanged(path: str, read_bytes: bytes) -> Removed | Changed:
    target = Path(path)
    try:
        current = _read_regular(path)
    except FileNotFoundError:
        return Changed(b"")
    if current != read_bytes or target.is_symlink():
        return Changed(current)
    target.unlink()
    _sync_parent(path)
    return Removed()


def _sync_parent(path: str) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rename_noreplace(source: str, destination: str) -> Renamed | Occupied:
    if os.name == "nt":
        try:
            Path(source).rename(destination)
        except FileExistsError:
            return Occupied()
        except OSError:
            if os.path.lexists(destination):
                return Occupied()
            raise
        return Renamed()
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform.startswith("linux"):
        rename = getattr(library, "renameat2", None)
        if rename is None:
            return Occupied()
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        result = rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    elif sys.platform == "darwin":
        rename = getattr(library, "renamex_np", None)
        if rename is None:
            return Occupied()
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(os.fsencode(source), os.fsencode(destination), 4)
    else:
        return Occupied()
    if result != 0:
        failure = ctypes.get_errno()
        if failure in (
            errno.EEXIST,
            errno.ENOTEMPTY,
            errno.ENOSYS,
            errno.ENOTSUP,
            errno.EINVAL,
        ):
            return Occupied()
        raise OSError(failure, os.strerror(failure), destination)
    _sync_parent(destination)
    if Path(source).parent != Path(destination).parent:
        _sync_parent(source)
    return Renamed()


def _write_new(path: str, data: bytes) -> Written | Occupied:
    descriptor, temporary = tempfile.mkstemp(
        prefix="." + Path(path).name + ".", dir=Path(path).parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        result = _rename_noreplace(temporary, path)
        return Written() if isinstance(result, Renamed) else Occupied()
    finally:
        if os.path.lexists(temporary):
            Path(temporary).unlink()


def real_port() -> FileSystemPort:
    return FileSystemPort(
        _list_tree,
        _read_regular,
        lambda path: str(Path(path).resolve()),
        lambda path: Path(path).unlink(),
        lambda path: Path(path).rmdir(),
        _replace_if_unchanged,
        _remove_if_unchanged,
        _write_new,
        _rename_noreplace,
    )


def _read(fs: FileSystemPort, path: str) -> bytes | None:
    try:
        return fs.read_bytes(path)
    except FileNotFoundError:
        return None


def _json(data: bytes | None) -> object | None:
    try:
        return json.loads(data) if data is not None else None
    except (ValueError, UnicodeError):
        return None


def _actual_config(fs: FileSystemPort, path: str) -> object | None:
    if Path(path).is_symlink():
        return None
    try:
        return _json(fs.read_bytes(path))
    except OSError:
        return None


def _safe_path(path: object, directory: str) -> str | None:
    if not isinstance(path, str) or not Path(path).is_absolute():
        return None
    normalized = os.path.normpath(path)
    return normalized if normalized.startswith(directory.rstrip("/") + "/") else None


def _has_link_ancestor(path: str, home: str) -> bool:
    current = Path(path).parent
    boundary = Path(home)
    while current not in (boundary, current.parent):
        if current.is_symlink():
            return True
        current = current.parent
    return False


@dataclass(frozen=True)
class DocumentSnapshot:
    document: core.SettingsDocument
    read_bytes: bytes
    raw: dict


def _entries(path: str, raw: dict, legacy: dict) -> tuple[core.HookEntry, ...]:
    legacy_marker = ".".join(legacy["hook_marker_parts"])
    hooks = raw.get("hooks", raw if "preToolUse" in raw else {})
    if not isinstance(hooks, dict):
        raise ValueError("hooks must be an event-keyed object")
    entries = []
    counts = {}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise ValueError(f"hook event {event} must hold a list")
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError(f"hook event {event} has a non-object entry")
            matcher = group.get("matcher", "")
            children = group.get("hooks", [group])
            if not isinstance(children, list):
                raise ValueError(f"hook event {event} has invalid hooks")
            for child in children:
                if not isinstance(child, dict):
                    raise ValueError(f"hook event {event} has a non-object command")
                key = (event, matcher)
                index = counts.get(key, 0)
                counts[key] = index + 1
                command = child.get("command", child.get("bash", ""))
                if isinstance(command, str) and any(
                    marker in command
                    for marker in (*legacy["hook_markers"], legacy_marker)
                ):
                    entries.append(
                        core.HookEntry(path, event, matcher, index, command, child)
                    )
    return tuple(entries)


def _settings(path: str, fs: FileSystemPort, legacy: dict) -> DocumentSnapshot | None:
    resolved = fs.resolve(path)
    data = _read(fs, resolved)
    if data is None:
        return None
    raw = _json(data)
    if not isinstance(raw, dict):
        raise ValueError(
            f"{path}: corrupt settings JSON; repair the file and rerun the upgrade"
        )
    try:
        entries = _entries(path, raw, legacy)
    except ValueError as error:
        raise ValueError(
            f"{path}: corrupt settings: {error}; repair the file and rerun"
        ) from error
    environment = raw.get("env", {})
    path_value = environment.get("PATH", "") if isinstance(environment, dict) else ""
    segments = (
        tuple(path_value.split(os.pathsep))
        if isinstance(path_value, str) and path_value
        else ()
    )
    return DocumentSnapshot(
        core.SettingsDocument(path, resolved, entries, segments), data, raw
    )


def _render_settings(
    snapshot: DocumentSnapshot,
    removals: tuple[core.Removal, ...],
    legacy: dict,
) -> bytes:
    path = snapshot.document.path
    drops = {
        (r.event, r.matcher, r.index)
        for r in removals
        if isinstance(r, core.DropEntry) and r.file == path
    }
    segments = {
        r.segment
        for r in removals
        if isinstance(r, core.DropPathSegment) and r.file == path
    }
    raw = dict(snapshot.raw)
    # The pinned release wrote its own settings env keys; the current release
    # writes only what a fresh install writes, so the upgrade drops the old
    # ones outright.
    dropped_env_keys = {
        key
        for key in legacy.get("settings_env_keys", ())
        if isinstance(raw.get("env"), dict) and key in raw["env"]
    }
    for key in dropped_env_keys:
        environment = dict(raw["env"])
        environment.pop(key, None)
        if environment:
            raw["env"] = environment
        else:
            raw.pop("env")
    if not drops and not segments and not dropped_env_keys:
        return snapshot.read_bytes
    hooks = raw.get("hooks", raw if "preToolUse" in raw else {})
    changed_hooks = {}
    counts = {}
    for event, groups in hooks.items():
        retained = []
        for group in groups:
            matcher = group.get("matcher", "")
            children = group.get("hooks", [group])
            kept = []
            for child in children:
                key = (event, matcher)
                index = counts.get(key, 0)
                counts[key] = index + 1
                if (event, matcher, index) not in drops:
                    kept.append(child)
            if len(kept) == len(children):
                retained.append(group)
            elif kept:
                retained.append({**group, "hooks": kept} if "hooks" in group else group)
        changed_hooks[event] = retained
    if "hooks" in raw:
        raw["hooks"] = changed_hooks
    else:
        raw.update(changed_hooks)
    if segments and "PATH" not in dropped_env_keys:
        environment = dict(raw.get("env", {}))
        environment["PATH"] = os.pathsep.join(
            s for s in snapshot.document.path_segments if s not in segments
        )
        raw["env"] = environment
    return (json.dumps(raw, indent=2) + "\n").encode()


_HOST_NAMES = ("claude", "codex", "cursor", "copilot", "opencode", "omp")


def cursor_config_dir(home: Path) -> Path:
    """Cursor configuration directory: CURSOR_HOME when set, else <home>/.cursor."""
    from scripts.shared import install_paths

    override = install_paths.env_or_none("CURSOR_HOME")
    return Path(override) if override else home / ".cursor"


def copilot_config_dir(home: Path) -> Path:
    """Copilot CLI configuration directory: COPILOT_HOME when set, else <home>/.copilot."""
    from scripts.shared import install_paths

    override = install_paths.env_or_none("COPILOT_HOME")
    return Path(override) if override else home / ".copilot"


def selected_hosts(home: str) -> tuple[tuple[str, str], ...] | Failure[str]:
    """Capture the public profile selections once, without reading an artifact."""
    from nwave_ai.platform.locations import NWaveLocations
    from scripts.shared import install_paths

    result = NWaveLocations.resolve(
        home=Path(home),
        repo_root=Path(home),
        agents_home_override=install_paths.env_or_none("NWAVE_AGENTS_HOME"),
        claude_config_override=install_paths.env_or_none("CLAUDE_CONFIG_DIR"),
        codex_config_override=install_paths.env_or_none("CODEX_HOME"),
    )
    if isinstance(result, Failure):
        return result
    locations = result.unwrap()
    roots = (
        locations.claude_config_dir,
        locations.codex_config_dir,
        cursor_config_dir(Path(home)),
        copilot_config_dir(Path(home)),
        locations.agents_home / ".config" / "opencode",
        install_paths.omp_agent_dir(),
    )
    return tuple(
        (host, str(Path(root).absolute()))
        for host, root in zip(_HOST_NAMES, roots, strict=True)
    )


def _snapshot(
    home: str,
    fs: FileSystemPort,
    legacy: dict,
    *,
    hosts: tuple[tuple[str, str], ...],
) -> tuple[
    tuple[core.Node, ...],
    tuple[DocumentSnapshot, ...],
    tuple[core.Receipt, ...],
    dict[str, tuple[bytes, dict]],
    tuple[core.Reservation, ...],
]:
    legacy_marker = ".".join(legacy["hook_marker_parts"])
    roots: set[str] = set()
    receipts: list[core.Receipt] = []
    documents: list[DocumentSnapshot] = []
    manifests = {}
    runtime_trees: dict[str, str] = {}

    def include(path: str, boundary: str) -> None:
        if not _has_link_ancestor(path, boundary):
            roots.add(path)

    selected = dict(hosts)
    for relative in legacy["extra_candidates"]:
        location = next(
            (
                (name, prefix)
                for name, prefix in zip(_HOST_NAMES, legacy["hosts"], strict=True)
                if Path(relative).is_relative_to(prefix)
            ),
            None,
        )
        if location is None:
            path, boundary = str(Path(home) / relative), home
        else:
            name, prefix = location
            if name not in selected:
                continue
            boundary = selected[name]
            path = str(Path(boundary) / Path(relative).relative_to(prefix))
        include(path, boundary)
        if Path(relative).name == Path(legacy["library"]).name:
            runtime_trees[path] = boundary
    for host in dict.fromkeys(root for _, root in hosts):
        library = str(Path(host) / legacy["library"])
        include(library, host)
        runtime_trees[library] = host
        include(str(Path(host) / "bin"), host)
        for name in legacy["scripts"]:
            include(str(Path(host) / "scripts" / name), host)
        for key in ("opencode_plugin", "omp_plugin", "copilot_file"):
            include(str(Path(host) / legacy[key]), host)
        for filename in ("settings.json", "settings.local.json", "hooks.json"):
            path = str(Path(host) / filename)
            if not _has_link_ancestor(path, host):
                snapshot = _settings(path, fs, legacy)
                if snapshot:
                    documents.append(snapshot)
        receipt_paths = (
            str(Path(host) / legacy["receipt"]),
            str(Path(host) / "extensions" / legacy["receipt"]),
        )
        for receipt_path in receipt_paths:
            include(receipt_path, host)
            if _has_link_ancestor(receipt_path, host):
                continue
            if Path(receipt_path).is_symlink() or (
                os.path.lexists(receipt_path) and not Path(receipt_path).is_file()
            ):
                receipts.append(
                    core.UnwitnessedReceipt(
                        receipt_path, "receipt is not a regular file"
                    )
                )
                continue
            data = _read(fs, receipt_path)
            raw = _json(data)
            if data is None:
                continue
            if not isinstance(raw, dict):
                receipts.append(
                    core.UnwitnessedReceipt(
                        receipt_path, "receipt is not a JSON object"
                    )
                )
                continue
            common = {"hooks_file", "python_path", "pythonpath"}
            if set(raw) in (common, common | {"event"}) and all(
                isinstance(raw[k], str) for k in raw
            ):
                hooks_file = _safe_path(raw["hooks_file"], host)
                if hooks_file is None or _has_link_ancestor(hooks_file, host):
                    receipts.append(
                        core.UnwitnessedReceipt(
                            receipt_path,
                            "receipt names a path outside its host or below a symlink",
                        )
                    )
                    continue
                python, lib = raw["python_path"], raw["pythonpath"]
                if not python or not lib:
                    receipts.append(
                        core.UnwitnessedReceipt(
                            receipt_path, "receipt interpreter or library path is empty"
                        )
                    )
                    continue
                if not any(
                    snapshot.document.path == hooks_file for snapshot in documents
                ):
                    snapshot = _settings(hooks_file, fs, legacy)
                    if snapshot is not None:
                        documents.append(snapshot)
                if "event" in raw:
                    quoted = _cursor_build_hook_entry(python, lib, legacy_marker)
                    unquoted = {
                        **quoted,
                        "command": f"PYTHONPATH={lib} {python} -m {legacy['hook_marker']} pre-tool-use",
                    }
                    forms = (quoted, unquoted)
                    receipts.append(
                        core.CursorReceipt(
                            receipt_path, hooks_file, python, lib, raw["event"], forms
                        )
                    )
                else:
                    launcher_path = str(Path(host) / legacy["codex_v1_launcher_name"])
                    include(launcher_path, host)
                    direct = _codex_build_hook_entry(python, lib, legacy_marker)[
                        "hooks"
                    ][0]["command"]
                    launcher_command = shlex.join(
                        [python, launcher_path, "pre-tool-use"]
                    )
                    sources = (
                        _codex_launcher_source(python, lib, legacy_marker),
                        _codex_v1_launcher_source(python, lib, legacy_marker),
                    )
                    receipts.append(
                        core.CodexReceipt(
                            receipt_path,
                            hooks_file,
                            python,
                            lib,
                            (direct, launcher_command),
                            launcher_path,
                            sources,
                        )
                    )
            elif set(raw) == {"hook_file", "python_path", "pythonpath"} and all(
                isinstance(v, str) for v in raw.values()
            ):
                path = _safe_path(raw["hook_file"], host)
                if path is None or _has_link_ancestor(path, host):
                    receipts.append(
                        core.UnwitnessedReceipt(
                            receipt_path,
                            "receipt names a path outside its host or below a symlink",
                        )
                    )
                    continue
                include(path, host)
                python, lib = raw["python_path"], raw["pythonpath"]
                rendered = _copilot_build_hook_config(python, lib, legacy_marker)
                receipts.append(
                    core.CopilotReceipt(
                        receipt_path,
                        path,
                        python,
                        lib,
                        rendered,
                        _actual_config(fs, path),
                    )
                )
            elif set(raw) == {"shim_file", "version", "sha256"} and all(
                isinstance(v, str) for v in raw.values()
            ):
                path = _safe_path(raw["shim_file"], host)
                if path is None or _has_link_ancestor(path, host):
                    receipts.append(
                        core.UnwitnessedReceipt(
                            receipt_path,
                            "receipt names a path outside its host or below a symlink",
                        )
                    )
                else:
                    include(path, host)
                    receipts.append(
                        core.OpencodeReceipt(
                            receipt_path, path, raw["version"], raw["sha256"]
                        )
                    )
            elif (
                set(raw) == {"installed_extensions", "sha256"}
                and isinstance(raw["installed_extensions"], list)
                and isinstance(raw["sha256"], str)
                and len(raw["installed_extensions"]) == 1
                and all(
                    isinstance(n, str) and Path(n).name == n and n not in (".", "..")
                    for n in raw["installed_extensions"]
                )
            ):
                files = tuple(
                    (str(Path(receipt_path).parent / n), raw["sha256"])
                    for n in raw["installed_extensions"]
                )
                for path, _ in files:
                    include(path, host)
                receipts.append(core.OmpReceipt(receipt_path, files))
            else:
                receipts.append(
                    core.UnwitnessedReceipt(
                        receipt_path,
                        "receipt fields do not match a declared plugin record",
                    )
                )
        manifest_path = str(Path(host) / legacy["scripts_manifest"])
        if not _has_link_ancestor(manifest_path, host):
            if Path(manifest_path).is_symlink() or (
                os.path.lexists(manifest_path) and not Path(manifest_path).is_file()
            ):
                include(manifest_path, host)
                receipts.append(
                    core.UnwitnessedReceipt(
                        manifest_path, "scripts receipt is not a regular file"
                    )
                )
                continue
            data = _read(fs, manifest_path)
            raw = _json(data)
            if data is not None and not isinstance(raw, dict):
                include(manifest_path, host)
                receipts.append(
                    core.UnwitnessedReceipt(
                        manifest_path, "scripts receipt is not a JSON object"
                    )
                )
            elif isinstance(raw, dict) and legacy["scripts_key"] in raw:
                members = raw[legacy["scripts_key"]]
                if isinstance(members, list) and all(
                    isinstance(n, str) and Path(n).name == n and n not in (".", "..")
                    for n in members
                ):
                    files = tuple(str(Path(manifest_path).parent / n) for n in members)
                    for path in files:
                        include(path, host)
                    receipts.append(
                        core.ScriptsKey(manifest_path, legacy["scripts_key"], files)
                    )
                    manifests[manifest_path] = (data, raw)
                else:
                    include(manifest_path, host)
                    receipts.append(
                        core.UnwitnessedReceipt(
                            manifest_path,
                            "scripts receipt contains an invalid or unsafe member list",
                        )
                    )
    for root, boundary in runtime_trees.items():
        include(root + core.RESERVED_SUFFIX, boundary)
        include(root + core.CONTROL_SUFFIX, boundary)
    # Deduplicate nested roots: each candidate is inspected and reported once.
    selected = tuple(
        root
        for root in sorted(roots)
        if not any(root.startswith(parent + "/") for parent in roots if parent != root)
    )
    tree = tuple(node for root in selected for node in fs.list_tree(root))
    reservations = []
    nodes = core.walk(tree)
    for node in nodes:
        if (
            node.path.endswith(core.CONTROL_SUFFIX)
            and node.path.removesuffix(core.CONTROL_SUFFIX) in runtime_trees
        ):
            reservation = (
                core.parse_reservation(node.path, fs.read_bytes(node.path))
                if isinstance(node, core.FileLeaf)
                else None
            )
            if reservation is None:
                receipts.append(
                    core.UnwitnessedReceipt(
                        node.path,
                        "control record is not an exact regular-file reservation for this tree",
                    )
                )
            else:
                reservations.append(reservation)
        if node.path.endswith("/" + legacy["runtime_manifest"]):
            root = node.path.rsplit("/", 1)[0]
            if (
                root not in runtime_trees
                and root.removesuffix(core.RESERVED_SUFFIX) not in runtime_trees
            ):
                continue
            raw = (
                _json(fs.read_bytes(node.path))
                if isinstance(node, core.FileLeaf)
                else None
            )
            if (
                isinstance(raw, dict)
                and type(raw.get("schema_version")) is int
                and raw["schema_version"] in (1, 2)
                and isinstance(raw.get("tree_hash"), str)
            ):
                descendants = tuple(
                    child for child in nodes if child.path.startswith(root + "/")
                )
                computed = (
                    None
                    if any(isinstance(child, core.SymlinkLeaf) for child in descendants)
                    else core.canonical_tree_hash(
                        tuple(
                            (child.path.removeprefix(root + "/"), child.md5)
                            for child in descendants
                            if isinstance(child, core.FileLeaf)
                            and child.path.endswith(".py")
                            and child.md5 is not None
                        )
                    )
                )
                receipts.append(
                    core.RuntimeTreeReceipt(
                        node.path, raw["tree_hash"], computed, node.sha256
                    )
                )
            else:
                receipts.append(
                    core.UnwitnessedReceipt(
                        node.path,
                        "runtime receipt is not a regular schema 1 or 2 object with a tree hash",
                    )
                )
    return tree, tuple(documents), tuple(receipts), manifests, tuple(reservations)


def cleanup(
    home: str,
    out: TextIO,
    err: TextIO,
    fs: FileSystemPort,
    *,
    hosts: tuple[tuple[str, str], ...] | None = None,
) -> core.CleanupOutcome:
    """Clean every host, retaining in-run evidence needed by the role installer."""
    witness = None
    try:
        home = str(Path(home).absolute())
        record = json.loads(
            fs.read_bytes(str(Path(__file__).with_name("upgrade_v3_identity.json")))
        )
        marker = ".".join(record["legacy"]["hook_marker_parts"])
        identity = core.ReleaseIdentity(
            frozenset(
                core.IdentityRow(row["path"], row["sha256"]) for row in record["files"]
            ),
            tuple(
                core.HookTemplate(
                    row["event"],
                    row["matcher"],
                    row["command"]
                    .replace("{{adapter}}", marker)
                    .replace("{adapter}", marker),
                )
                for row in record["hook_templates"]
            ),
        )
        if hosts is None:
            selection = selected_hosts(home)
            if isinstance(selection, Failure):
                print(
                    f"Upgrade cleanup refused: {selection.error}; "
                    "repair the named profile override and rerun",
                    file=err,
                )
                return core.CleanupOutcome(1, witness)
            hosts = selection
        tree, snapshots, receipts, manifests, reservations = _snapshot(
            home, fs, record["legacy"], hosts=hosts
        )
        codex_hooks = next(
            (str(Path(root) / "hooks.json") for name, root in hosts if name == "codex"),
            None,
        )
        for receipt in receipts:
            if (
                isinstance(receipt, core.CodexReceipt)
                and receipt.hooks_file == codex_hooks
            ):
                snapshot = next(
                    (s for s in snapshots if s.document.path == receipt.hooks_file),
                    None,
                )
                if snapshot is not None:
                    manifest = {
                        "hooks_file": receipt.hooks_file,
                        "python_path": receipt.python_path,
                        "pythonpath": receipt.pythonpath,
                    }
                    matched_command = legacy_direct_hook_command(
                        manifest, Path(receipt.hooks_file), snapshot.raw
                    )
                    if matched_command is not None:
                        witness = core.CodexWitness(
                            manifest,
                            snapshot.raw,
                            receipt.hooks_file,
                            matched_command,
                        )
        documents = tuple(snapshot.document for snapshot in snapshots)
        partition = core.partition(
            home, tree, documents, receipts, identity, reservations, hosts=hosts
        )
        plan = core.plan(partition, tree, documents)
        for problem in partition.indeterminate:
            print(core.reservation_conflict_line(problem), file=err)
        for kept in partition.kept:
            _emit_kept(kept, out)
        file_status = _execute_file_plan(
            home, tree, identity, partition, plan, fs, out, err, hosts=hosts
        )
        for snapshot in snapshots:
            changed = _render_settings(snapshot, plan.removals, record["legacy"])
            if changed == snapshot.read_bytes:
                continue
            result = fs.replace_if_unchanged(
                snapshot.document.resolved_path, snapshot.read_bytes, changed
            )
            if isinstance(result, Changed):
                print(
                    f"{snapshot.document.path}: changed since read; no settings replacement was written; close the host and rerun",
                    file=err,
                )
                return core.CleanupOutcome(1, witness)
            for removal in plan.removals:
                if (
                    isinstance(removal, (core.DropEntry, core.DropPathSegment))
                    and removal.file == snapshot.document.path
                ):
                    print(f"REMOVED {core.locator(removal)}", file=out)
        for removal in plan.removals:
            if isinstance(removal, core.DropKey):
                before, raw = manifests[removal.manifest_path]
                document = core.drop_key(raw, removal)
                after = (json.dumps(document, indent=2) + "\n").encode()
                result = (
                    fs.replace_if_unchanged(removal.manifest_path, before, after)
                    if document
                    else fs.remove_if_unchanged(removal.manifest_path, before)
                )
                if isinstance(result, Changed):
                    print(
                        f"{removal.manifest_path}: changed since read; manifest not replaced; close the host and rerun",
                        file=err,
                    )
                    return core.CleanupOutcome(1, witness)
                print(f"REMOVED {core.locator(removal)}", file=out)
        return core.CleanupOutcome(
            1 if partition.indeterminate else file_status, witness
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(
            f"Upgrade cleanup refused: {error}; repair the named installation artifact and rerun",
            file=err,
        )
        return core.CleanupOutcome(1, witness)


def run(
    home: str,
    out: TextIO,
    err: TextIO,
    fs: FileSystemPort,
    *,
    hosts: tuple[tuple[str, str], ...] | None = None,
) -> int:
    """The console and changed-since-read seam, with no installer evidence loss."""
    return cleanup(home, out, err, fs, hosts=hosts).exit_code


def legacy_direct_hook_command(
    manifest: object, hooks_path: Path, hooks_document: object
) -> str | None:
    """Attest the legacy alias consumer using the same exact invocation evidence."""
    return _codex_legacy_direct_des_command(manifest, hooks_path, hooks_document)


def _powershell_argv(command: str) -> list[str] | None:
    """Decode the exact literal-only PowerShell command emitted by the installer."""
    tokens = command.split()
    if (
        tokens[:3] != ["powershell", "-NoProfile", "-EncodedCommand"]
        or len(tokens) != 4
    ):
        return None
    try:
        source = base64.b64decode(tokens[3], validate=True).decode("utf-16le")
    except (ValueError, UnicodeDecodeError):
        return None
    if not source.startswith("&"):
        return None

    values: list[str] = []
    index = 1
    while index < len(source):
        while index < len(source) and source[index].isspace():
            index += 1
        if index == len(source):
            break
        if source[index] != "'":
            return None
        index += 1
        value = ""
        while index < len(source):
            if source[index] != "'":
                value += source[index]
                index += 1
            elif index + 1 < len(source) and source[index + 1] == "'":
                value += "'"
                index += 2
            else:
                index += 1
                break
        else:
            return None
        if index < len(source) and not source[index].isspace():
            return None
        values.append(value)
    return values


def _command_argv(command: str) -> list[str] | None:
    """Return argv only for the exact command encodings the installer emits."""
    if os.name == "nt":
        return _powershell_argv(command)
    try:
        return shlex.split(command)
    except ValueError:
        return None


def _codex_command_owns_launcher(
    command: str, launcher_path: Path, subcommand: str = "pre-tool-use"
) -> bool:
    """Identify an nWave hook by its canonical launcher, not its interpreter.

    The interpreter is intentionally excluded from this ownership identity: a
    reinstall may run under a different Python than the one that rendered the
    previous hook command.  The launcher path and event are installer-owned
    and remain stable across that change.
    """
    argv = _command_argv(command)
    if argv is None or len(argv) < 1:
        return False
    expected_tail = [str(launcher_path), subcommand]
    if subcommand == _SESSION_START_SUBCOMMAND:
        expected_tail.append(_CODEX_HOST_PROVENANCE_ARGUMENT)
    return argv[1:] == expected_tail


def _emit_kept(value: core.Kept, out: TextIO) -> None:
    print(core.preserved_line(value), file=out)


def _emit_preserved(path: str, why: str, out: TextIO) -> None:
    print(core.preserved_path_line(path, core.Witness.W4, why), file=out)


# Effect boundary: ownership snapshots and injected filesystem/output ports stay explicit.
def _occupied_tree_lines(  # noqa: PLR0913
    home: str,
    reservation: core.Reservation,
    identity: core.ReleaseIdentity,
    fs: FileSystemPort,
    out: TextIO,
    *,
    hosts: tuple[tuple[str, str], ...],
) -> None:
    tree = fs.list_tree(reservation.tree) + fs.list_tree(reservation.reserved)
    partition = core.occupied_runtime_partition(
        home, reservation, tree, identity, hosts=hosts
    )
    for value in partition.kept:
        _emit_kept(value, out)
    for step in core.plan(partition, tree, ()).removals:
        if isinstance(step, core.RemoveFile):
            fs.remove_file(step.path)
            print(f"REMOVED {core.locator(step)}", file=out)
        elif isinstance(step, core.RemoveDir):
            fs.remove_dir(step.path)
            print(f"REMOVED {core.locator(step)}", file=out)


# Plan interpreter boundary: retain explicit immutable inputs and independent effect ports.
def _execute_file_plan(  # noqa: PLR0913, PLR0917
    home: str,
    tree: tuple[core.Node, ...],
    identity: core.ReleaseIdentity,
    partition: core.Partition,
    plan: core.Plan,
    fs: FileSystemPort,
    out: TextIO,
    err: TextIO,
    *,
    hosts: tuple[tuple[str, str], ...],
) -> int:
    controls = {r.tree: r for r in partition.reservations}
    existing_paths = {node.path for node in core.walk(tree)}
    denied, retained = set(), set()
    status = 0

    def conflict(reservation: core.Reservation, why: str) -> None:
        nonlocal status
        print(
            core.reservation_conflict_line(
                core.UnwitnessedReceipt(reservation.path, why)
            ),
            file=err,
        )
        denied.add(reservation.tree)
        status = 1

    for step in plan.removals:
        if isinstance(step, core.RemoveFile):
            fs.remove_file(step.path)
            print(f"REMOVED {core.locator(step)}", file=out)
            continue
        if isinstance(step, core.RemoveDir):
            fs.remove_dir(step.path)
            print(f"REMOVED {core.locator(step)}", file=out)
            continue
        if isinstance(step, core.Reserve):
            reservation = step.reservation
            if reservation.path in existing_paths:
                try:
                    current = fs.read_bytes(reservation.path)
                except (OSError, ValueError):
                    current = None
                if current != step.record:
                    conflict(reservation, "the previously read control record changed")
                    continue
            elif isinstance(fs.write_new(reservation.path, step.record), Occupied):
                conflict(
                    reservation,
                    "the control record could not be published without replacement",
                )
                continue
            if isinstance(
                fs.rename_noreplace(reservation.tree, reservation.reserved), Occupied
            ):
                if reservation.path not in existing_paths:
                    result = fs.remove_if_unchanged(reservation.path, step.record)
                    if isinstance(result, Changed):
                        conflict(
                            reservation,
                            "the control record changed after the reserved destination was found occupied",
                        )
                        continue
                denied.add(reservation.tree)
                _occupied_tree_lines(home, reservation, identity, fs, out, hosts=hosts)
            continue
        if not isinstance(
            step,
            (
                core.RemoveRecorded,
                core.RemoveReceipt,
                core.RemoveReservedDir,
                core.RemoveControl,
            ),
        ):
            continue
        reservation = (
            controls.get(step.tree)
            if isinstance(step, core.RemoveControl)
            else next(
                (
                    r
                    for r in controls.values()
                    if step.path == r.reserved or step.path.startswith(r.reserved + "/")
                ),
                None,
            )
        )
        if reservation is None or reservation.tree in denied:
            continue
        if (
            isinstance(
                step, (core.RemoveReceipt, core.RemoveReservedDir, core.RemoveControl)
            )
            and reservation.tree in retained
        ):
            continue
        if isinstance(step, (core.RemoveRecorded, core.RemoveReceipt)):
            if isinstance(step, core.RemoveReceipt):
                remaining = core.remaining_reserved_members(
                    reservation, fs.list_tree(reservation.reserved)
                )
                if remaining:
                    retained.add(reservation.tree)
                    for value in remaining:
                        _emit_kept(value, out)
                    continue
            try:
                data = fs.read_bytes(step.path)
            except FileNotFoundError:
                continue
            except (OSError, ValueError):
                retained.add(reservation.tree)
                _emit_preserved(
                    step.path, "reserved file is no longer a readable regular file", out
                )
                continue
            verified = core.verified_removal_bytes(step, data)
            if verified is None:
                retained.add(reservation.tree)
                if isinstance(step, core.RemoveReceipt):
                    conflict(
                        reservation, "the receipt no longer matches the control record"
                    )
                else:
                    _emit_preserved(
                        step.path, "file no longer matches its recorded digest", out
                    )
                continue
            result = fs.remove_if_unchanged(step.path, verified)
            if isinstance(result, Changed):
                retained.add(reservation.tree)
                _emit_preserved(
                    step.path, "reserved file changed since it was read", out
                )
                continue
            print(f"REMOVED {core.locator(step)}", file=out)
        elif isinstance(step, core.RemoveReservedDir):
            try:
                fs.remove_dir(step.path)
            except FileNotFoundError:
                continue
            if step.original is not None:
                print(f"REMOVED {core.locator(step)}", file=out)
        else:
            if fs.list_tree(reservation.reserved):
                retained.add(reservation.tree)
                continue
            try:
                data = fs.read_bytes(step.path)
            except FileNotFoundError:
                continue
            except (OSError, ValueError):
                conflict(
                    reservation,
                    "the control record is no longer a readable regular file",
                )
                continue
            if data != core.render_reservation(reservation):
                conflict(
                    reservation,
                    "the control record no longer equals the admitted reservation",
                )
                continue
            if isinstance(fs.remove_if_unchanged(step.path, data), Changed):
                conflict(reservation, "the control record changed since it was read")
                continue
            if not fs.list_tree(reservation.tree):
                print(f"REMOVED {core.locator(step)}", file=out)
    return status


def _legacy_hook_marker() -> str:
    """The retired hook adapter module name, from the frozen v3 identity record.

    The record is the generated byte inventory of the pinned v3.22.2 wheel; its
    legacy block names what that wheel installed. Reading the name from there
    keeps the legacy-form recognition exact without re-declaring the retired
    module in this file.
    """
    record = json.loads(
        Path(__file__).with_name("upgrade_v3_identity.json").read_text(encoding="utf-8")
    )
    return ".".join(record["legacy"]["hook_marker_parts"])


# --- cursor render laws (verbatim from HEAD 8d300bac1 closure, host-prefixed) ---
def _cursor_build_hook_entry(
    python_path: str, pythonpath: str, marker: str | None = None
) -> dict[str, Any]:
    """Build a Cursor preToolUse hook entry for the DES adapter.

    Cursor uses a flat entry shape (command + optional matcher/timeout),
    not Codex's nested ``hooks: [{type, command}]`` groups.

    Matcher targets Cursor tool names commonly used for shell and edits.
    """
    marker = marker if marker is not None else _legacy_hook_marker()
    hook_command = f"PYTHONPATH={shlex.quote(pythonpath)} {shlex.quote(python_path)} -m {marker} pre-tool-use"
    return {
        "command": hook_command,
        "matcher": "Shell|Write|Edit|Delete",
        "timeout": 30,
    }


# --- copilot render laws (verbatim from HEAD 8d300bac1 closure, host-prefixed) ---
_copilot_PRE_TOOL_USE_EVENT = "preToolUse"


def _copilot_build_hook_config(
    python_path: str, pythonpath: str, marker: str | None = None
) -> dict:
    """Build the Copilot preToolUse hook config (FS-1 double-nested shape).

    The hook config is an event-keyed object whose ``preToolUse`` value is a
    list of hook entries. Each entry is double-nested:
    ``{matcher, hooks: [{type, bash, timeoutSec}]}`` — the shape Copilot v1.0.54
    actually honors (spike FS-1). The handler payload key is ``bash`` (the shell
    command Copilot runs), distinct from the Codex ``command`` key.

    The shared DES adapter (hook_router) requires an argv positional event token
    (``pre-tool-use``); Copilot does not inject the event name as argv, so the
    token is baked into the ``bash`` command string at install time (mirrors the
    Codex precedent — without it the adapter exits 1 on every fire).

    Args:
        python_path: Absolute path to the Python executable
        pythonpath: Path to add to PYTHONPATH for DES imports

    Returns:
        Event-keyed hook config dict in the FS-1 double-nested shape.
    """
    marker = marker if marker is not None else _legacy_hook_marker()
    hook_command = f"PYTHONPATH={pythonpath} {python_path} -m {marker} pre-tool-use"
    return {
        _copilot_PRE_TOOL_USE_EVENT: [
            {
                "matcher": ".*",
                "hooks": [{"type": "command", "bash": hook_command, "timeoutSec": 30}],
            }
        ]
    }


# --- codex render laws (verbatim from HEAD 8d300bac1 closure, host-prefixed) ---
_codex_LAUNCHER_FILENAME = "nwave_claude_code_hook_adapter_launcher.py"

_codex_PRE_TOOL_USE_EVENT = "PreToolUse"

_SESSION_START_SUBCOMMAND = "session-start"
_CODEX_HOST_PROVENANCE_ARGUMENT = "--host-provenance=codex"

_codex_ANNOUNCED_TOOLS: tuple[str, ...] = (
    "exec_command",
    "Bash",
    "write_stdin",
    "update_plan",
    "request_user_input",
    "view_image",
    "multi_agent_v1",
    "get_goal",
    "create_goal",
    "update_goal",
    "web_search",
)

_codex_INTERCEPTED_TOOLS: tuple[str, ...] = ("exec_command", "Bash")


def _codex_pre_tool_use_matcher() -> str:
    """Return a matcher restricted to tools observed on the Codex host."""
    unannounced = set(_codex_INTERCEPTED_TOOLS).difference(_codex_ANNOUNCED_TOOLS)
    if not _codex_INTERCEPTED_TOOLS or unannounced:
        raise ValueError(
            f"Codex PreToolUse matcher names no observed host tool: {sorted(unannounced)!r}"
        )
    return "|".join(f"^{re.escape(tool)}$" for tool in _codex_INTERCEPTED_TOOLS)


_codex_LAUNCHER_TIMEOUT_ENV = "NWAVE_CODEX_HOOK_TIMEOUT"

_codex_LAUNCHER_TIMEOUT_SECONDS = 25.0


def _codex_build_hook_invocation(
    python_path: str, pythonpath: str, marker: str | None = None
) -> dict:
    """Build a shell-independent DES invocation with literal argv and env."""
    marker = marker if marker is not None else _legacy_hook_marker()
    return {
        "argv": [python_path, "-m", marker, "pre-tool-use"],
        "env": {"PYTHONPATH": pythonpath},
    }


def _codex_launcher_source(
    python_path: str, pythonpath: str, marker: str | None = None
) -> str:
    """Return the exact bytes of an nWave-generated launcher.

    This text becomes executable code on the operator's machine, so the spawn it
    emits owes the same two duties every hand-written spawn in this tree owes
    (``tests/build/test_no_unbounded_unstdin_spawn.py``): an explicit stdin
    decision and a wall-clock bound.  The static ban cannot see this one -- at
    scan time it is a string literal, not a Call node -- so the duties are
    discharged here and witnessed behaviourally by
    ``tests/bugs/test_bug_generated_launcher_unbounded_spawn.py``.

    The stdin decision is a FORWARD, not a ``DEVNULL``: the Codex hook protocol
    is JSON on stdin and the DES adapter reads it, while
    ``read_and_parse_stdin`` fails OPEN on empty input -- starving the child
    would switch validation off silently.  It is a pass-through rather than an
    ``input=`` read so the launcher itself never blocks on a descriptor that
    never reaches EOF; the child's read stays the only blocking wait on the
    path, and the bound covers it.

    The bound sits below the ``timeout: 30`` this installer declares on the hook
    entry, so the launcher reaches its own explained verdict before the harness
    kills it, and degrades LOUD-and-allow on expiry (the adapter's own policy:
    a hook never bricks a session).

    The child's stdout/stderr go to seekable ``tempfile.TemporaryFile`` objects,
    never ``PIPE``/``capture_output=True``: a grandchild that inherits a pipe's
    write end keeps it open, and ``subprocess.run`` keeps waiting on it after the
    direct child has exited -- the same hang this file exists to close.

    The shared adapter writes the legacy Claude Code ``{"decision": "block",
    "reason": ...}`` shape to stdout on exit 2 and may leave stderr empty.
    Codex's legacy exit-2-plus-stderr blocking path is fragile against exactly
    that (a stale/absent/miscaptured stderr reads as a FAILED hook, not a
    block), so on child exit 2 this launcher translates instead of forwarding:
    it derives a reason (child stderr, then the stdout JSON's top-level
    ``reason``, then ``hookSpecificOutput.permissionDecisionReason``, then a
    deterministic WHAT/WHY/HOW fallback) and emits exactly one Codex-native
    ``{"decision": "block", "reason": ...}`` JSON document on its OWN stdout,
    exiting 0 -- Codex's documented normal-block shape, not its failure path.
    The child's own stdout/stderr are not also forwarded on this path, so
    Codex never sees two JSON documents on stdout.
    """
    marker = marker if marker is not None else _legacy_hook_marker()
    return f'"""nWave Codex DES launcher. Generated; reinstall to update."""\nimport json\nimport os\nimport subprocess\nimport sys\nimport tempfile\n\nPYTHON_PATH = {json.dumps(python_path)}\nPYTHONPATH = {json.dumps(pythonpath)}\nTIMEOUT_ENV = {json.dumps(_codex_LAUNCHER_TIMEOUT_ENV)}\nDEFAULT_TIMEOUT_SECONDS = {_codex_LAUNCHER_TIMEOUT_SECONDS!r}\nenv = os.environ.copy()\nenv["PYTHONPATH"] = PYTHONPATH\nargv = [\n    PYTHON_PATH,\n    "-m",\n    {json.dumps(marker)},\n    "pre-tool-use",\n]\ntry:\n    bound = float(os.environ.get(TIMEOUT_ENV, DEFAULT_TIMEOUT_SECONDS))\nexcept (TypeError, ValueError):\n    bound = DEFAULT_TIMEOUT_SECONDS\ntry:\n    stdin_channel = sys.stdin.fileno()\nexcept (AttributeError, OSError, ValueError):\n    stdin_channel = subprocess.DEVNULL\nwith tempfile.TemporaryFile(\n    mode="w+", encoding="utf-8", errors="replace"\n) as stdout_tmp, tempfile.TemporaryFile(\n    mode="w+", encoding="utf-8", errors="replace"\n) as stderr_tmp:\n    try:\n        completed = subprocess.run(\n            argv,\n            env=env,\n            check=False,\n            stdin=stdin_channel,\n            timeout=bound,\n            stdout=stdout_tmp,\n            stderr=stderr_tmp,\n        )\n    except subprocess.TimeoutExpired:\n        sys.stderr.write(\n            f"WHAT: the nWave DES PreToolUse validation did not finish "\n            f"within its {{bound:g}}s bound and was killed.\\n"\n            f"WHY: a hook that never returns hangs the Codex session, "\n            f"so this launcher bounds its child and always yields.\\n"\n            f"HOW: re-run. If the validation genuinely needs longer, "\n            f"set {{TIMEOUT_ENV}}=<seconds>. Allowing the tool without "\n            f"a verdict.\\n"\n        )\n        sys.exit(0)\n    stdout_tmp.seek(0)\n    stderr_tmp.seek(0)\n    child_stdout = stdout_tmp.read()\n    child_stderr = stderr_tmp.read()\nif completed.returncode == 2:\n    reason = child_stderr.strip()\n    if not reason:\n        try:\n            payload = json.loads(child_stdout)\n        except (TypeError, ValueError):\n            payload = None\n        candidate = None\n        if isinstance(payload, dict):\n            candidate = payload.get("reason")\n            if not (isinstance(candidate, str) and candidate.strip()):\n                hook_specific = payload.get("hookSpecificOutput")\n                candidate = (\n                    hook_specific.get("permissionDecisionReason")\n                    if isinstance(hook_specific, dict)\n                    else None\n                )\n        if isinstance(candidate, str) and candidate.strip():\n            reason = candidate.strip()\n    if not reason:\n        reason = (\n            "WHAT: the nWave DES PreToolUse hook blocked this tool "\n            "call (exit 2) without a readable reason.\\n"\n            "WHY: its child wrote nothing to stderr, and stdout was "\n            "not valid JSON with a `reason` or "\n            "`hookSpecificOutput.permissionDecisionReason` field.\\n"\n            "HOW: re-run to reproduce, or inspect the DES adapter "\n            "raw stdout above.\\n"\n        )\n    json.dump({{"decision": "block", "reason": reason.strip()}}, sys.stdout)\n    sys.stdout.write("\\n")\n    sys.exit(0)\nsys.stdout.write(child_stdout)\nsys.stderr.write(child_stderr)\nsys.exit(completed.returncode)\n'


def _codex_v1_launcher_source(
    python_path: str, pythonpath: str, marker: str | None = None
) -> str:
    """Return the exact launcher body emitted by the public v1 bootstrap."""
    marker = marker if marker is not None else _legacy_hook_marker()
    return f'"""nWave Codex DES launcher. Generated; reinstall to update."""\nimport os\nimport subprocess\nimport sys\n\nPYTHON_PATH = {json.dumps(python_path)}\nPYTHONPATH = {json.dumps(pythonpath)}\nenv = os.environ.copy()\nenv["PYTHONPATH"] = PYTHONPATH\nargv = [PYTHON_PATH, "-m", {json.dumps(marker)}, "pre-tool-use"]\ncompleted = subprocess.run(argv, env=env, check=False)\nsys.exit(completed.returncode)\n'


def _codex_build_hook_entry(
    python_path: str, pythonpath: str, marker: str | None = None
) -> dict:
    """Build the Codex PreToolUse hook entry for the DES adapter.

    The hook entry follows the Codex hooks.json format:
    - matcher: regex that matches tool names to intercept
    - hooks: list of command entries with type, command, timeout

    Matcher is narrowed to ``^Bash$|^apply_patch$`` — the two tools
    Codex actually emits in PreToolUse per
    developers.openai.com/codex/hooks (DDD-6, verified by DDD-8 spike Q6):
    - Bash: shell command execution
    - apply_patch: file edits performed by Codex

    The pre-FM-3 matcher (``^Task$|^Bash$``) referenced ``Task`` — a
    Claude-Code-internal tool name Codex never emits — by analogy with the
    Claude Code plugin. FM-3 root cause: mirrored a peer without reading
    the Codex docs. ``Edit|Write`` aliases for apply_patch and ``mcp__*``
    matchers are deferred to a later slice per DESIGN.

    Read / Grep / Glob and other read-only tools are excluded to avoid
    unnecessary overhead on every file access. Using ``.*`` (all tools)
    was the walking-skeleton default; this matcher is the
    production-grade narrow form.

    Args:
        python_path: Absolute path to the Python executable
        pythonpath: Path to add to PYTHONPATH for DES imports

    Returns:
        Dict representing a single hooks.json entry
    """
    marker = marker if marker is not None else _legacy_hook_marker()
    invocation = _codex_build_hook_invocation(python_path, pythonpath, marker)
    _, *module_argv = invocation["argv"]
    module_and_event = " ".join(module_argv)
    pythonpath = invocation["env"]["PYTHONPATH"]
    windows_path = len(python_path) >= 3 and python_path[1:3] in {":/", ":\\"}
    if windows_path:
        powershell_python = python_path.replace("'", "''")
        powershell_pythonpath = pythonpath.replace("'", "''")
        hook_command = f"""powershell -NoProfile -Command '$env:PYTHONPATH = "{powershell_pythonpath}"; & "{powershell_python}" {module_and_event}'"""
    else:
        hook_command = f"PYTHONPATH={shlex.quote(pythonpath)} {shlex.quote(python_path)} {module_and_event}"
    return {
        "matcher": _codex_pre_tool_use_matcher(),
        "hooks": [
            {
                "type": "command",
                "command": hook_command,
                "timeout": 30,
                "statusMessage": "nWave DES validation...",
            }
        ],
    }


def _codex_legacy_direct_des_command(
    manifest: object, hooks_path: Path, hooks_document: object
) -> str | None:
    """Return the sole direct-hook command proven by the pre-launcher manifest.

    The original Codex bootstrap recorded only its hook file, interpreter and
    PYTHONPATH.  That sparse record is ownership evidence only when it has its
    exact three-field shape *and* either the recorded direct command or the
    exact v1 launcher file and command still appears in ``hooks.PreToolUse``.
    A module-name substring, another event, or a merely similar shell command
    is deliberately not enough.
    """
    if not (
        isinstance(manifest, dict)
        and set(manifest) == {"hooks_file", "python_path", "pythonpath"}
        and (manifest.get("hooks_file") == str(hooks_path))
        and isinstance(manifest.get("python_path"), str)
        and manifest["python_path"]
        and isinstance(manifest.get("pythonpath"), str)
        and manifest["pythonpath"]
        and isinstance(hooks_document, dict)
        and isinstance(hooks_document.get("hooks"), dict)
    ):
        return None
    expected_direct = _codex_build_hook_entry(
        manifest["python_path"], manifest["pythonpath"], _legacy_hook_marker()
    )["hooks"][0]["command"]
    launcher_path = hooks_path.parent / _codex_LAUNCHER_FILENAME
    try:
        launcher_is_v1 = (
            launcher_path.is_file()
            and (not launcher_path.is_symlink())
            and (
                launcher_path.read_text(encoding="utf-8")
                == _codex_v1_launcher_source(
                    manifest["python_path"], manifest["pythonpath"]
                )
            )
        )
    except (OSError, UnicodeDecodeError):
        launcher_is_v1 = False
    expected_launcher = shlex.join(
        [manifest["python_path"], str(launcher_path), "pre-tool-use"]
    )
    pretool = hooks_document["hooks"].get(_codex_PRE_TOOL_USE_EVENT)
    if not isinstance(pretool, list):
        return None
    for group in pretool:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            continue
        for handler in group["hooks"]:
            command = handler.get("command") if isinstance(handler, dict) else None
            if command == expected_direct or (
                launcher_is_v1 and command == expected_launcher
            ):
                return command
    return None
