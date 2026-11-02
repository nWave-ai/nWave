"""Selection algebra over declared reach facts, independent of source adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import chain
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


def _ancestry(path: str):
    while path:
        yield path
        path = path.rpartition("/")[0]


class MissingKind(str, Enum):
    ABSENT_FROM_INDEX = "absent-from-index"
    STALE = "stale"
    NON_PYTHON = "non-python"
    UNPARSEABLE = "unparseable"
    UNJUDGED_DYNAMIC_REACH = "unjudged-dynamic-reach"
    INDEX_UNPAIRED = "index-unpaired"
    OUTSIDE_ROOT = "outside-root"
    JUDGMENT_TABLE_UNREADABLE = "judgment-table-unreadable"


@dataclass(frozen=True)
class Missing:
    kind: MissingKind
    path: str

    @property
    def sort_key(self) -> tuple[str, str]:
        return self.kind.value, self.path


@dataclass(frozen=True)
class Judgment:
    test_file: str
    sha256: str
    reaches: frozenset[str]


@dataclass(frozen=True)
class JudgmentTable:
    entries: tuple[Judgment, ...] = ()
    _by_file: Mapping[str, Judgment] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        by_file = {entry.test_file: entry for entry in self.entries}
        if len(by_file) != len(self.entries):
            raise ValueError(
                "two judgments name the same test_file; record one judgment per file"
            )
        object.__setattr__(self, "_by_file", by_file)

    def reaches_of(
        self, path: str, current_sha256: str | None
    ) -> frozenset[str] | None:
        judgment = self._by_file.get(path)
        return (
            judgment.reaches if judgment and judgment.sha256 == current_sha256 else None
        )


def _closure(
    start: Iterable[str], adjacency: Mapping[str, Iterable[str]]
) -> frozenset[str]:
    reached = set(start)
    pending = list(reached)
    while pending:
        for neighbour in adjacency.get(pending.pop(), ()):
            if neighbour not in reached:
                reached.add(neighbour)
                pending.append(neighbour)
    return frozenset(reached)


@dataclass(frozen=True)
class ContentHoldings:
    pairs: frozenset[tuple[str, str]] = frozenset()

    def holders_reached_by(self, changed: Iterable[str]) -> frozenset[str]:
        ancestry = frozenset(chain.from_iterable(_ancestry(path) for path in changed))
        return frozenset(
            holder for holder, content in self.pairs if content in ancestry
        )


@dataclass(frozen=True)
class ReachView:
    test_files: frozenset[str]
    conftest_files: frozenset[str]
    test_tree_files: frozenset[str]
    import_edges: frozenset[tuple[str, str]]
    call_edges: frozenset[tuple[str, str]]
    cli_links: frozenset[tuple[str, str]]
    dynamic_files: frozenset[str]
    unparseable_files: frozenset[str]
    current_digests: Mapping[str, str]
    judgments: JudgmentTable
    table_gap: Missing | None = None
    content_holdings: ContentHoldings = field(default_factory=ContentHoldings)

    def impact_of(self, changed: Iterable[str]) -> frozenset[str]:
        paths = frozenset(changed)
        dependents: dict[str, set[str]] = {}
        for dependent, dependency in self.import_edges | self.call_edges:
            dependents.setdefault(dependency, set()).add(dependent)
        return _closure(
            paths | self.content_holdings.holders_reached_by(paths), dependents
        )

    def _reaches_of(self, path: str) -> frozenset[str] | None:
        return self.judgments.reaches_of(path, self.current_digests.get(path))

    def unjudged_dynamic_files(self) -> frozenset[str]:
        return frozenset(
            path for path in self.dynamic_files if self._reaches_of(path) is None
        )

    def _governing_conftests(self, path: str) -> frozenset[str]:
        return frozenset(
            conftest
            for conftest in self.conftest_files
            if not (directory := conftest.rpartition("/")[0])
            or path.startswith(directory + "/")
        )

    def tests_depending_on(self, files: Iterable[str]) -> frozenset[str]:
        dependents: dict[str, set[str]] = {}
        for dependent, dependency in self.import_edges | self.call_edges:
            if dependent in self.test_tree_files and dependency in self.test_tree_files:
                dependents.setdefault(dependency, set()).add(dependent)
        for path in self.test_tree_files:
            for conftest in self._governing_conftests(path) - {path}:
                dependents.setdefault(conftest, set()).add(path)
        return self.test_files & _closure(files, dependents)

    def static_selection(self, changed: Iterable[str]) -> frozenset[str]:
        impact = self.impact_of(changed)
        launching = {test for test, module in self.cli_links if module in impact}
        judged = {
            path
            for path in self.dynamic_files
            if (self._reaches_of(path) or frozenset()) & impact
        }
        depending = self.tests_depending_on(judged)
        return frozenset(
            test
            for test in self.test_files
            if test in impact
            or test in launching
            or test in depending
            or self._governing_conftests(test) & impact
        )


@dataclass(frozen=True)
class Selected:
    tests: frozenset[str]


@dataclass(frozen=True)
class Indeterminate:
    widened_tests: frozenset[str]
    missing: frozenset[Missing]
    reached_tests: frozenset[str]

    def __post_init__(self) -> None:
        if not self.missing:
            raise ValueError(
                "an indeterminate selection must name what is missing; provide its gaps"
            )
        outside = self.reached_tests - self.widened_tests
        if outside:
            raise ValueError(
                f"reached_tests must stay within widened_tests; {sorted(outside)} "
                "are reached but not widened; include every reached test in widened_tests"
            )


def select(
    changed: Iterable[str], view: ReachView, coverage_missing: frozenset[Missing]
) -> Selected | Indeterminate:
    paths = frozenset(changed)
    unjudged = view.unjudged_dynamic_files()
    missing = coverage_missing | frozenset(
        chain(
            (
                Missing(MissingKind.NON_PYTHON, p)
                for p in paths
                if not p.endswith(".py")
            ),
            (Missing(MissingKind.UNPARSEABLE, p) for p in view.unparseable_files),
            (Missing(MissingKind.UNJUDGED_DYNAMIC_REACH, p) for p in unjudged),
            (view.table_gap,) if view.table_gap else (),
        )
    )
    selection = view.static_selection(paths)
    if not missing:
        return Selected(selection)
    if all(gap.kind == MissingKind.UNJUDGED_DYNAMIC_REACH for gap in missing):
        return Indeterminate(
            selection | view.tests_depending_on(unjudged), missing, selection
        )
    return Indeterminate(view.test_files, missing, selection)
