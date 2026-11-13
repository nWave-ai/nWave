"""What a selection says to the one who asked: the list, the notes, the document.

Pure. The command line prints what this module decides; it decides nothing itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from nwave_ai.testrun.refusal import Refusal
from nwave_ai.testrun.selection import Indeterminate, Selected


if TYPE_CHECKING:
    from nwave_ai.testrun.declaration import Depth, SelectionRules


@dataclass(frozen=True)
class Report:
    """The tests to print, the lines for standard error and the JSON document."""

    tests: tuple[str, ...]
    notes: tuple[str, ...]
    document: dict[str, object]


def no_selection_refusal(source: str) -> Refusal:
    return Refusal(
        what=f"no selection of tests is declared in {source}",
        why="where the tests are, which adapter reads which files and how "
        "deep each use goes are the project's to declare; none is assumed",
        how="declare tests.selection in .nwave/config.json, or pass --declaration FILE",
    )


@dataclass(frozen=True)
class DeclaredUse:
    """A use the project declares, with the depth it declares for it."""

    name: str
    depth: Depth


def declared_use(rules: SelectionRules, name: str | None) -> DeclaredUse | Refusal:
    """The named use and its depth, or why no depth can be taken."""
    if name is not None and name in rules.uses:
        return DeclaredUse(name, rules.uses[name])
    return Refusal(
        what="no use was named: --use is required"
        if name is None
        else f"the use '{name}' is not declared",
        why="the depth of the selection is declared per use",
        how=f"pass --use with one of the declared uses: {', '.join(rules.uses)}",
    )


def _no_widest_refusal(result: Indeterminate) -> Refusal:
    undecided = "; ".join(f"{item.path}: {item.reason}" for item in result.undecided)
    return Refusal(
        what=f"the selection is indeterminate and no widest group is declared: "
        f"{undecided}",
        why="a list computed from the decided paths alone would silently "
        "leave out tests of the undecided ones",
        how="declare selection.widest, or a rule for these paths: an "
        "adapter, an asset prefix or a no_tests prefix",
    )


def report(
    result: Selected | Indeterminate, use: DeclaredUse, ceiling: int | None
) -> Report | Refusal:
    """The list and what must be said with it; a refusal when nothing can be listed."""
    indeterminate = isinstance(result, Indeterminate)
    if indeterminate and result.widest is None:
        return _no_widest_refusal(result)
    undecided = result.undecided if indeterminate else ()
    tests = result.tests() if indeterminate else result.tests
    over = ceiling is not None and len(tests) > ceiling
    notes = [f"INDETERMINATE: {item.path}: {item.reason}" for item in undecided]
    if undecided:
        notes.append(
            "INDETERMINATE: the list is the widest declared group, with what the "
            "decided paths reach"
        )
    notes.extend(f"NOTE: no test depends on {item.path}" for item in result.uncovered)
    if over:
        notes.append(
            f"OVER LOCAL CEILING: {len(tests)} tests are selected and the declared "
            f"local ceiling is {ceiling}: send the complete list to the place that "
            "runs the wide groups; do not run it on this machine"
        )
    document = {
        "use": use.name,
        "depth": use.depth.shown(),
        "local_ceiling": ceiling,
        "outcome": "indeterminate" if undecided else "selected",
        "tests": list(tests),
        "reached": list(result.reached if indeterminate else result.tests),
        "added": list(result.added),
        "undecided": [{"path": item.path, "reason": item.reason} for item in undecided],
        "uncovered": [item.path for item in result.uncovered],
        "over_local_ceiling": over,
    }
    return Report(tuple(tests), tuple(notes), document)
