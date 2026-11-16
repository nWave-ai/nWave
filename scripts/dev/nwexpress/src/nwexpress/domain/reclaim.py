"""Decides which conditions keep one finished delivery from being reclaimed.

Values only: the facts are read from git by infrastructure and passed in. Every unmet precondition is a blocker in
one pass, so a refusal names all of them. Two rules are made structural rather than checked late:

* the branch deletion takes a DeliveryBranch, and a DeliveryBranch can only be admitted for a name that is not a
  protected trunk branch, so the trunk ref cannot reach the deletion path;
* an ignored path is harmless only when one of its folder names is a rebuildable cache: git removes ignored files
  silently with a worktree, so any other ignored path would be lost.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable


class BlockerKind(Enum):
    PROTECTED = "protected"
    CHECKED_OUT = "checked-out"
    DIRTY = "dirty"
    IGNORED = "ignored"
    UNINTEGRATED = "unintegrated"
    MERGE = "merge"


@dataclass(frozen=True)
class Blocker:
    kind: BlockerKind
    subject: str


@dataclass(frozen=True)
class DeliveryBranch:
    """A branch that reclaim may delete. The only way to hold one is admit, which refuses a protected trunk name."""

    name: str

    @classmethod
    def admit(cls, name: str, protected: frozenset[str]) -> DeliveryBranch | Blocker:
        if name in protected:
            return Blocker(BlockerKind.PROTECTED, name)
        return cls(name)


@dataclass(frozen=True)
class ReclaimFacts:
    dirty: tuple[str, ...]
    ignored: tuple[str, ...]
    unintegrated: tuple[str, ...]
    merges: tuple[str, ...]
    checked_out_in: tuple[str, ...]


def blockers_of(
    facts: ReclaimFacts, cache_names: frozenset[str]
) -> tuple[Blocker, ...]:
    """Every blocker of the delivery, in the order: other worktrees holding the branch, dirty paths, ignored non-cache
    paths, unintegrated commits, merges."""
    return (
        *(Blocker(BlockerKind.CHECKED_OUT, path) for path in facts.checked_out_in),
        *(Blocker(BlockerKind.DIRTY, path) for path in facts.dirty),
        *(
            Blocker(BlockerKind.IGNORED, path)
            for path in facts.ignored
            if not is_rebuildable(path, cache_names)
        ),
        *(Blocker(BlockerKind.UNINTEGRATED, commit) for commit in facts.unintegrated),
        *(Blocker(BlockerKind.MERGE, commit) for commit in facts.merges),
    )


def is_rebuildable(path: str, cache_names: Iterable[str]) -> bool:
    """True when one folder name of the path is exactly a rebuildable cache name; a name is matched whole, never by pattern."""
    names = frozenset(cache_names)
    return any(part in names for part in path.split("/") if part)
