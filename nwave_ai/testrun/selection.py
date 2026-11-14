"""Which tests a diff selects: a pure function of the diff and the project.

Given the changed files, what the project declares (``SelectionRules``), the tree
(``Project.files``) and the dependency relation the project's declared command gives
(``relation``), the result is the list of tests, or an explicit ``Indeterminate``
widened as the project declares. Nothing here names a language, a test runner or a
version-control tool: which file depends on which is the declared command's answer.

Rules, per changed path (their union decides the path):

* a test file selects itself;
* another file inside a test root selects the tests of its directory;
* a path under a declared asset prefix selects the tests the project maps it to;
* a path the declared dependents command covers selects the tests that depend on it;
* a path under a declared ``no_tests`` prefix selects nothing, by declaration;
* a path no rule decides makes the selection indeterminate: nothing is guessed.

Depth bounds the dependency hops from a changed file outside the test roots. A
changed file inside a test root is followed to every test that depends on it: test
code's own dependents are cheap and exact. When the relation cannot be read, every
path that needs it is undecided and says why.
"""

from __future__ import annotations

import fnmatch
import posixpath
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from nwave_ai.testrun.dependents.closure import collect_edges, dependents_index, reach
from nwave_ai.testrun.refusal import Refusal


if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from nwave_ai.testrun.declaration import Depth, SelectionRules
    from nwave_ai.testrun.dependents.edge import DependencyEdge


NO_RULE_REASON = (
    "no rule decides this file: no selection.dependents pattern covers it, and no "
    "selection.assets prefix or selection.no_tests prefix names it"
)


@dataclass(frozen=True)
class Project:
    """A project as the selector knows it: its declared rules and its tree."""

    rules: SelectionRules
    files: frozenset[str]


@dataclass(frozen=True)
class Undecided:
    """A changed path no rule decides, and why."""

    path: str
    reason: str


@dataclass(frozen=True)
class Uncovered:
    """A changed path that was decided and reaches no test."""

    path: str
    reason: str


@dataclass(frozen=True)
class Selected:
    """Every changed path was decided: these are the tests."""

    tests: tuple[str, ...]
    added: tuple[str, ...]
    uncovered: tuple[Uncovered, ...]


@dataclass(frozen=True)
class Indeterminate:
    """Some path was not decided.

    ``reached`` is what the decided paths reach, with what was added. ``widest`` is
    the widest group the project declares, or ``None`` when it declares none: then
    there is nothing to fall back to and the caller must refuse.
    """

    reached: tuple[str, ...]
    widest: tuple[str, ...] | None
    added: tuple[str, ...]
    undecided: tuple[Undecided, ...]
    uncovered: tuple[Uncovered, ...]

    def tests(self) -> tuple[str, ...]:
        """The widest group united with what was reached: never fewer tests."""
        return tuple(sorted({*self.reached, *(self.widest or ())}))


@dataclass(frozen=True)
class Unusable:
    """Input the selector cannot use, every defect at once.

    ``outside``: changed paths that do not stay inside the project tree.
    ``not_tests``: paths given to add that are not tests of the project.
    """

    outside: tuple[str, ...]
    not_tests: tuple[str, ...]

    def refusal(self) -> Refusal:
        defects = (
            *(
                f"the changed path '{path}' is not inside the project tree"
                for path in self.outside
            ),
            *(f"'{path}' is not a test of this project" for path in self.not_tests),
        )
        return Refusal(
            what="; ".join(defects),
            why="the selector decides only on files of the tree and adds only tests the "
            "project has",
            how="give changed paths relative to the project root and inside the tree; "
            "with --add give only test files that the declared test_roots and "
            "test_files match",
        )


def normal_path(path: str) -> str | None:
    """The tree-relative spelling of a path, or ``None`` when it leaves the tree."""
    spelled = posixpath.normpath(path.replace("\\", "/"))
    if spelled.startswith(("/", "../")) or spelled == ".." or ":" in spelled[:2]:
        return None
    return spelled


def _under(path: str, directory: str) -> bool:
    directory = directory.rstrip("/")
    return (
        directory in ("", ".") or path == directory or path.startswith(directory + "/")
    )


def _matches(path: str, patterns: Iterable[str]) -> bool:
    """A pattern with a slash matches the whole path; one without matches the name."""
    name = posixpath.basename(path)
    return any(
        fnmatch.fnmatchcase(path if "/" in pattern else name, pattern)
        for pattern in patterns
    )


def _in_test_tree(path: str, rules: SelectionRules) -> bool:
    return any(_under(path, root) for root in rules.test_roots)


def _named_as_test(path: str, rules: SelectionRules) -> bool:
    """A file the project names as a test, wherever it sits."""
    return _matches(path, rules.test_files)


def is_test(path: str, rules: SelectionRules) -> bool:
    """A test of the project: inside a test root, named as the project declares."""
    return _in_test_tree(path, rules) and _named_as_test(path, rules)


