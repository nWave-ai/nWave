"""Filesystem and process effects for public examination workspaces."""

import errno
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from nwdes import packets, prose
from nwdes.contracts import Built, Defect, Refused, checked
from nwdes.shell.git import failure_reason, run_git, scrubbed_env
from nwdes.shell.ports import Unreadable


WORKSPACE_PREFIX = "nwdes-examine-"


def _git(root, arguments):
    result = run_git(str(root), arguments, env=scrubbed_env(os.environ))
    if isinstance(result, Unreadable) or result.code != 0:
        return checked(
            None,
            (
                Defect(
                    "InputUnreadable: git " + " ".join(arguments),
                    failure_reason(result),
                    "Run the examine prompt from a git checkout of the candidate with git on PATH; "
                    "the public projection reads committed files at HEAD.",
                ),
            ),
        )
    return Built(result.stdout)


def _committed(root, name):
    """The committed blob at HEAD for one path, or None when HEAD does not commit it."""
    listed = _git(root, ("ls-tree", "-z", "HEAD", "--", name))
    if isinstance(listed, Refused):
        return listed
    if not listed.value:
        return Built(None)
    found = _git(root, ("cat-file", "blob", "HEAD:" + name))
    if isinstance(found, Refused) and name == packets.DECLARATION_FILE:
        return checked(None, (packets.declaration_unreadable(),))
    return found


def _path_flag():
    """O_PATH: a reference that needs search permission on each directory, not read permission on the
    file, so an execute-only executable is reachable. Where the platform has no O_PATH the open needs
    read permission. Read at call time, so a platform without the flag still imports this module."""
    return getattr(os, "O_PATH", os.O_RDONLY)


def _no_follow():
    return getattr(os, "O_NOFOLLOW", 0) | _path_flag()


def _descriptor_walk_supported():
    """Whether a name can be opened relative to a directory descriptor without following a symlink."""
    return hasattr(os, "O_NOFOLLOW") and os.open in os.supports_dir_fd


_BY_ERRNO = {
    errno.ENOENT: "missing",
    errno.ELOOP: "symlink",
    errno.ENOTDIR: "not_directory",
    errno.EACCES: "no_access",
    errno.EPERM: "no_access",
}


