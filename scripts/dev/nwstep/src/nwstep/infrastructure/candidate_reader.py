"""Reads the identity of the candidate in a project directory.

Version control is an adapter here, not a requirement. When git answers and nothing is uncommitted, the identity
is the commit. When changes are uncommitted, or when no version control answers, the identity is a digest of the
tree state, and the returned notes say so: the caller prints them, so a weaker identity is never silent.
The workspace directory is left out of every reading: its files change with each record and are not the candidate.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from nwstep.domain import candidate
from nwstep.domain.candidate import Observed, Unreadable


GIT_TIMEOUT_S = 300
TWO_NAMES = frozenset("RC")


def read_candidate(root: Path, workspace: Path) -> Observed | Unreadable:
    if not root.is_dir():
        return Unreadable(f"the project directory {root} does not exist")
    top = _git(root, "rev-parse", "--show-toplevel")
    if isinstance(top, str):
        return _unversioned(root, workspace, f"git cannot be run ({top})")
    if top.returncode != 0:
        return _unversioned(root, workspace, "it is not inside a git repository")
    return _versioned(Path(_text(top.stdout).strip()), workspace)


def _versioned(repository: Path, workspace: Path) -> Observed | Unreadable:
    """The commit of a repository with nothing uncommitted, else a digest of the files git lists for it."""
    excluded = _relative(workspace, repository)
    status = _git(repository, "status", "--porcelain", "-z", "--untracked-files=all")
    head = _git(repository, "rev-parse", "--verify", "--quiet", "HEAD^{commit}")
    if isinstance(status, str) or isinstance(head, str) or status.returncode != 0:
        return Unreadable(f"git cannot read the state of {repository}")
    changed = _changed(_text(status.stdout), excluded)
    identity = candidate.commit(_text(head.stdout)) if head.returncode == 0 else None
    if identity is not None and not changed:
        return Observed(identity)
    listed = _git(
        repository, "ls-files", "-z", "--cached", "--others", "--exclude-standard"
    )
    if isinstance(listed, str) or listed.returncode != 0:
        return Unreadable(f"git cannot list the files of {repository}")
    names = {
        name
        for name in _text(listed.stdout).split("\0")
        if name and not _under(name, excluded)
    }
    files = _contents(repository, sorted(names))
    if isinstance(files, Unreadable):
        return files
    return Observed(
        candidate.tree_digest(files),
        (
            f"{repository} has uncommitted changes: the candidate identity is a digest of the tree state, not a "
            "commit. Commit the changes and run packet again to get a commit identity; a verdict for this digest "
            "does not carry over to that commit.",
        ),
    )


def _unversioned(root: Path, workspace: Path, reason: str) -> Observed | Unreadable:
    """A digest of every file under the root, with the reason no version control names the candidate."""
    excluded = _relative(workspace, root)
    names: list[str] = []
    for directory, subdirectories, filenames in os.walk(root):
        relative = os.path.relpath(directory, root)
        prefix = "" if relative == "." else relative + "/"
        subdirectories[:] = sorted(
            name for name in subdirectories if not _under(prefix + name, excluded)
        )
        names += [prefix + name for name in filenames]
    files = _contents(root, sorted(names))
    if isinstance(files, Unreadable):
        return files
    return Observed(
        candidate.tree_digest(files),
        (
            f"no version control names the candidate in {root}: {reason}. The candidate identity is a digest of "
            "every file under that directory, so a build or cache file changes it too.",
        ),
    )


def _contents(
    base: Path, names: list[str]
) -> list[tuple[str, bytes | None]] | Unreadable:
    """Each listed path with its bytes; a link counts as its target text, a listed path that is gone as absent."""
    files: list[tuple[str, bytes | None]] = []
    for name in names:
        path = base / name
        try:
            if path.is_symlink():
                files.append((name, os.fsencode(path.readlink())))
            elif path.is_file():
                files.append((name, path.read_bytes()))
            else:
                files.append((name, None))
        except OSError as error:
            return Unreadable(f"{path} cannot be read: {error.strerror or error}")
    return files


def changed_paths(status: str, repository: Path, workspace: Path) -> list[str]:
    """The uncommitted paths `git status --porcelain -z` names for a repository, the workspace directory left out."""
    return _changed(status, _relative(workspace, repository))


def _changed(status: str, excluded: str | None) -> list[str]:
    return [path for path in _status_paths(status) if not _under(path, excluded)]


def _status_paths(status: str) -> list[str]:
    """Every path that `git status --porcelain -z` names.

    A renamed or copied file takes two fields: the new name after its two status letters, then the old name with
    no letters before it. The fields are read in order, so the old name is kept whole.
    """
    fields = iter(status.split("\0"))
    paths: list[str] = []
    for entry in fields:
        paths.append(entry[3:])
        if TWO_NAMES & set(entry[:2]):
            paths.append(next(fields, ""))
    return [path for path in paths if path]


def _relative(workspace: Path, base: Path) -> str | None:
    """The workspace as a path relative to the base, or None when it lies outside the base."""
    try:
        return workspace.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return None


def _under(name: str, excluded: str | None) -> bool:
    if excluded is None:
        return False
    return excluded in (".", name) or name.startswith(excluded + "/")


def _text(data: bytes) -> str:
    return data.decode("utf-8", errors="surrogateescape")


def _git(directory: Path, *arguments: str) -> subprocess.CompletedProcess[bytes] | str:
    """The finished git call, or the reason git could not be started."""
    try:
        return subprocess.run(
            ["git", "-C", str(directory), *arguments],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return str(getattr(error, "strerror", None) or error)
