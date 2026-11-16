"""Effects of the commit hook check: git reads of the work tree, the hook directory and core.hooksPath, the declaring
config file, and the pre-commit install. Every failure raises GitHooksError (GitUnavailable when git itself cannot
run) with its reason; nothing is returned as an empty fact.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from nwexpress.domain.commit_hooks import HOOK_TYPES
from nwexpress.domain.delivery_root import MARKER_KEY
from nwexpress.domain.source_hooks import SourceHook, runnable


TIMEOUT_S = 300
CONFIG_NAME = ".pre-commit-config.yaml"
INSTALL_ARGUMENTS = tuple(argument for hook in HOOK_TYPES for argument in ("-t", hook))


class GitHooksError(Exception):
    """A git or pre-commit effect could not run or failed; the message is the reason."""


class GitUnavailable(GitHooksError):
    """The git executable cannot be started at all."""


def inside_work_tree(root: Path) -> bool:
    completed = _git(root, "rev-parse", "--is-inside-work-tree")
    return completed.returncode == 0 and completed.stdout.strip() == b"true"


def declares_hooks(root: Path) -> bool:
    return (root / CONFIG_NAME).is_file()


def hooks_directory(root: Path) -> Path:
    completed = _git(root, "rev-parse", "--git-path", "hooks")
    _require(completed, f"the hook directory of {root} cannot be read")
    return (root / completed.stdout.decode("utf-8").strip()).resolve()


def hooks_path_value(root: Path) -> str | None:
    completed = _git(root, "config", "--get", "core.hooksPath")
    if completed.returncode == 1:
        return None
    _require(completed, f"core.hooksPath of {root} cannot be read")
    return completed.stdout.decode("utf-8").strip()


def hook_file_contents(root: Path) -> tuple[bytes | None, ...]:
    directory = hooks_directory(root)
    return tuple(_read_or_none(directory / name) for name in HOOK_TYPES)


def read_hooks(directory: Path) -> tuple[SourceHook, ...]:
    """Every regular file in directory with its permission bits and bytes; a directory that does not exist holds none."""
    if not directory.is_dir():
        return ()
    try:
        return tuple(
            SourceHook(
                name=path.name,
                mode=path.stat().st_mode & 0o7777,
                content=path.read_bytes(),
            )
            for path in sorted(directory.iterdir())
            if path.is_file()
        )
    except OSError as error:
        raise GitHooksError(
            f"the hook directory {directory} cannot be read: {error.strerror or error}"
        ) from None


def runnable_hooks(directory: Path) -> tuple[SourceHook, ...]:
    """The commit hooks in directory that git would run: executable, not a sample, and of a commit hook type.

    The trunk guard is a reference-transaction hook of nwexpress's own and is not a commit hook of the project.
    """
    return tuple(
        hook for hook in runnable(read_hooks(directory)) if hook.name in HOOK_TYPES
    )


def installer_available() -> bool:
    return importlib.util.find_spec("pre_commit") is not None


def hook_directory_contents(root: Path) -> dict[str, bytes]:
    """The bytes of every regular file in the hook directory of root, by name: the snapshot an install is measured by."""
    return {hook.name: hook.content for hook in read_hooks(hooks_directory(root))}


def worktree_count(root: Path) -> int:
    """How many worktrees the repository of root has, the primary checkout included."""
    completed = _git(root, "worktree", "list", "--porcelain")
    _require(completed, f"the worktrees of {root} cannot be listed")
    return sum(
        1
        for line in completed.stdout.decode("utf-8").splitlines()
        if line.startswith("worktree ")
    )


def install_hooks(root: Path) -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, "-m", "pre_commit", "install", *INSTALL_ARGUMENTS],
        cwd=root,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=TIMEOUT_S,
        check=False,
    )
    return completed.returncode == 0, (completed.stdout + completed.stderr).strip()


def toplevel(root: Path) -> Path | None:
    """The resolved toplevel of the work tree holding root, or None when root is not inside one."""
    completed = _git(root, "rev-parse", "--show-toplevel")
    if completed.returncode != 0:
        return None
    return Path(completed.stdout.decode("utf-8").strip()).resolve()


def is_linked_worktree(top: Path) -> bool:
    """True when top is a linked worktree: its git directory is not the common directory the primary checkout uses."""
    completed = _git(top, "rev-parse", "--git-dir", "--git-common-dir")
    _require(completed, f"the git directories of {top} cannot be read")
    lines = completed.stdout.decode("utf-8").splitlines()
    if len(lines) != 2:
        raise GitHooksError(
            f"the git directories of {top} cannot be read: git printed {len(lines)} lines, expected 2"
        )
    git_dir, common_dir = ((top / line).resolve() for line in lines)
    return git_dir != common_dir


def clone_marker(top: Path) -> str | None:
    """The delivery marker of top, written by the full-clone route of earlier deliveries; None when none is written."""
    completed = _git(top, "config", "--local", "--get", MARKER_KEY)
    if completed.returncode == 1:
        return None
    _require(completed, f"the delivery marker of {top} cannot be read")
    return completed.stdout.decode("utf-8").strip()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=TIMEOUT_S,
            check=False,
        )
    except OSError as error:
        raise GitUnavailable(f"git cannot be run: {error.strerror or error}") from None


def _require(completed: subprocess.CompletedProcess[bytes], reason: str) -> None:
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise GitHooksError(f"{reason}: {detail or 'git exited without a message'}")


def _read_or_none(path: Path) -> bytes | None:
    if not path.is_file():
        return None
    return path.read_bytes()


def remove_hooks_created(root: Path, before: tuple[bytes | None, ...]) -> None:
    """Removes each commit-hook file that was absent before the call and is present now; a file that existed is kept.

    before is the hook_file_contents of root taken before the call, in HOOK_TYPES order.
    """
    directory = hooks_directory(root)
    for name, content in zip(HOOK_TYPES, before, strict=True):
        path = directory / name
        if content is None and path.is_file():
            path.unlink()
