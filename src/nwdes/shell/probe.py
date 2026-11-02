"""Filesystem and process effects for public examination workspaces."""

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
    manifest = _git(root, ("cat-file", "blob", "HEAD:pyproject.toml"))
    if isinstance(manifest, Refused):
        return manifest
    common = _git(root, ("rev-parse", "--path-format=absolute", "--git-common-dir"))
    if isinstance(common, Refused):
        return common
    planned = packets.public_projection(listing.value, files, manifest.value, str(root))
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


def materialize(root):
    root = Path(root).resolve()
    planned = projection(root)
    if isinstance(planned, Refused):
        return planned
    public, roots = planned.value
    workspace = None
    try:
        workspace = Path(tempfile.mkdtemp(prefix="nwdes-examine-"))
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
