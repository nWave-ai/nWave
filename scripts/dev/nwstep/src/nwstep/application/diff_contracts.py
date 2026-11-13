"""Checks contract items against the change from BASE.

Before craft (oracle, design, model), an item is checked against the working tree, including uncommitted and
untracked files. A witness symbol, a reason's trigger naming and an invariant's witness are only declared then:
they are verified after craft by `verify`, against the committed change. A law or message field declared
after_craft is only parsed before craft: its generator and test names are verified after craft, by selfreview.
Self-review uses `check_locators` and `verify` on the committed change from BASE to HEAD.

When the change cannot be read (no baseline, no git), the parse-level rules still apply and the
diff-level checks are reported as could-not-verify, never as passed.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from nwstep.domain.baseline import Baseline
from nwstep.domain.contract_outcome import ContractOutcome
from nwstep.domain.definitions import Definitions
from nwstep.domain.field import Field
from nwstep.domain.invariant_item import InvariantItem
from nwstep.domain.law_item import LawItem
from nwstep.domain.locator import Locator
from nwstep.domain.message_item import MessageItem
from nwstep.domain.model_witness_item import ModelWitnessItem
from nwstep.domain.prefixed_item import PrefixedItem
from nwstep.domain.self_review_verdict import SelfReviewVerdict
from nwstep.infrastructure.git_diff import GitDiff, GitDiffError

# Contracts whose diff-level part waits for the committed change (after craft).
_DEFERRED = frozenset({"invariant", "model", "stateless"})

# Each keyword a no-state reason must name when the added lines use it.
_TRIGGERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "open(",
        re.compile(r"\bopen\([^,)]*,\s*(?:mode\s*=\s*)?[\"'][^\"']*[wxa+][^\"']*[\"']"),
    ),
    ("os.replace", re.compile(r"\bos\.replace\(")),
    ("flock", re.compile(r"\bflock\b")),
    ("fcntl", re.compile(r"\bfcntl\b")),
    ("msvcrt", re.compile(r"\bmsvcrt\b")),
    ("threading", re.compile(r"\bthreading\b")),
    ("subprocess", re.compile(r"\bsubprocess\b")),
    ("signal", re.compile(r"\b(?:import|from)\s+signal\b|\bsignal\.[A-Za-z_]")),
    ("sqlite", re.compile(r"\bsqlite3?\b")),
    ("write_text", re.compile(r"\.write_text\(")),
)


class DiffContracts:
    DIFF_LINT = "diff_lint"
    NO_STATE_MIN_CHARS = 30

    def __init__(self, baseline: Baseline) -> None:
        self._baseline = baseline

    def check(self, field: Field, items: list[str], root: Path) -> ContractOutcome:
        """A contract field recorded before craft, against the working tree. Deferred parts wait for `verify`; an after_craft field is only parsed."""
        return self._run(
            field.name,
            field.contract or "",
            items,
            root,
            committed=False,
            deferred=field.after_craft,
        )

    def verify(
        self, contract: str, items: list[str], root: Path, *, generated: bool = False
    ) -> ContractOutcome:
        """A contract's items after craft, against the committed change from BASE to HEAD."""
        return self._run(
            contract, contract, items, root, committed=True, generated=generated
        )

    def check_locators(
        self, field: Field, items: list[str], root: Path
    ) -> ContractOutcome:
        """The self-review locators, against the committed change from BASE to HEAD."""
        diff, reason = self._diff(root, committed=True)
        try:
            problems = self._locators(field.locator_ids, items, diff)
        except GitDiffError as error:
            reason = str(error)
            problems = self._locators(field.locator_ids, items, None)
        return ContractOutcome(
            tuple(problems), self._warnings(field.name, reason, True)
        )

    def model_file(self, path: str, root: Path) -> ContractOutcome:
        """The formal model file: a relative .qnt or .tla file that exists and is part of the change (working tree)."""
        problems: list[str] = []
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts:
            problems.append(f"'{path}' must be a relative path inside the root")
        elif pure.suffix not in (".qnt", ".tla"):
            problems.append(f"'{path}' must be a .qnt or .tla model file")
        elif not (root / path).is_file():
            problems.append(f"model file '{path}' does not exist under the root")
        diff, reason = self._diff(root, committed=False)
        if not problems and diff is not None:
            try:
                changed = diff.names()
            except GitDiffError as error:
                reason = str(error)
            else:
                if path not in changed:
                    problems.append(
                        f"model file '{path}' is not part of the change from BASE: write it (uncommitted is fine)"
                    )
        return ContractOutcome(
            tuple(problems), self._warnings("model_file", reason, False)
        )

    def artifact(self, artifact: str, root: Path) -> ContractOutcome:
        """A probe case's artifact: a function or class the committed change defines in a changed Python file."""
        label = f"artifact {artifact}"
        diff, reason = self._diff(root, committed=True)
        if diff is None:
            return ContractOutcome((), self._warnings(label, reason, True))
        try:
            defined = self._defined_in(diff)
        except GitDiffError as error:
            return ContractOutcome((), self._warnings(label, str(error), True))
        if artifact in defined:
            return ContractOutcome(())
        return ContractOutcome(
            (
                f"artifact '{artifact}' is not a function or class defined in a Python file changed from BASE to HEAD",
            )
        )

    def _defined_in(self, diff: GitDiff) -> frozenset[str]:
        names: set[str] = set()
        for path in sorted(name for name in diff.names() if name.endswith(".py")):
            source = diff.text(path)
            if source is None:
                continue
            try:
                names |= Definitions(source).names()
            except ValueError:
                continue
        return frozenset(names)

    def _run(
        self,
        label: str,
        contract: str,
        items: list[str],
        root: Path,
        *,
        committed: bool,
        deferred: bool = False,
        generated: bool = False,
    ) -> ContractOutcome:
        if not committed and (contract in _DEFERRED or deferred):
            problems, _ = self._problems(contract, items, None)
            return ContractOutcome(tuple(problems))
        diff, reason = self._diff(root, committed)
        try:
            problems, lint = self._problems(contract, items, diff, generated)
        except GitDiffError as error:
            reason = str(error)
            problems, lint = self._problems(contract, items, None)
        if contract == "message" and diff is None:
            lint = {"checked": False, "reason": reason}
        return ContractOutcome(
            tuple(problems), self._warnings(label, reason, committed), lint
        )

    def _diff(self, root: Path, committed: bool) -> tuple[GitDiff | None, str | None]:
        reason = self._baseline.unverifiable_for(root)
        if reason is not None:
            return None, reason
        return GitDiff(
            str(self._baseline.top), str(self._baseline.sha), working=not committed
        ), None

    @staticmethod
    def _warnings(label: str, reason: str | None, committed: bool) -> tuple[str, ...]:
        if reason is None:
            return ()
        mode = "committed change from BASE to HEAD" if committed else "working tree"
        return (
            f"'{label}': cannot verify its items against the {mode}: {reason}; "
            "they are recorded as could-not-verify, not as checked",
        )

    def _problems(
        self,
        contract: str,
        items: list[str],
        diff: GitDiff | None,
        generated: bool = False,
    ) -> tuple[list[str], dict[str, object] | None]:
        if contract == "invariant":
            return self._invariants(items, diff), None
        if contract == "model":
            return self._model_witnesses(items, diff), None
        if contract == "stateless":
            return self._stateless(items, diff), None
        if contract == "law":
            return self._generators(items, diff, LawItem, "law", generated), None
        if contract == "message":
            problems = self._generators(items, diff, MessageItem, "message")
            return problems, None if diff is None else self._lint(diff)
        return [], None

    def _invariants(self, items: list[str], diff: GitDiff | None) -> list[str]:
        problems: list[str] = []
        parsed: list[InvariantItem] = []
        for item in items:
            try:
                parsed.append(InvariantItem.parse(item))
            except ValueError as error:
                problems.append(f"'{item}' is not a valid invariant: {error}")
        if diff is None:
            return problems
        changed = diff.names()
        for invariant in parsed:
            path, symbol = invariant.witness_path, invariant.witness_symbol
            if path is None or symbol is None:
                continue
            if path not in changed:
                problems.append(
                    f"{invariant.identifier}: witness path '{path}' is not changed from BASE to HEAD"
                )
            elif not path.endswith(".py"):
                problems.append(
                    f"{invariant.identifier}: witness '{path}' is not a .py file, so its symbol cannot be checked"
                )
            else:
                problems += self._symbol_problems(
                    invariant.identifier, path, symbol, diff
                )
        return problems

    def _model_witnesses(self, items: list[str], diff: GitDiff | None) -> list[str]:
        problems: list[str] = []
        parsed: list[ModelWitnessItem] = []
        for item in items:
            try:
                parsed.append(ModelWitnessItem.parse(item))
            except ValueError as error:
                problems.append(f"'{item}' is not a valid model witness: {error}")
        if diff is None:
            return problems
        changed = diff.names()
        for witness in parsed:
            path = witness.witness_path
            if path not in changed:
                problems.append(
                    f"{witness.identifier}: witness path '{path}' is not changed from BASE to HEAD"
                )
            elif not path.endswith(".py"):
                problems.append(
                    f"{witness.identifier}: witness '{path}' is not a .py file, so its symbol cannot be checked"
                )
            else:
                problems += self._symbol_problems(
                    witness.identifier, path, witness.witness_symbol, diff
                )
        return problems

    def _stateless(self, items: list[str], diff: GitDiff | None) -> list[str]:
        """A reason that the change has no state must be long enough; if the added lines use a trigger, the reason must name it. No reason means nothing to verify."""
        if not items:
            return []
        problems = [
            f"'{item}' is shorter than {self.NO_STATE_MIN_CHARS} characters: say that the change has no state, protocol, concurrency or crash window"
            for item in items
            if len(item.strip()) < self.NO_STATE_MIN_CHARS
        ]
        if diff is None:
            return problems
        text = " ".join(items).lower()
        found: dict[str, str] = {}
        for path in sorted(name for name in diff.names() if name.endswith(".py")):
            source = diff.text(path)
            if source is None:
                continue
            lines = source.splitlines()
            for number in sorted(diff.added_lines(path)):
                if number > len(lines):
                    continue
                line = lines[number - 1]
                for label, pattern in _TRIGGERS:
                    if label not in found and pattern.search(line):
                        found[label] = f"{path}:{number}"
        for label, location in found.items():
            if label.lower() not in text:
                problems.append(
                    f"{location} adds '{label}': a reason that the change has no state must name '{label}' and say what the change does not do with it"
                )
        return problems

    def _symbol_problems(
        self, identifier: str, path: str, symbol: str, diff: GitDiff
    ) -> list[str]:
        source = diff.text(path)
        if source is None:
            return [f"{identifier}: witness path '{path}' has no text at HEAD"]
        try:
            defined = Definitions(source).names()
        except ValueError as error:
            return [f"{identifier}: '{path}' at HEAD {error}"]
        if all(part in defined for part in symbol.split(".")):
            return []
        return [f"{identifier}: symbol '{symbol}' is not defined in '{path}' at HEAD"]

    def _generators(
        self,
        items: list[str],
        diff: GitDiff | None,
        parser: type,
        label: str,
        generated: bool = False,
    ) -> list[str]:
        problems: list[str] = []
        parsed: list[LawItem | MessageItem] = []
        for item in items:
            try:
                parsed.append(parser.parse(item))
            except ValueError as error:
                problems.append(f"'{item}' is not a valid {label}: {error}")
        if diff is None:
            return problems
        tests = self._test_functions(diff)
        properties = self._property_tests(diff) if generated else frozenset()
        for entry in parsed:
            test = entry.generator if isinstance(entry, LawItem) else entry.test
            if test is not None and test not in tests:
                problems.append(
                    f"{entry.identifier}: test '{test}' is not a test function in a test file changed from BASE"
                )
            elif generated and test is not None and test not in properties:
                problems.append(
                    f"{entry.identifier}: test '{test}' is not a property test: decorate it with @given so that its inputs are generated"
                )
        return problems

    def _test_functions(self, diff: GitDiff) -> frozenset[str]:
        names: set[str] = set()
        for path in self._test_files(diff):
            source = diff.text(path)
            if source is None:
                continue
            try:
                names |= Definitions(source).functions()
            except ValueError:
                continue
        return frozenset(names)

    def _property_tests(self, diff: GitDiff) -> frozenset[str]:
        names: set[str] = set()
        for path in self._test_files(diff):
            source = diff.text(path)
            if source is None:
                continue
            try:
                names |= Definitions(source).property_functions()
            except ValueError:
                continue
        return frozenset(names)

    @staticmethod
    def _test_files(diff: GitDiff) -> list[str]:
        return sorted(
            path
            for path in diff.names()
            if path.endswith(".py")
            and (Path(path).name.startswith("test_") or "tests" in Path(path).parts)
        )

    def _lint(self, diff: GitDiff) -> dict[str, object]:
        """Assert messages on added lines of changed test files that look interpolated but are plain literals. Recorded, never a gate."""
        files: list[str] = []
        findings: list[str] = []
        for path in self._test_files(diff):
            source = diff.text(path)
            if source is None:
                continue
            try:
                definitions = Definitions(source)
            except ValueError:
                continue
            files.append(path)
            added = diff.added_lines(path)
            for line, text in definitions.placeholder_asserts():
                if line in added:
                    findings.append(
                        f"{path}:{line}: assert message is a plain literal with a replacement field: {text!r}"
                    )
        return {"checked": True, "files": files, "findings": findings}

    def _locators(
        self, locator_ids: tuple[str, ...], items: list[str], diff: GitDiff | None
    ) -> list[str]:
        problems: list[str] = []
        changed = None if diff is None else diff.names()
        for item in items:
            identifier = PrefixedItem(item).identifier
            if identifier not in locator_ids:
                continue
            try:
                verdict = SelfReviewVerdict.parse(item)
            except ValueError:
                continue
            if verdict.word == SelfReviewVerdict.NOT_APPLICABLE:
                problems.append(
                    f"{identifier} is n/a; {identifier} needs pass or fixed, citing a locator PATH:LINE of an added line"
                )
                continue
            locator = Locator.find(verdict.evidence)
            if locator is None:
                problems.append(
                    f"{identifier} cites no locator PATH:LINE in its evidence"
                )
            elif diff is not None and changed is not None:
                if locator.path not in changed:
                    problems.append(
                        f"{identifier}: locator '{locator.text}' names a file not changed from BASE to HEAD"
                    )
                elif locator.line not in diff.added_lines(locator.path):
                    problems.append(
                        f"{identifier}: locator '{locator.text}' is not an added line of the diff"
                    )
        return problems
