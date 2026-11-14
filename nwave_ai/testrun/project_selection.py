"""Select the tests of a change in a project: the one wiring of the selector's steps.

The CLI and the commit gate both call this. It reads the tree once, prepares the
declared dependents command (run in rounds, and only when a path needs dependents, by
``select_tests``) and hands both to the pure ``selection.select_tests``. A project that
declares no command gets an empty answer: its files are then decided by the other
declared rules only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwave_ai.testrun.dependents.command import DependentsCommand
from nwave_ai.testrun.project_tree import read_project
from nwave_ai.testrun.selection import Project, select_tests


if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from nwave_ai.testrun.declaration import Depth, SelectionRules
    from nwave_ai.testrun.dependents.edge import DependencyEdge
    from nwave_ai.testrun.refusal import Refusal
    from nwave_ai.testrun.selection import Indeterminate, Selected, Unusable


def _no_relation(targets: frozenset[str]) -> frozenset[DependencyEdge]:
    return frozenset()


def select_in_project(
    root: Path,
    rules: SelectionRules,
    changed: Iterable[str],
    added: Iterable[str],
    depth: Depth,
) -> Selected | Indeterminate | Unusable:
    """The tests the change selects in the project at ``root``, under its declared rules."""
    changed = tuple(changed)
    added = tuple(added)
    files = read_project(root, rules)
    relation: Callable[[frozenset[str]], frozenset[DependencyEdge] | Refusal] = (
        _no_relation
    )
    if rules.dependents is not None:
        # The command reads the tree; a changed path that was deleted is not in it, and
        # is named to the command as a target only.
        relation = DependentsCommand(rules.dependents, root, files)
    return select_tests(changed, added, depth, Project(rules, files), relation)