def project_tests(files: frozenset[str], rules: SelectionRules) -> frozenset[str]:
    """Every test the project has: this is how the project lists its tests."""
    return frozenset(path for path in files if is_test(path, rules))


def _tests_under(tests: frozenset[str], directories: Iterable[str]) -> frozenset[str]:
    wanted = tuple(directories)
    return frozenset(
        test for test in tests if any(_under(test, directory) for directory in wanted)
    )


def _asset_tests(
    files: Iterable[str], rules: SelectionRules, directories: Iterable[str]
) -> frozenset[str]:
    """Tests under an asset rule's directories, selected without joining the full run."""
    wanted = tuple(directories)
    return frozenset(
        path
        for path in files
        if any(_under(path, directory) for directory in wanted)
        and _named_as_test(path, rules)
    )


def _no_tests(path: str, rules: SelectionRules) -> bool:
    return any(path.startswith(prefix) for prefix in rules.no_tests)


def _covered(path: str, rules: SelectionRules) -> bool:
    """A file the declared dependents command answers for."""
    return rules.dependents is not None and _matches(path, rules.dependents.covers)


def _asset_directories(path: str, rules: SelectionRules) -> tuple[str, ...] | None:
    return next(
        (mapped for prefix, mapped in rules.assets if path.startswith(prefix)), None
    )


def _needs_relation(path: str, rules: SelectionRules) -> bool:
    """A path decided by a rule whose reach to dependents is read from the relation."""
    if _no_tests(path, rules):
        return False
    return (
        _in_test_tree(path, rules)
        or _covered(path, rules)
        or _asset_directories(path, rules) is not None
    )


def _could_not_verify(refusal: Refusal) -> str:
    return f"WHAT: {refusal.what}; WHY: {refusal.why}; HOW: {refusal.how}"


def _decided(
    path: str,
    depth: Depth,
    project: Project,
    tests: frozenset[str],
    index: Mapping[str, frozenset[str]],
) -> frozenset[str] | Undecided | Uncovered:
    """The tests one changed path selects, or why it selects none or is not decided."""
    rules = project.rules
    if _no_tests(path, rules):
        return frozenset()
    selected: set[str] = set()
    inside = _in_test_tree(path, rules)
    asset_directories = _asset_directories(path, rules)
    if not (inside or _covered(path, rules) or asset_directories is not None):
        return Undecided(path, NO_RULE_REASON)
    if inside and not is_test(path, rules):
        # A helper, a fixture or data beside tests conditions the tests around it.
        selected |= _tests_under(tests, [posixpath.dirname(path)])
    if asset_directories is not None:
        selected |= _asset_tests(project.files, rules, asset_directories)
    selected |= reach(path, index, None if inside else depth.hops) & tests
    if not selected and not inside and asset_directories is None:
        return Uncovered(path, "no test depends on it")
    return frozenset(selected)


_NO_EDGES: Mapping[str, frozenset[str]] = MappingProxyType({})


def select_tests(
    changed: Iterable[str],
    added: Iterable[str],
    depth: Depth,
    project: Project,
    relation: Callable[[frozenset[str]], frozenset[DependencyEdge] | Refusal],
) -> Selected | Indeterminate | Unusable:
    """The tests to run for ``changed``, united with ``added``; nothing is removed.

    ``relation`` answers the direct dependents of the files it is asked about, in
    rounds, and only for the paths that need dependents.
    """
    rules = project.rules
    spelled = {path: normal_path(path) for path in changed}
    extra = {path: normal_path(path) for path in added}
    tests = project_tests(project.files, rules)
    outside = tuple(sorted(path for path, normal in spelled.items() if normal is None))
    not_tests = tuple(sorted(path for path, test in extra.items() if test not in tests))
    if outside or not_tests:
        return Unusable(outside, not_tests)
    paths = sorted(set(spelled.values()))
    needing = frozenset(path for path in paths if _needs_relation(path, rules))
    hops = None if any(_in_test_tree(path, rules) for path in needing) else depth.hops
    universe = project.files | frozenset(paths)
    answer = collect_edges(needing, hops, relation, universe)
    failure = answer if isinstance(answer, Refusal) else None
    index = _NO_EDGES if failure is not None else dependents_index(answer)
    decisions = [
        Undecided(path, _could_not_verify(failure))
        if failure is not None and path in needing
        else _decided(path, depth, project, tests, index)
        for path in paths
    ]
    undecided = tuple(item for item in decisions if isinstance(item, Undecided))
    uncovered = tuple(item for item in decisions if isinstance(item, Uncovered))
    joined = tuple(sorted(set(extra.values())))
    reached = tuple(
        sorted(
            {test for item in decisions if isinstance(item, frozenset) for test in item}
            | set(joined)
        )
    )
    if not undecided:
        return Selected(reached, joined, uncovered)
    widest = tuple(sorted(_tests_under(tests, rules.widest))) if rules.widest else None
    return Indeterminate(reached, widest, joined, undecided, uncovered)
