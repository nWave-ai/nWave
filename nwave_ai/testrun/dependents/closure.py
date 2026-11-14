"""Which files depend on a set of files, through any number of hops: a pure fold.

A reader answers, for a set of files, the direct dependents of each of them, or a
refusal when it cannot. The closure asks in rounds: one call per round, for every file
reached and not asked before. A wide round is answered for the whole universe of
files at once, because then the rest of the closure is already in the answer. Every
round returns new values; no memo is shared between rounds or between calls. ``reach``
then answers, from the collected edges, how far each start reaches, with its own depth.
"""

from __future__ import annotations

from collections.abc import Callable
from types import MappingProxyType
from typing import TYPE_CHECKING

from nwave_ai.testrun.refusal import Refusal


if TYPE_CHECKING:
    from collections.abc import Mapping

    from nwave_ai.testrun.dependents.edge import DependencyEdge


# A round this wide is cheaper asked of the whole universe once than of each file.
WIDE_ROUND = 64

Reader = Callable[[frozenset[str]], "frozenset[DependencyEdge] | Refusal"]


def collect_edges(
    starts: frozenset[str],
    max_hops: int | None,
    read: Reader,
    universe: frozenset[str],
) -> frozenset[DependencyEdge] | Refusal:
    """Every edge read while following dependents from ``starts`` for ``max_hops`` rounds."""
    asked: frozenset[str] = frozenset()
    frontier, edges, rounds_left = starts, frozenset(), max_hops
    while frontier and rounds_left != 0:
        query = universe if len(frontier) > WIDE_ROUND else frontier
        answer = read(query)
        if isinstance(answer, Refusal):
            return answer
        asked = asked | query
        frontier = frozenset(edge.dependent for edge in answer) - asked
        edges = edges | answer
        rounds_left = None if rounds_left is None else rounds_left - 1
    return edges


def dependents_index(
    edges: frozenset[DependencyEdge],
) -> Mapping[str, frozenset[str]]:
    """The direct dependents of each file that some edge names as a target."""
    grouped: dict[str, set[str]] = {}
    for edge in edges:
        grouped.setdefault(edge.target, set()).add(edge.dependent)
    return MappingProxyType(
        {target: frozenset(found) for target, found in grouped.items()}
    )


def reach(
    start: str, index: Mapping[str, frozenset[str]], hops: int | None
) -> frozenset[str]:
    """Every file within ``hops`` dependency hops of ``start``, itself included."""
    return _walk(index, frozenset({start}), frozenset({start}), hops)


def _walk(
    index: Mapping[str, frozenset[str]],
    seen: frozenset[str],
    frontier: frozenset[str],
    hops_left: int | None,
) -> frozenset[str]:
    if not frontier or hops_left == 0:
        return seen
    step = (
        frozenset(
            dependent for target in frontier for dependent in index.get(target, ())
        )
        - seen
    )
    return _walk(index, seen | step, step, None if hops_left is None else hops_left - 1)
