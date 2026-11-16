"""Makes a git work tree carry its commit hooks: the commit-msg and pre-commit hooks a declaring config installs.

The decisions are in nwexpress.domain.commit_hooks; this module sequences the effects and turns every failure into a
Refusal that says WHAT broke, WHY it matters and HOW to fix it. A delivery worktree shares the hook directory of the
main checkout, so one installation serves every worktree.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nwexpress.domain.commit_hooks import (
    HookFile,
    HookOutcome,
    HookPlan,
    changed_names,
    classify,
    installed_outcome,
    is_installed,
    plan_hooks,
)
from nwexpress.domain.refusal import Refusal
from nwexpress.infrastructure import commit_hooks_git as git_hooks
from nwexpress.infrastructure.commit_hooks_git import GitHooksError, GitUnavailable


if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class HookReport:
    """What the hook check did: its outcome, the hook directory it read, whether other worktrees share it, and the names it changed."""

    outcome: HookOutcome
    hooks_dir: Path | None = None
    shared: bool = False
    changed: tuple[str, ...] = ()


def ensure_hooks(root: Path) -> HookReport:
    """Installs the two hooks in a git work tree that declares them; any other root is reported, never changed."""
    try:
        if not git_hooks.inside_work_tree(root):
            return HookReport(HookOutcome.NOT_A_WORK_TREE)
        return _check(root)
    except GitUnavailable:
        return HookReport(HookOutcome.GIT_UNAVAILABLE)
    except GitHooksError as error:
        raise Refusal(
            what=f"the commit hooks of {root} cannot be checked: {error}",
            why="without a readable hook state the tool cannot tell whether commits in this work tree are checked",
            how=f"make {root} a readable git work tree (git -C {root} status must succeed), then run this command again",
        ) from None


def _check(root: Path) -> HookReport:
    declared = git_hooks.declares_hooks(root)
    before = _states(root) if declared else ()
    hooks_path = git_hooks.hooks_path_value(root)
    own_hooks = not declared and bool(
        git_hooks.runnable_hooks(git_hooks.hooks_directory(root))
    )
    plan = plan_hooks(
        before,
        declared=declared,
        hooks_path_set=hooks_path is not None,
        installer_available=git_hooks.installer_available(),
        own_hooks=own_hooks,
    )
    return _act(root, before, plan, hooks_path)


def _act(
    root: Path,
    before: tuple[HookFile, ...],
    plan: HookPlan,
    hooks_path: str | None,
) -> HookReport:
    if plan is HookPlan.NOT_DECLARED:
        return HookReport(HookOutcome.NOT_DECLARED)
    if plan is HookPlan.OWN_HOOKS:
        return HookReport(HookOutcome.OWN_HOOKS_PRESENT)
    if plan is HookPlan.IN_PLACE_HOOKS:
        return HookReport(
            HookOutcome.IN_PLACE_HOOKS_PRESENT,
            hooks_dir=git_hooks.hooks_directory(root),
        )
    if plan is HookPlan.ALREADY_INSTALLED:
        return HookReport(HookOutcome.ALREADY_INSTALLED)
    if plan is HookPlan.HOOKS_PATH_SET:
        raise _hooks_path_refusal(root, hooks_path or "")
    if plan is HookPlan.INSTALLER_MISSING:
        raise _installer_refusal(f"the commit hooks of {root} cannot be installed")
    return _install(root, before)


def _install(root: Path, before: tuple[HookFile, ...]) -> HookReport:
    snapshot = git_hooks.hook_directory_contents(root)
    installed, output = git_hooks.install_hooks(root)
    if not installed:
        raise Refusal(
            what=f"pre-commit install failed in {root}",
            why=f"pre-commit reported: {_last_line(output)}",
            how=f"run 'python -m pre_commit install -t pre-commit -t commit-msg' in {root} with the Python of the repository .venv, fix the error it shows, then run this command again",
        )
    if not is_installed(_states(root)):
        raise Refusal(
            what=f"pre-commit install in {root} did not write both hook files",
            why="a commit-msg or pre-commit file without the pre-commit marker would let commits skip the commit rules",
            how=f"remove the commit-msg and pre-commit files in the hook directory of {root} that pre-commit did not write, then run this command again",
        )
    return HookReport(
        installed_outcome(before),
        hooks_dir=git_hooks.hooks_directory(root),
        shared=git_hooks.worktree_count(root) > 1,
        changed=changed_names(snapshot, git_hooks.hook_directory_contents(root)),
    )


def _states(root: Path) -> tuple[HookFile, ...]:
    return tuple(classify(content) for content in git_hooks.hook_file_contents(root))


def _installer_refusal(subject: str) -> Refusal:
    return Refusal(
        what=f"{subject}: pre_commit is not importable by {sys.executable}",
        why="a commit in a work tree without the commit-msg and pre-commit hooks is not checked by the commit rules, so a delivery must not start there",
        how="install pre-commit into that Python, or run this command with the Python of the repository .venv, which has it, then run the command again",
    )


def _hooks_path_refusal(root: Path, value: str) -> Refusal:
    return Refusal(
        what=f"the commit hooks cannot be installed in {root}: core.hooksPath is set to {value}",
        why="git ignores the hook directory of a work tree whose core.hooksPath is set, so a commit there would skip the commit rules",
        how=f"git -C {root} config --unset-all core.hooksPath (or git config --global --unset-all core.hooksPath for a global setting), then run this command again",
    )


def _last_line(output: str) -> str:
    lines = [line for line in output.splitlines() if line.strip()]
    return lines[-1].strip() if lines else "no output"
