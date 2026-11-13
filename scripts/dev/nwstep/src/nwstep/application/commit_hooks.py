"""Makes a working clone carry the commit-msg and pre-commit hooks: the check behind prompt and init, and the clone command.

The decisions are in nwstep.domain.commit_hooks; this module sequences the effects and turns every failure into a
Refusal that says WHAT broke, WHY it matters and HOW to fix it.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from nwstep.domain.commit_hooks import (
    HookFile,
    HookOutcome,
    HookPlan,
    classify,
    installed_outcome,
    is_installed,
    plan_hooks,
)
from nwstep.domain.refusal import Refusal
from nwstep.infrastructure import commit_hooks_git as git_hooks
from nwstep.infrastructure.commit_hooks_git import GitHooksError, GitUnavailable


if TYPE_CHECKING:
    from pathlib import Path


NO_HOOKS_OUTCOMES = (
    HookOutcome.NOT_A_WORK_TREE,
    HookOutcome.NOT_DECLARED,
    HookOutcome.GIT_UNAVAILABLE,
)


def ensure_hooks(root: Path) -> HookOutcome:
    """Installs the two hooks in a git work tree that declares them; any other root is reported, never changed."""
    try:
        if not git_hooks.inside_work_tree(root):
            return HookOutcome.NOT_A_WORK_TREE
        return _check(root)
    except GitUnavailable:
        return HookOutcome.GIT_UNAVAILABLE
    except GitHooksError as error:
        raise Refusal(
            what=f"the commit hooks of {root} cannot be checked: {error}",
            why="without a readable hook state the tool cannot tell whether commits in this clone are checked",
            how=f"make {root} a readable git work tree (git -C {root} status must succeed), then run this command again",
        ) from None


def clone_with_hooks(source: str, destination: Path) -> HookOutcome:
    """Clones source into destination and installs the hooks; a clone this call created is removed when that fails."""
    if not git_hooks.installer_available():
        raise _installer_refusal(f"the clone at {destination} was not created")
    created = not destination.exists()
    try:
        git_hooks.clone(source, destination)
    except GitHooksError as error:
        raise Refusal(
            what=f"git clone of {source} into {destination} failed",
            why=f"git reported: {error}; no clone exists, so no hook was installed",
            how=f"check that {source} is a repository git can clone, then run the clone command again",
        ) from None
    try:
        outcome = ensure_hooks(destination)
    except Refusal as refusal:
        raise _without_clone(refusal, destination, created) from None
    if outcome in NO_HOOKS_OUTCOMES:
        raise _without_clone(
            _no_hooks(outcome, source, destination), destination, created
        ) from None
    return outcome


def _check(root: Path) -> HookOutcome:
    declared = git_hooks.declares_hooks(root)
    before = _states(root) if declared else ()
    hooks_path = git_hooks.hooks_path_value(root)
    plan = plan_hooks(
        before,
        declared=declared,
        hooks_path_set=hooks_path is not None,
        installer_available=git_hooks.installer_available(),
    )
    return _act(root, before, plan, hooks_path)


def _act(
    root: Path,
    before: tuple[HookFile, ...],
    plan: HookPlan,
    hooks_path: str | None,
) -> HookOutcome:
    if plan is HookPlan.NOT_DECLARED:
        return HookOutcome.NOT_DECLARED
    if plan is HookPlan.ALREADY_INSTALLED:
        return HookOutcome.ALREADY_INSTALLED
    if plan is HookPlan.HOOKS_PATH_SET:
        raise _hooks_path_refusal(root, hooks_path or "")
    if plan is HookPlan.INSTALLER_MISSING:
        raise _installer_refusal(f"the commit hooks of {root} cannot be installed")
    return _install(root, before)


def _install(root: Path, before: tuple[HookFile, ...]) -> HookOutcome:
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
    return installed_outcome(before)


def _states(root: Path) -> tuple[HookFile, ...]:
    return tuple(classify(content) for content in git_hooks.hook_file_contents(root))


def _no_hooks(outcome: HookOutcome, source: str, destination: Path) -> Refusal:
    if outcome is HookOutcome.NOT_DECLARED:
        return Refusal(
            what=f"the clone at {destination} would carry no commit hooks: {source} has no .pre-commit-config.yaml",
            why="the commit-msg and pre-commit hooks are declared by that config; without it they cannot be installed and commits would not be checked",
            how="clone a repository that declares its commit hooks in .pre-commit-config.yaml, then run the clone command again",
        )
    return Refusal(
        what=f"the clone at {destination} is not a git work tree ({outcome.value})",
        why="a clone that is not a work tree cannot carry commit hooks",
        how=f"check the source {source} and run the clone command again",
    )


def _installer_refusal(subject: str) -> Refusal:
    return Refusal(
        what=f"{subject}: pre_commit is not importable by {sys.executable}",
        why="a commit in a clone without the commit-msg and pre-commit hooks is not checked by the commit rules, so a delivery must not start there",
        how="install pre-commit into that Python, or run this command with the Python of the repository .venv, which has it, then run the command again",
    )


def _hooks_path_refusal(root: Path, value: str) -> Refusal:
    return Refusal(
        what=f"the commit hooks cannot be installed in {root}: core.hooksPath is set to {value}",
        why="git ignores the hook directory of a clone whose core.hooksPath is set, so a commit there would skip the commit rules",
        how=f"git -C {root} config --unset-all core.hooksPath (or git config --global --unset-all core.hooksPath for a global setting), then run this command again",
    )


def _without_clone(refusal: Refusal, destination: Path, created: bool) -> Refusal:
    if not created:
        return Refusal(
            refusal.what,
            f"{refusal.why}; the destination existed before this command, so the clone was left in place without hooks",
            f"run prompt or init with --root {destination} (or with the working directory there), which install the hooks or refuse, before any delivery uses it",
        )
    try:
        git_hooks.remove_tree(destination)
    except OSError as error:
        return Refusal(
            f"{refusal.what}; the clone at {destination} could not be removed: {error.strerror or error}",
            refusal.why,
            f"remove {destination} by hand, then run the clone command again",
        )
    return Refusal(
        refusal.what,
        f"{refusal.why}; the clone was removed, so nothing is left behind",
        refusal.how,
    )


def _last_line(output: str) -> str:
    lines = [line for line in output.splitlines() if line.strip()]
    return lines[-1].strip() if lines else "no output"
