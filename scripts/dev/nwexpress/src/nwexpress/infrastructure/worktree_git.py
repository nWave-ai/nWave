"""The git calls a delivery worktree needs: resolving a commit, adding and removing the worktree, deleting its branch at
the tip that was proven, and the facts reclaim reads (uncommitted and ignored paths, commits not integrated into the
trunk by patch equivalence, merge commits).

Every call raises GitHooksError with git's own message when git refuses; nothing is returned as an empty fact.
Deleting a branch is an update-ref with the expected old value: git refuses the deletion when the branch moved after
the proof, so no blind force is used anywhere in this module.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from nwexpress.infrastructure.commit_hooks_git import TIMEOUT_S, GitHooksError


if TYPE_CHECKING:
    from nwexpress.domain.reclaim import DeliveryBranch


def resolve_commit(repository: Path, name: str) -> str | None:
    """The commit a revision names in the repository, or None when it names no commit."""
    completed = _git(
        repository,
        "rev-parse",
        "--verify",
        "--quiet",
        f"{name}^{{commit}}",
        expected=(0, 1),
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.decode("utf-8").strip()


def common_directory(top: Path) -> Path:
    """The repository's common git directory, shared by the primary checkout and every linked worktree."""
    completed = _git(top, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(completed.stdout.decode("utf-8").strip()).resolve()


def current_branch(top: Path) -> str | None:
    """The branch the worktree has checked out, or None when its HEAD is detached."""
    completed = _git(top, "symbolic-ref", "--quiet", "--short", "HEAD", expected=(0, 1))
    if completed.returncode != 0:
        return None
    return completed.stdout.decode("utf-8").strip()


def add_worktree(main: Path, dest: Path, branch: str, commit: str) -> None:
    _git(main, "worktree", "add", "-b", branch, str(dest), commit)


def remove_worktree(main: Path, dest: Path) -> None:
    """Removes the worktree without force: git refuses when it holds changes it would delete."""
    _git(main, "worktree", "remove", str(dest))


def delete_branch(main: Path, branch: DeliveryBranch, tip: str) -> None:
    """Deletes refs/heads/<branch> only while it still points at tip, the commit the proof judged integrated.

    The branch is a DeliveryBranch, which only admission produces for a name that is not a protected trunk branch.
    """
    _git(main, "update-ref", "-d", f"refs/heads/{branch.name}", tip)


def checked_out_elsewhere(top: Path, branch: str) -> tuple[str, ...]:
    """The paths of the other worktrees that have refs/heads/<branch> checked out, from git's own worktree list."""
    completed = _git(top, "worktree", "list", "--porcelain")
    holders: list[str] = []
    path: str | None = None
    for line in completed.stdout.decode("utf-8").splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree ") :]
        elif line == f"branch refs/heads/{branch}" and path is not None:
            if Path(path).resolve() != top.resolve():
                holders.append(path)
    return tuple(holders)


def dirty_paths(top: Path) -> tuple[str, ...]:
    """Paths with uncommitted changes or untracked files, one per path (no rename pairs)."""
    completed = _git(
        top, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames"
    )
    entries = completed.stdout.decode("utf-8").split("\0")
    return tuple(entry[3:] for entry in entries if entry)


def ignored_paths(top: Path) -> tuple[str, ...]:
    """Every ignored file, one per path. A folder is not collapsed: each file's own folder names decide whether it is a cache."""
    completed = _git(
        top,
        "ls-files",
        "-z",
        "--others",
        "--ignored",
        "--exclude-standard",
    )
    return tuple(path for path in completed.stdout.decode("utf-8").split("\0") if path)


def unintegrated_commits(top: Path, trunk: str, branch: str) -> tuple[str, ...]:
    """Commits of the branch with no patch-equivalent commit on the trunk, as git cherry judges patches."""
    completed = _git(top, "cherry", trunk, branch)
    return tuple(
        line.split(" ", 1)[1].strip()
        for line in completed.stdout.decode("utf-8").splitlines()
        if line.startswith("+ ")
    )


def merge_commits(top: Path, trunk: str, branch: str) -> tuple[str, ...]:
    """Merge commits of the branch that the trunk does not hold; git cherry never compares a merge."""
    completed = _git(top, "rev-list", "--merges", f"{trunk}..{branch}")
    return tuple(line for line in completed.stdout.decode("utf-8").split() if line)


def _git(
    repository: Path, *args: str, expected: tuple[int, ...] = (0,)
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *args],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=TIMEOUT_S,
            check=False,
        )
    except OSError as error:
        raise GitHooksError(f"git cannot be run: {error.strerror or error}") from None
    if completed.returncode not in expected:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise GitHooksError(f"git {' '.join(args)} failed: {detail or 'no message'}")
    return completed
