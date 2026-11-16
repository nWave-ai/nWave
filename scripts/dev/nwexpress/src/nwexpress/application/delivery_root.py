"""Admits the root of a delivery command or raises its refusal; the git reads sit behind commit_hooks_git.

Called before any write, hook installation or record, so a refused root is left exactly as it was.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwexpress.domain.delivery_root import RootFacts, root_refusal
from nwexpress.domain.refusal import Refusal
from nwexpress.infrastructure import commit_hooks_git as git_hooks
from nwexpress.infrastructure.commit_hooks_git import GitHooksError


if TYPE_CHECKING:
    from pathlib import Path


def require_delivery_root(root: Path, *, anchor: str | None, command: str) -> None:
    """Raises the refusal when root is neither a clone the clone command made nor a linked worktree, or is not the root init ran in."""
    try:
        top = git_hooks.toplevel(root)
        marker = None if top is None else git_hooks.clone_marker(top)
        linked = top is not None and git_hooks.is_linked_worktree(top)
    except GitHooksError as error:
        raise Refusal(
            what=f"the root {root} cannot be checked as a delivery clone or worktree: {error}",
            why="a delivery admits only a clone the clone command made or a git linked worktree; without a readable git directory the tool cannot tell those from the primary checkout",
            how=f"make {root} a readable git work tree (git -C {root} status must succeed), or make the delivery clone with 'nwexpress clone --source <your checkout> --dest <new directory>', then run {command} from inside it",
        ) from None
    facts = RootFacts(
        root=str(root.resolve() if top is None else top),
        marked=top is not None and marker == str(top),
        anchor=anchor,
        linked=linked,
    )
    refusal = root_refusal(facts, command=command)
    if refusal is not None:
        raise refusal
