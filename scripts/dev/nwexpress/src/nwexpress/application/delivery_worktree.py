"""Makes a delivery as a git linked worktree: a branch of its own at the declared base commit, sharing the repository,
its hook directory and the trunk guard with the main checkout.

The order is the design. Every refusal that can be decided from reads is decided before the first write: the target,
the storage policy, a core.hooksPath that would move the hook directory, and a foreign reference-transaction hook. Then
the worktree is added. Then the commit hooks and the trunk guard are installed. A failure after the worktree exists
rolls back exactly what this call created: the worktree, its branch, and the commit-hook files that were absent before.
So a refused clone leaves no worktree, no branch and no guard behind.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nwexpress.application.commit_hooks import ensure_hooks
from nwexpress.application.storage_guard import admit_directory
from nwexpress.domain.reclaim import DeliveryBranch
from nwexpress.domain.refusal import Refusal
from nwexpress.infrastructure import commit_hooks_git as git_hooks
from nwexpress.infrastructure import worktree_git
from nwexpress.infrastructure.commit_hooks_git import GitHooksError
from nwexpress.infrastructure.storage_settings import read_storage_policy
from nwexpress.infrastructure.trunk_guard import check_trunk_guard, install_trunk_guard


if TYPE_CHECKING:
    from nwexpress.application.commit_hooks import HookReport


@dataclass(frozen=True)
class DeliveryWorktree:
    dest: Path
    branch: str
    commit: str
    hooks: HookReport
    warnings: tuple[str, ...]


def make_delivery_worktree(
    source: str,
    base: str,
    dest: Path,
    *,
    environ: dict[str, str],
    home: Path,
) -> DeliveryWorktree:
    main = _main_checkout(source)
    commit = _base_commit(main, base)
    if dest.exists():
        raise Refusal(
            what=f"the destination {dest} already exists, so no delivery worktree can be made there",
            why="a delivery is made in a new folder; an existing folder may hold work that a worktree would not own",
            how=f"give a new destination folder with --dest, or remove {dest} after checking it with git -C {dest} status",
        )
    policy = read_storage_policy(main, home, environ)
    warnings = admit_directory(
        dest,
        policy=policy,
        command="clone",
        configuration=main / ".nwave" / "config.json",
    )
    _refuse_hooks_path(main)
    check_trunk_guard(main)
    hooks_before = _commit_hook_contents(main)
    branch = f"nwexpress/{dest.name}"
    try:
        worktree_git.add_worktree(main, dest, branch, commit)
    except GitHooksError as error:
        raise Refusal(
            what=f"git could not add the worktree {dest} on branch {branch} at {base}: {error}",
            why="a delivery worktree needs a new branch of its own at the declared base; git refuses when the branch exists or the path is taken",
            how=f"give a destination whose name is not already a branch, or delete the stale branch {branch} after checking it with git branch --list, then run the clone command again",
        ) from None
    try:
        hooks = ensure_hooks(dest)
        install_trunk_guard(main)
    except Refusal:
        _roll_back(main, dest, branch, commit, hooks_before)
        raise
    except OSError as error:
        _roll_back(main, dest, branch, commit, hooks_before)
        raise Refusal(
            what=f"the trunk guard cannot be written in the hook directory of {main}: {error.strerror or error}",
            why="without the guard an accidental trunk update from a delivery worktree is not refused, so the delivery is not made",
            how=f"make the hook directory of {main} writable, then run the clone command again",
        ) from None
    return DeliveryWorktree(
        dest=dest.resolve(),
        branch=branch,
        commit=commit,
        hooks=hooks,
        warnings=warnings,
    )


def _refuse_hooks_path(main: Path) -> None:
    """Refuses, before any write, a repository whose core.hooksPath would move the hook directory: globally or locally."""
    try:
        value = git_hooks.hooks_path_value(main)
    except GitHooksError as error:
        raise Refusal(
            what=f"core.hooksPath of {main} cannot be read: {error}",
            why="the trunk guard is written into the hook directory, and that directory is known only when git says whether core.hooksPath moves it",
            how=f"make git -C {main} config --get core.hooksPath succeed, then run the clone command again",
        ) from None
    if value is None:
        return
    raise Refusal(
        what=f"the delivery cannot be made: core.hooksPath is set to {value}, so the trunk guard would be written into a hook directory the tool does not own",
        why="that directory can be shared with other repositories (a global setting shares it with every repository on the machine), and a guard written there makes git init and git clone fail for all of them",
        how=f"unset it with git -C {main} config --local --unset core.hooksPath, or git config --global --unset core.hooksPath, then run the clone command again",
    )


def _main_checkout(source: str) -> Path:
    top = git_hooks.toplevel(Path(source))
    if top is None:
        raise Refusal(
            what=f"the source {source} is not a git checkout",
            why="a delivery worktree is made from a repository on this machine, so the source must be its checkout",
            how="give the path of a git checkout with --source, for example the repository root of your working copy",
        )
    try:
        return worktree_git.common_directory(top).parent
    except GitHooksError as error:
        raise Refusal(
            what=f"the git directory of {source} cannot be read: {error}",
            why="the worktree is added to the repository that the common git directory names",
            how=f"check that git -C {source} rev-parse --git-common-dir succeeds, then run the clone command again",
        ) from None


def _base_commit(main: Path, base: str) -> str:
    commit = worktree_git.resolve_commit(main, base)
    if commit is None:
        raise Refusal(
            what=f"the base {base} names no commit of {main}",
            why="the delivery starts at the declared base commit, and a revision that names none cannot be checked out",
            how=f"give a revision of {main} that names a commit, for example --base HEAD, then run the clone command again",
        )
    return commit


def _commit_hook_contents(main: Path) -> tuple[bytes | None, ...]:
    try:
        return git_hooks.hook_file_contents(main)
    except GitHooksError as error:
        raise Refusal(
            what=f"the commit hooks of {main} cannot be read: {error}",
            why="the clone records which commit-hook files existed before it, so that a refusal can remove only what it wrote",
            how=f"make git -C {main} rev-parse --git-path hooks succeed, then run the clone command again",
        ) from None


def _roll_back(
    main: Path,
    dest: Path,
    branch: str,
    commit: str,
    hooks_before: tuple[bytes | None, ...],
) -> None:
    """Removes what this call created: the commit-hook files it wrote, then the worktree and its branch."""
    try:
        git_hooks.remove_hooks_created(main, hooks_before)
        worktree_git.remove_worktree(main, dest)
        created = DeliveryBranch.admit(branch, frozenset())
        if isinstance(created, DeliveryBranch):
            worktree_git.delete_branch(main, created, commit)
    except GitHooksError as error:
        raise Refusal(
            what=f"the rollback of the worktree {dest} stopped: {error}",
            why="the commit hooks or the worktree of the refused clone could not be removed, so something was left in place",
            how=f"remove {dest} with git -C {main} worktree remove {dest}, and the branch {branch} with git -C {main} branch -d {branch}, then run the clone command again",
        ) from None
