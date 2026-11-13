"""Which tests a diff selects: a pure function of the diff and the project.

Given the changed files, what the project declares (``SelectionRules``), the tree as
read once (``ProjectSnapshot``) and the dependency adapters this version has, the
result is the list of tests, or an explicit ``Indeterminate`` widened as the project
declares. Nothing here names a language, a test runner or a version-control tool:
how a file's dependencies are computed is an adapter's business, behind
``DependencyAdapter``.

Rules, per changed path (their union decides the path):

* a test file selects itself;
* another file inside a test root selects the tests of its directory;
* a path under a declared asset prefix selects the tests the project maps it to;
* a path whose file type has an adapter selects the tests that depend on it;
* a path under a declared ``no_tests`` prefix selects nothing, by declaration;
* a path no rule decides makes the selection indeterminate: nothing is guessed.

Depth bounds the dependency hops from a changed file outside the test roots. A
changed file inside a test root is followed to every test that depends on it: test
code's own dependents are cheap and exact.
"""

from __future__ import annotations

import fnmatch
import posixpath
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from nwave_ai.testrun.refusal import Refusal


if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from nwave_ai.testrun.declaration import Depth, SelectionRules


# Up to this many files are looked up one by one with the adapter's cheap textual
# pre-check; beyond it every dependency is computed once and indexed. Either way the
# answer is the same: the pre-check only skips files that cannot hold a dependency.
_ONE_BY_ONE = 12


class DependencyAdapter(Protocol):
    """How the files of one language depend on each other."""

    def dependencies(
        self,
        path: str,
        text: str,
        files: frozenset[str],
        settings: Mapping[str, object],
    ) -> frozenset[str] | None:
        """The files ``path`` depends on; ``None`` when its text cannot be read."""

    def may_reference(
        self, path: str, text: str, target: str, settings: Mapping[str, object]
    ) -> bool:
        """False only when ``path`` cannot depend on ``target``; cheap."""

    def setting_defects(self, settings: Mapping[str, object]) -> tuple[str, ...]:
        """Every declared setting the adapter does not know or cannot use."""


@dataclass(frozen=True)
class ProjectSnapshot:
    """The tree as read once: every file path, and the text of the readable ones."""

    files: frozenset[str]
    texts: Mapping[str, str]


@dataclass(frozen=True)
class Project:
    """A project as the selector knows it: its rules, its tree, the adapters at hand."""

    rules: SelectionRules
    snapshot: ProjectSnapshot
    adapters: Mapping[str, DependencyAdapter]

    def adapter_of(self, path: str) -> DependencyAdapter | None:
        """The adapter that reads this file's dependencies, if declared and at hand."""
        name = self.rules.adapters.get(_extension(path))
        return None if name is None else self.adapters.get(name)


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
    ``settings``: declared adapter settings the adapter cannot use.
    """

    outside: tuple[str, ...]
    not_tests: tuple[str, ...]
    settings: tuple[str, ...] = ()

    def refusal(self) -> Refusal:
        defects = (
            *(
                f"the changed path '{path}' is not inside the project tree"
                for path in self.outside
            ),
            *(f"'{path}' is not a test of this project" for path in self.not_tests),
            *(f"{defect}" for defect in self.settings),
        )
        return Refusal(
            what="; ".join(defects),
            why="the selector decides only on files of the tree, adds only tests the "
            "project has, and computes dependencies only with settings it understands",
            how="give changed paths relative to the project root and inside the tree; "
            "with --add give only test files that the declared test_roots and "
            "test_files match; correct the adapter settings in the declaration",
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


def _in_test_tree(path: str, rules: SelectionRules) -> bool:
    return any(_under(path, root) for root in rules.test_roots)


def _named_as_test(path: str, rules: SelectionRules) -> bool:
    """A file the project names as a test, wherever it sits."""
    name = posixpath.basename(path)
    return any(
        fnmatch.fnmatchcase(path if "/" in pattern else name, pattern)
        for pattern in rules.test_files
    )


def is_test(path: str, rules: SelectionRules) -> bool:
    """A test of the project: inside a test root, named as the project declares."""
    return _in_test_tree(path, rules) and _named_as_test(path, rules)


def project_tests(snapshot: ProjectSnapshot, rules: SelectionRules) -> frozenset[str]:
    """Every test the project has: this is how the project lists its tests."""
    return frozenset(path for path in snapshot.files if is_test(path, rules))


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


class _Dependents:
    """Who depends on a file. Each file's dependencies are computed at most once."""

    def __init__(self, project: Project, known: frozenset[str]) -> None:
        self._texts = project.snapshot.texts
        self._rules = project.rules
        self._known = known
        self._readable = {
            path: adapter
            for path in sorted(project.snapshot.texts)
            if (adapter := project.adapter_of(path)) is not None
        }
        self._forward: dict[str, frozenset[str] | None] = {}
        self._asked: dict[str, frozenset[str]] = {}
        self._index: dict[str, set[str]] | None = None

    def _settings(self, path: str) -> Mapping[str, object]:
        return self._rules.settings_of(self._rules.adapters[_extension(path)])

    def _dependencies(self, path: str) -> frozenset[str] | None:
        if path not in self._forward:
            self._forward[path] = self._readable[path].dependencies(
                path, self._texts[path], self._known, self._settings(path)
            )
        return self._forward[path]

    def _depends(self, path: str, target: str) -> bool:
        if path == target:
            return False
        may = self._readable[path].may_reference(
            path, self._texts[path], target, self._settings(path)
        )
        if not may:
            return False
        found = self._dependencies(path)
        # An unreadable file may depend on anything its text can name.
        return True if found is None else target in found

    def _indexed(self) -> dict[str, set[str]]:
        if self._index is None:
            index: dict[str, set[str]] = {}
            for path in self._readable:
                for target in self._dependencies(path) or ():
                    index.setdefault(target, set()).add(path)
            self._index = index
        return self._index

    def of(self, target: str) -> frozenset[str]:
        """The files that depend directly on ``target``."""
        if target not in self._asked:
            if len(self._asked) < _ONE_BY_ONE and self._index is None:
                found = {path for path in self._readable if self._depends(path, target)}
            else:
                found = set(self._indexed().get(target, ()))
                found.update(
                    path
                    for path, known in self._forward.items()
                    if known is None and self._depends(path, target)
                )
                found.discard(target)
            self._asked[target] = frozenset(found)
        return self._asked[target]

    def reach(self, start: str, hops: int | None) -> frozenset[str]:
        """Every file within ``hops`` dependency hops of ``start``, itself included."""
        seen, frontier, hop = {start}, {start}, 0
        while frontier and (hops is None or hop < hops):
            frontier = {
                path for target in sorted(frontier) for path in self.of(target)
            } - seen
            seen |= frontier
            hop += 1
        return frozenset(seen)


