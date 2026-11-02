"""Filesystem effects implementing the pure write plan, one atomic rename per Write."""

import os
import shutil
import stat
import tempfile
from pathlib import Path

from nwdes.contracts import Built, Defect, checked
from nwdes.destinations import local_path
from nwdes.documents import OutputSet, Write, parse_adr_filename, plan_writes, read_adr
from nwdes.handoff import UnavailableInput
from nwdes.shell.ports import IOFailure, Missing, Unreadable, WriteResult


def read_file(path):
    try:
        return Path(path).read_bytes()
    except FileNotFoundError as error:
        return Missing(str(path), str(error))
    except OSError as error:
        return Unreadable(str(path), str(error))


def check_paths(root, paths):
    base = Path(root)
    prefixes = dict.fromkeys(
        base.joinpath(*parts[:index])
        for path in paths
        for parts in (Path(path).parts,)
        for index in range(1, len(parts) + 1)
    )
    return checked(
        None,
        (
            Defect(
                f"DestinationInvalid: {prefix.relative_to(base)}",
                f"Path crosses symlink {prefix}.",
                "Choose a repository-relative destination without symlinks.",
            )
            for prefix in prefixes
            if prefix.is_symlink()
        ),
    )


def read_register_files(root, directory):
    folder = Path(root) / directory
    try:
        paths = tuple(sorted(folder.iterdir()))
    except FileNotFoundError:
        return Built({})
    except OSError as error:
        return Unreadable(str(folder), str(error))
    files = {}
    for path in paths:
        if parse_adr_filename(path.name) is not None:
            raw = read_file(path)
            files[path.name] = (
                raw
                if isinstance(raw, bytes)
                else UnavailableInput(
                    Defect(
                        f"InputUnreadable: {path}",
                        raw.reason,
                        "Make this ADR file readable before retrying.",
                    )
                )
            )
    return Built(files)


def read_register(root, directory):
    result = read_register_files(root, directory)
    if isinstance(result, Unreadable):
        return result
    for name, raw in result.value.items():
        if isinstance(raw, UnavailableInput):
            return Unreadable(str(Path(root) / directory / name), raw.defect.why)
    return read_adr(result.value)


def write_outputs(root: str, outputs: OutputSet):
    existing = {}
    for output in outputs.outputs:
        path = Path(root) / output.path
        try:
            existing[output.path] = path.read_bytes() if path.is_file() else None
        except OSError as error:
            return IOFailure((output.path,), str(error))
    plan = plan_writes(outputs, existing)
    reported = []
    for index, step in enumerate(plan):
        if not isinstance(step, Write):
            reported.append(("UNCHANGED", step.path))
            continue
        path = Path(root) / step.path
        temporary = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(
                prefix="." + path.name + ".", dir=path.parent
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(step.data)
            Path(temporary).replace(path)
            temporary = None
            reported.append(("WROTE", step.path))
        except OSError as error:
            return IOFailure(
                tuple(remaining.path for remaining in plan[index:]), str(error)
            )
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
    return WriteResult(tuple(reported))


def ensure_exclude(root):
    path = Path(root) / ".git/info/exclude"
    try:
        original = path.read_bytes() if path.exists() else b""
        if b"lanes/" not in original.splitlines():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(
                original
                + (b"\n" if original and not original.endswith(b"\n") else b"")
                + b"lanes/\n"
            )
        return Built(None)
    except OSError as error:
        return IOFailure((str(path),), str(error))


def remove_paths(root, paths):
    try:
        base = Path(root).resolve()
    except (OSError, RuntimeError) as error:
        return IOFailure(paths, str(error))
    reported = []
    for index, relative in enumerate(paths):
        if not local_path(relative.rstrip("/")):
            return IOFailure(
                paths[index:],
                "Removal requires a confined repository-relative path: " + relative,
            )
        path = base / relative
        try:
            if not path.parent.resolve().is_relative_to(base):
                return IOFailure(
                    paths[index:], "Removal crosses an external symlink: " + relative
                )
            if stat.S_ISDIR(path.lstat().st_mode):
                shutil.rmtree(path)
            else:
                path.unlink()
            reported.append(("REMOVED", relative))
        except (OSError, RuntimeError) as error:
            return IOFailure(paths[index:], str(error))
    return WriteResult(tuple(reported))
