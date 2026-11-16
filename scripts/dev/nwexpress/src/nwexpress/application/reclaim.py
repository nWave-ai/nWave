"""Reclaims one finished delivery. The facts come from git and the decision is the pure one in domain.reclaim; this
module sequences the effects and turns every blocker into a Refusal that says what failed, why, and how to fix it.

The branch is admitted before any other fact is read: a protected trunk branch (the --trunk argument, or the trunk the
configuration names, default master) cannot become a DeliveryBranch, so it cannot reach the deletion. Order of the
removal: the worktree first (git refuses it without force when it holds changes), then the branch at the tip that was
proven integrated (update-ref with the old value), then the workspace folder. Nothing is removed while any blocker
stands; all blockers are reported in one pass.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from nwexpress.domain.reclaim import (
    Blocker,
    BlockerKind,
    DeliveryBranch,
    ReclaimFacts,
    blockers_of,
)
from nwexpress.domain.refusal import Refusal
from nwexpress.infrastructure import commit_hooks_git as git_hooks
from nwexpress.infrastructure import worktree_git
from nwexpress.infrastructure.baseline_store import BaselineStore
from nwexpress.infrastructure.commit_hooks_git import GitHooksError
from nwexpress.infrastructure.lane_settings import configured_trunk
from nwexpress.infrastructure.workspace import Workspace


DEFAULT_TRUNK = "master"


@dataclass(frozen=True)
class ReclaimOutcome:
    removed: tuple[str, ...]
    refusals: tuple[Refusal, ...]


def reclaim_delivery(
    workspace_directory: Path, trunk: str, cache_names: frozenset[str], home: Path
) -> ReclaimOutcome:
    workspace = Workspace(workspace_directory)
    if not workspace.is_initialized():
        raise Refusal(
            what=f"{workspace_directory} is not an initialized workspace",
            why="reclaim removes the delivery a workspace records, and only a workspace names one",
            how="give the workspace folder of a delivery that was started with nwexpress init",
        )
    baseline = BaselineStore(workspace).read()
    if not baseline.is_available or baseline.top is None:
        raise Refusal(
            what=f"the workspace {workspace_directory} records no delivery worktree: {baseline.reason}",
            why="without the worktree on record reclaim cannot tell which folder and branch belong to this delivery",
            how="remove the folder and its branch by hand after checking them with git worktree list, or reclaim a workspace that was initialized from a delivery worktree",
        )
    top = Path(baseline.top)
    if not top.is_dir():
        raise Refusal(
            what=f"the delivery worktree {top} recorded by the workspace is missing",
            why="reclaim removes the worktree and its branch, and neither can be checked without the folder",
            how=f"run git -C <main checkout> worktree prune, then check the branch with git branch --list, and remove {workspace_directory} by hand",
        )
    try:
        if not git_hooks.is_linked_worktree(top):
            raise Refusal(
                what=f"{top} is not a linked worktree, so reclaim will not remove it",
                why="the primary checkout is the single writer of the trunk and is never removed by reclaim",
                how=f"reclaim only the delivery worktrees that nwexpress clone made; {top} is left as it is",
            )
        main = worktree_git.common_directory(top).parent
        branch = worktree_git.current_branch(top)
        if branch is None:
            raise Refusal(
                what=f"the worktree {top} has a detached HEAD, so it names no branch to prove integrated",
                why="reclaim proves that the branch's commits are on the trunk, and a detached HEAD has no branch to prove",
                how=f"check out the delivery branch in {top} with git switch, then run reclaim again",
            )
        if worktree_git.resolve_commit(top, trunk) is None:
            raise Refusal(
                what=f"the trunk {trunk} names no commit of the repository",
                why="reclaim judges integration against the trunk it is given, and an unknown trunk proves nothing",
                how="give the trunk branch of the repository, for example --trunk master, then run reclaim again",
            )
        protected = frozenset({trunk, configured_trunk(main, home) or DEFAULT_TRUNK})
        admitted = DeliveryBranch.admit(branch, protected)
        tip = worktree_git.resolve_commit(top, f"refs/heads/{branch}")
        facts = ReclaimFacts(
            dirty=worktree_git.dirty_paths(top),
            ignored=worktree_git.ignored_paths(top),
            unintegrated=worktree_git.unintegrated_commits(top, trunk, branch),
            merges=worktree_git.merge_commits(top, trunk, branch),
            checked_out_in=worktree_git.checked_out_elsewhere(top, branch),
        )
    except GitHooksError as error:
        raise Refusal(
            what=f"the delivery in {top} cannot be read from git: {error}",
            why="reclaim removes nothing it cannot prove safe to remove",
            how=f"make {top} a readable git worktree (git -C {top} status must succeed), then run reclaim again",
        ) from None
    blockers = blockers_of(facts, cache_names)
    if isinstance(admitted, Blocker):
        blockers = (admitted, *blockers)
    if blockers or not isinstance(admitted, DeliveryBranch):
        return ReclaimOutcome(
            removed=(),
            refusals=tuple(
                _refusal_of(blocker, top, branch, trunk, main) for blocker in blockers
            ),
        )
    assert tip is not None
    try:
        worktree_git.remove_worktree(main, top)
        worktree_git.delete_branch(main, admitted, tip)
    except GitHooksError as error:
        raise Refusal(
            what=f"reclaim stopped while removing the delivery in {top}: {error}",
            why="the steps before this one completed, so what remains is listed by git worktree list and git branch --list",
            how=f"check the worktree and the branch {branch} with git, remove what is left by hand, then remove {workspace_directory}",
        ) from None
    shutil.rmtree(workspace_directory)
    return ReclaimOutcome(
        removed=(
            f"worktree {top}",
            f"branch {branch}",
            f"workspace {workspace_directory}",
        ),
        refusals=(),
    )


def _refusal_of(
    blocker: Blocker, top: Path, branch: str, trunk: str, main: Path
) -> Refusal:
    if blocker.kind is BlockerKind.PROTECTED:
        return Refusal(
            what=f"the delivery branch {blocker.subject} is a protected trunk branch, so reclaim will not delete it",
            why="deleting that branch would delete the trunk ref itself, and every delivery integrates into the trunk",
            how=f"move the delivery's work to a branch of its own with git -C {top} switch -c nwexpress/<delivery name> (this leaves {blocker.subject} untouched), then run reclaim again",
        )
    if blocker.kind is BlockerKind.CHECKED_OUT:
        return Refusal(
            what=f"the delivery branch {branch} is checked out in another worktree at {blocker.subject}",
            why="git refuses to delete a branch that a worktree has checked out, and deleting it here would leave that worktree on a branch that no longer exists",
            how=f"remove that worktree with git -C {main} worktree remove {blocker.subject} after checking it holds nothing to keep, then run reclaim again",
        )
    if blocker.kind is BlockerKind.DIRTY:
        return Refusal(
            what=f"the worktree {top} holds the uncommitted or untracked file {blocker.subject}",
            why="removing the worktree deletes this file, and no commit of the branch holds it",
            how=f"commit {blocker.subject} on {branch} or remove it, then run reclaim again",
        )
    if blocker.kind is BlockerKind.IGNORED:
        return Refusal(
            what=f"the ignored path {blocker.subject} in {top} is not a rebuildable cache",
            why="git removes ignored files silently with the worktree, so this path would be lost",
            how=f"move {blocker.subject} out of the worktree, or, if it is rebuildable, add its folder name to the closed cache list in rebuildable_caches.txt, then run reclaim again",
        )
    if blocker.kind is BlockerKind.UNINTEGRATED:
        short = blocker.subject[:12]
        return Refusal(
            what=f"commit {short} of {branch} is not integrated into {trunk}",
            why="no patch-equivalent commit holds that work on the trunk, so removing the branch would lose it",
            how=f"cherry-pick {short} onto {trunk} in the main checkout, then run reclaim again",
        )
    short = blocker.subject[:12]
    return Refusal(
        what=f"merge commit {short} of {branch} is not held by {trunk}",
        why="git cherry does not compare merge commits, so the trunk may lack the work the merge brings",
        how=f"merge {branch} into {trunk} in the main checkout, or make the delivery linear, then run reclaim again",
    )