def _extension(path: str) -> str:
    return posixpath.splitext(path)[1]


def _why_undecided(path: str, rules: SelectionRules) -> str:
    extension = _extension(path)
    kind = f"'{extension}' files" if extension else "files without an extension"
    declared = rules.adapters.get(extension)
    if declared is None:
        return f"no dependency adapter is declared for {kind}"
    return (
        f"the dependency adapter '{declared}' declared for {kind} is not "
        "available in this version"
    )


def _decided(
    path: str,
    depth: Depth,
    project: Project,
    tests: frozenset[str],
    dependents: _Dependents,
) -> frozenset[str] | Undecided | Uncovered:
    """The tests one changed path selects, or why it selects none or is not decided."""
    rules = project.rules
    if any(path.startswith(prefix) for prefix in rules.no_tests):
        return frozenset()
    selected: set[str] = set()
    inside = _in_test_tree(path, rules)
    asset_directories = next(
        (mapped for prefix, mapped in rules.assets if path.startswith(prefix)), None
    )
    if not (inside or project.adapter_of(path) or asset_directories is not None):
        return Undecided(path, _why_undecided(path, rules))
    if inside and not is_test(path, rules):
        # A helper, a fixture or data beside tests conditions the tests around it.
        selected |= _tests_under(tests, [posixpath.dirname(path)])
    if asset_directories is not None:
        selected |= _asset_tests(project.snapshot.files, rules, asset_directories)
    selected |= dependents.reach(path, None if inside else depth.hops) & tests
    if not selected and not inside and asset_directories is None:
        return Uncovered(path, "no test depends on it")
    return frozenset(selected)


def select_tests(
    changed: Iterable[str], added: Iterable[str], depth: Depth, project: Project
) -> Selected | Indeterminate | Unusable:
    """The tests to run for ``changed``, united with ``added``; nothing is removed."""
    rules = project.rules
    spelled = {path: normal_path(path) for path in changed}
    extra = {path: normal_path(path) for path in added}
    tests = project_tests(project.snapshot, rules)
    outside = tuple(sorted(path for path, normal in spelled.items() if normal is None))
    not_tests = tuple(sorted(path for path, test in extra.items() if test not in tests))
    settings = tuple(
        f"selection.{name}.{defect}"
        for name in sorted(set(rules.adapters.values()) & set(project.adapters))
        for defect in project.adapters[name].setting_defects(rules.settings_of(name))
    )
    if outside or not_tests or settings:
        return Unusable(outside, not_tests, settings)
    paths = sorted(set(spelled.values()))
    dependents = _Dependents(project, project.snapshot.files | set(paths))
    decisions = [_decided(path, depth, project, tests, dependents) for path in paths]
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