def _entry(parent, name):
    """(status, descriptor) for one name under an open directory: no symlink is followed, and the
    descriptor refers to the entry itself. Without O_PATH the open needs read permission, so an EACCES
    there is not_readable; with O_PATH an EACCES means the directory cannot be searched (no_access)."""
    try:
        descriptor = os.open(name, _no_follow(), dir_fd=parent)
    except OSError as error:
        if error.errno == errno.EACCES and not hasattr(os, "O_PATH"):
            return "not_readable", None
        return _BY_ERRNO.get(error.errno, "unreadable"), None
    if stat.S_ISLNK(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        return "symlink", None
    return "ok", descriptor


def _open_by_descriptors(root, relative):
    """(status, descriptor) for a declared executable, walking the path one name at a time. The
    descriptor is the file a run executes."""
    parts = relative.split("/")
    try:
        current = os.open(root, _path_flag() | getattr(os, "O_DIRECTORY", 0))
    except OSError as error:
        return _BY_ERRNO.get(error.errno, "unreadable"), None
    opened = [current]
    try:
        for part in parts[:-1]:
            status, child = _entry(current, part)
            if child is None:
                return ("symlink_directory" if status == "symlink" else status), None
            opened.append(child)
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                return "not_directory", None
            current = child
        status, descriptor = _entry(current, parts[-1])
        if descriptor is None:
            return status, None
        mode = os.fstat(descriptor).st_mode
        if not stat.S_ISREG(mode):
            os.close(descriptor)
            return "missing", None
        if mode & 0o111:
            return "ok", descriptor
        os.close(descriptor)
        return "not_executable", None
    finally:
        for descriptor in opened:
            os.close(descriptor)


def _open_declared(root, relative):
    """(status, descriptor) for a declared executable. The descriptor is the file a run starts.

    A platform without descriptor-relative no-follow opens cannot pin the file it checks, so it is
    refused with no_descriptor_walk and no handle: the examiner never checks a path by name and then
    runs it by name. status is ok or the cause of the refusal; the handle is None unless ok.
    """
    if not _descriptor_walk_supported():
        return "no_descriptor_walk", None
    return _open_by_descriptors(root, relative)


def _declared_status(root, relative):
    status, handle = _open_declared(root, relative)
    if isinstance(handle, int):
        os.close(handle)
    return status


def projection(root):
    listing = _git(
        root, ("ls-tree", "-r", "-z", "HEAD", "--", *prose.PUBLIC_PROJECTION[0])
    )
    if isinstance(listing, Refused):
        return listing
    files = {}
    for name, identity in packets.public_entries(listing.value):
        content = _git(root, ("cat-file", "blob", identity))
        if isinstance(content, Refused):
            return content
        files[name] = content.value
    manifests = {}
    for name in packets.MANIFESTS:
        found = _committed(root, name)
        if isinstance(found, Refused):
            return found
        manifests[name] = found.value
        if found.value is not None:
            # the first committed manifest in precedence order decides; a later one is never read
            break
    common = _git(root, ("rev-parse", "--path-format=absolute", "--git-common-dir"))
    if isinstance(common, Refused):
        return common
    declared = packets.declare(manifests)
    executables = {
        path: _declared_status(root, path) for path in packets.required_paths(declared)
    }
    planned = packets.public_projection(
        listing.value, files, declared, str(root), executables
    )
    if isinstance(planned, Refused):
        return planned
    return Built(
        (
            planned.value,
            (str(root), str(Path(os.fsdecode(common.value).strip()).parent.resolve())),
        )
    )


def _enumerate(workspace):
    entries = []

    def visit(directory):
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(workspace).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                entries.append(packets.WorkspaceEntry(relative, "link"))
            elif stat.S_ISDIR(mode):
                entries.append(packets.WorkspaceEntry(relative, "dir"))
                if relative != "scratch":
                    visit(path)
            elif stat.S_ISREG(mode):
                entries.append(
                    packets.WorkspaceEntry(
                        relative,
                        "file",
                        path.read_bytes(),
                        bool(mode & 0o222),
                    )
                )
            else:
                entries.append(packets.WorkspaceEntry(relative, "other"))

    visit(workspace)
    return tuple(entries)


def inspect(projection, workspace, roots):
    try:
        if workspace.is_symlink():
            return checked(
                None, (packets.workspace_contaminated(("workspace symlink",)),)
            )
        return packets.inspect_workspace(
            projection,
            str(workspace),
            str(workspace.resolve()),
            roots,
            _enumerate(workspace),
        )
    except OSError as error:
        return checked(None, (packets.workspace_contaminated((str(error),)),))


def _scope_key(handoff):
    return hashlib.sha256(str(Path(handoff).resolve()).encode("utf-8")).hexdigest()


def _scope_records(records, handoff):
    """The record files of one examination scope: one per workspace it has left, in name order."""
    directory = Path(records)
    if not directory.is_dir():
        return []
    return sorted(directory.glob(_scope_key(handoff) + "-*.json"))


def _record(records, handoff, workspace):
    """Name the workspace in the checkout's private record directory, so close can find it."""
    Path(records).mkdir(parents=True, exist_ok=True)
    name = _scope_key(handoff) + "-" + workspace.name + ".json"
    (Path(records) / name).write_text(
        json.dumps({"workspace": str(workspace)}), encoding="utf-8"
    )


def materialize(root, records, handoff):
    root = Path(root).resolve()
    planned = projection(root)
    if isinstance(planned, Refused):
        return planned
    public, roots = planned.value
    for outcome, path, reason in discard(records, handoff):
        if outcome == "kept":
            sys.stderr.write("\nKEPT " + path + " - " + reason + "\n")
    workspace = None
    try:
        workspace = Path(tempfile.mkdtemp(prefix=WORKSPACE_PREFIX))
        (workspace / "public").mkdir()
        (workspace / "scratch").mkdir()
        for name, content in public.files:
            target = workspace / "public" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(0o444)
        inspected = inspect(public, workspace, roots)
        if isinstance(inspected, Refused):
            shutil.rmtree(workspace)
            return inspected
        _record(records, handoff, workspace)
        return inspected
    except OSError as error:
        if workspace is not None:
            shutil.rmtree(workspace, ignore_errors=True)
        return checked(
            None,
            (
                Defect(
                    "InputUnreadable: " + str(workspace or tempfile.gettempdir()),
                    str(error),
                    "Make the system temporary directory writable and rebuild the examine prompt.",
                ),
            ),
        )


def _recorded_workspace(record):
    try:
        return Path(json.loads(record.read_text(encoding="utf-8"))["workspace"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _settle(record, outcome):
    """Drop the record once its workspace is gone; a kept workspace keeps it for a later attempt."""
    if outcome[0] != "kept":
        record.unlink(missing_ok=True)
    return outcome


def _remove(record, gate):
    """One record's outcome: removed, gone (already absent) or kept, with its reason.

    gate(workspace) returns the reason to keep the workspace, or None to allow its removal.
    """
    workspace = _recorded_workspace(record)
    if workspace is None:
        return "kept", str(record), "its record cannot be read"
    if not workspace.name.startswith(WORKSPACE_PREFIX):
        return "kept", str(workspace), "its name is not an examination workspace name"
    if not workspace.is_symlink() and not workspace.exists():
        return "gone", str(workspace), "it is already absent"
    reason = gate(workspace)
    if reason:
        return "kept", str(workspace), reason
    try:
        shutil.rmtree(workspace)
    except OSError as error:
        return "kept", str(workspace), str(error)
    return "removed", str(workspace), ""


def retire(root, records, handoff):
    """Remove each examination workspace recorded for one scope, once its inspection is clean.

    An accepted close calls this after publication. Returns one (outcome, path, reason) per
    record of the scope, or () when the scope has none. A removed or absent workspace loses its
    record; a kept one keeps its record so a later close names it again. Other scopes' records
    are never read.
    """
    records_of_scope = _scope_records(records, handoff)
    if not records_of_scope:
        return ()
    planned = projection(root)
    if isinstance(planned, Refused):
        reason = "; ".join(d.what for d in planned.defects)
        return tuple(
            _settle(record, ("kept", str(record), reason))
            for record in records_of_scope
        )
    public, roots = planned.value

    def gate(workspace):
        verdict = inspect(public, workspace, roots)
        if isinstance(verdict, Refused):
            return "; ".join(d.what for d in verdict.defects)
        return None

    return tuple(_settle(record, _remove(record, gate)) for record in records_of_scope)


def _own_layout(workspace):
    """Discard gate: remove only a non-symlink workspace whose top level is exactly public and scratch."""
    if workspace.is_symlink():
        return "it is a symbolic link"
    try:
        names = sorted(entry.name for entry in workspace.iterdir())
    except OSError as error:
        return str(error)
    if names != ["public", "scratch"]:
        return "its top level is not exactly public and scratch"
    return None


def discard(records, handoff):
    """Remove each workspace recorded for one scope on its re-prompt or abort, when its top level
    is exactly public and scratch. Nothing is published by those steps, so this top-level guard is
    the whole gate; a workspace failing it is kept with its record and reported kept. Returns one
    (outcome, path, reason) per record of the scope, or () when the scope has none.
    """
    return tuple(
        _settle(record, _remove(record, _own_layout))
        for record in _scope_records(records, handoff)
    )


def _read_path(workspace, path):
    public = workspace / "public"
    target = public / path
    symlink = any(
        part.is_symlink()
        for part in (target, *target.parents)
        if part != workspace.parent
    )
    return packets.prepare_read(
        packets.ExaminationWorkspace(str(workspace), ()),
        path,
        str(target.resolve()),
        symlink,
    )


def run(root, workspace, action, arguments):
    root = Path(root).resolve()
    workspace = Path(workspace).absolute()
    planned = projection(root)
    if isinstance(planned, Refused):
        return planned
    public, roots = planned.value
    inspected = inspect(public, workspace, roots)
    if isinstance(inspected, Refused):
        return inspected
    if action == "read":
        ready = _read_path(workspace, arguments[0] if arguments else ".")
        if isinstance(ready, Refused):
            return ready
        try:
            target = Path(ready.value.path)
            if target.is_dir():
                sys.stdout.write(
                    "".join(
                        p.name + ("/" if p.is_dir() else "") + "\n"
                        for p in sorted(target.iterdir())
                    )
                )
            elif target.is_file():
                sys.stdout.buffer.write(target.read_bytes())
            else:
                return checked(
                    None,
                    (
                        Defect(
                            "ReadRefused: " + str(arguments),
                            "The public path does not exist or is not a regular file.",
                            "List the public directory with nwdes examine read --workspace W and choose an existing path.",
                        ),
                    ),
                )
        except OSError as error:
            return checked(
                None,
                (
                    Defect(
                        "ReadRefused: " + str(arguments),
                        str(error),
                        "Read an accessible public document with nwdes examine read --workspace W.",
                    ),
                ),
            )
        return 0
    argv = tuple(arguments[1:] if arguments[:1] == ["--"] else arguments)
    resolved = tuple(
        str(
            (
                workspace
                / "scratch"
                / (arg.split("=", 1)[1] if arg.startswith("--") and "=" in arg else arg)
            ).resolve()
        )
        for arg in argv[1:]
    )
    ready = packets.prepare_probe(
        public,
        inspected.value,
        argv,
        resolved,
        packets.ProbeRuntime(
            str(root), sys.executable, (root / "src").is_dir(), os.environ
        ),
    )
    if isinstance(ready, Refused):
        return ready
    plan = ready.value
    if plan.executable is not None:
        return _run_declared(root, plan)
    try:
        result = subprocess.run(
            plan.argv,
            cwd=plan.cwd,
            env=dict(plan.environment),
            capture_output=True,
            check=False,
        )
    except OSError as error:
        return checked(
            None,
            (
                Defect(
                    "InputUnreadable: probe interpreter",
                    str(error),
                    "Restore the running Python interpreter and retry nwdes examine probe.",
                ),
            ),
        )
    sys.stdout.buffer.write(packets.mask_candidate(result.stdout, plan.candidate))
    sys.stderr.buffer.write(packets.mask_candidate(result.stderr, plan.candidate))
    return result.returncode


def _run_declared(root, plan):
    """Run the declared executable that was checked, passing its exit and streams through. The program
    is started through /dev/fd/N, the very file the descriptor walk checked."""
    status, handle = _open_declared(root, plan.executable)
    if handle is None:
        return checked(
            None, (packets.executable_defect(plan.executable, status, plan.remedy),)
        )
    try:
        result = subprocess.run(
            plan.argv,
            executable=f"/dev/fd/{handle}",
            pass_fds=(handle,),
            cwd=plan.cwd,
            env=dict(plan.environment),
            capture_output=True,
            check=False,
        )
    except OSError as error:
        return checked(
            None,
            (packets.executable_launch_failure(plan.executable, error, plan.remedy),),
        )
    finally:
        os.close(handle)
    sys.stdout.buffer.write(packets.mask_candidate(result.stdout, plan.candidate))
    sys.stderr.buffer.write(packets.mask_candidate(result.stderr, plan.candidate))
    return result.returncode
