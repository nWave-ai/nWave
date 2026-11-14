"""Checks contract items against the change from BASE.

Before craft (oracle, design, model), an item is checked against the working tree, including uncommitted and untracked
files. A witness symbol, a reason's trigger naming and an invariant's witness are only declared then: they are verified
after craft by `verify`, against the committed change. A law or message field declared after_craft is only parsed before
craft: its generator and test names are verified after craft, by selfreview, against the test files the oracle declared.
Self-review uses `check_locators` and `verify` on the committed change from BASE to HEAD.

A symbol is found as a whole word in the text of a file the change touched, whatever the file's language. A generated
law's generation cannot be observed in every language, so it is stated as could-not-verify, never as passed.
When the change cannot be read (no baseline, no git), the parse-level rules still apply and the diff-level checks are
reported as could-not-verify, never as passed.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from nwstep.domain.baseline import Baseline
from nwstep.domain.contract_outcome import ContractOutcome
from nwstep.domain.field import Field
from nwstep.domain.invariant_item import InvariantItem
from nwstep.domain.law_item import LawItem
from nwstep.domain.locator import Locator
from nwstep.domain.message_item import MessageItem
from nwstep.domain.model_witness_item import ModelWitnessItem
from nwstep.domain.prefixed_item import PrefixedItem
from nwstep.domain.self_review_verdict import SelfReviewVerdict
from nwstep.domain.state_trigger import StateTrigger
from nwstep.domain.symbol_text import SymbolText
from nwstep.infrastructure.git_diff import GitDiff, GitDiffError

# Contracts whose diff-level part waits for the committed change (after craft).
_DEFERRED = frozenset({"invariant", "model", "stateless"})


class DiffContracts:
    NO_STATE_MIN_CHARS = 30

    def __init__(self, baseline: Baseline) -> None:
        self._baseline = baseline

    def check(
        self,
        field: Field,
        items: list[str],
        root: Path,
        tests: list[str] | tuple[str, ...] = (),
    ) -> ContractOutcome:
        """A contract field recorded before craft, against the working tree and the test files the oracle declares. Deferred parts wait for `verify`; an after_craft field is only parsed."""
        return self._run(
            field.name,
            field.contract or "",
            items,
            root,
            committed=False,
            deferred=field.after_craft,
            tests=tuple(tests),
        )

    def verify(
        self,
        contract: str,
        items: list[str],
        root: Path,
        *,
        generated: bool = False,
        tests: list[str] | tuple[str, ...] = (),
    ) -> ContractOutcome:
        """A contract's items after craft, against the committed change from BASE to HEAD and the test files the oracle declared."""
        return self._run(
            contract,
            contract,
            items,
            root,
            committed=True,
            generated=generated,
            tests=tuple(tests),
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
        """A probe case's artifact: a name that occurs as a whole word in a file the committed change touched."""
        label = f"artifact {artifact}"
        diff, reason = self._diff(root, committed=True)
        if diff is None:
            return ContractOutcome((), self._warnings(label, reason, True))
        try:
            texts = self._texts(diff)
        except GitDiffError as error:
            return ContractOutcome((), self._warnings(label, str(error), True))
        if any(SymbolText.mentions(text, artifact) for text in texts.values()):
            return ContractOutcome(())
        return ContractOutcome(
            (f"artifact '{artifact}' occurs in no file changed from BASE to HEAD",)
        )

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
        tests: tuple[str, ...] = (),
    ) -> ContractOutcome:
        if not committed and (contract in _DEFERRED or deferred):
            problems, _ = self._problems(contract, items, None, generated, tests)
            return ContractOutcome(tuple(problems))
        diff, reason = self._diff(root, committed)
        try:
            problems, found = self._problems(contract, items, diff, generated, tests)
        except GitDiffError as error:
            reason = str(error)
            problems, found = self._problems(contract, items, None, generated, tests)
        return ContractOutcome(
            tuple(problems),
            (*self._warnings(label, reason, committed), *found),
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
        tests: tuple[str, ...] = (),
    ) -> tuple[list[str], tuple[str, ...]]:
        if contract == "invariant":
            return self._invariants(items, diff), ()
        if contract == "model":
            return self._model_witnesses(items, diff), ()
        if contract == "stateless":
            return self._stateless(items, diff), ()
        if contract == "law":
            return self._generators(items, diff, LawItem, "law", generated, tests)
        if contract == "message":
            return self._generators(items, diff, MessageItem, "message", False, tests)
        return [], ()

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
        for invariant in parsed:
            if invariant.witness_path is None or invariant.witness_symbol is None:
                continue
            problems += self._witness_problems(
                invariant.identifier,
                invariant.witness_path,
                invariant.witness_symbol,
                diff,
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
        for witness in parsed:
            problems += self._witness_problems(
                witness.identifier,
                witness.witness_path,
                witness.witness_symbol,
                diff,
            )
        return problems

    def _witness_problems(
        self, identifier: str, path: str, symbol: str, diff: GitDiff
    ) -> list[str]:
        """A witness path must be changed from BASE, and its symbol must occur as a whole word in its text at HEAD."""
        if path not in diff.names():
            return [
                f"{identifier}: witness path '{path}' is not changed from BASE to HEAD"
            ]
        source = diff.text(path)
        if source is None:
            return [f"{identifier}: witness path '{path}' has no text at HEAD"]
        if SymbolText.mentions(source, symbol):
            return []
        return [f"{identifier}: symbol '{symbol}' does not occur in '{path}' at HEAD"]

    def _stateless(self, items: list[str], diff: GitDiff | None) -> list[str]:
        """A reason that the change has no state must be long enough; each trigger word the added lines of any changed file use must be named in it."""
        if not items:
            return []
        problems = [
            f"'{item}' is shorter than {self.NO_STATE_MIN_CHARS} characters: say that the change has no state, protocol, concurrency or crash window"
            for item in items
            if len(item.strip()) < self.NO_STATE_MIN_CHARS
        ]
        if diff is None:
            return problems
        text = " ".join(items)
        found: dict[str, str] = {}
        for path in sorted(diff.names()):
            source = diff.text(path)
            if source is None:
                continue
            lines = source.splitlines()
            for number in sorted(diff.added_lines(path)):
                if not 1 <= number <= len(lines):
                    continue
                for word in sorted(StateTrigger.in_text(lines[number - 1])):
                    found.setdefault(word, f"{path}:{number}")
        for word, location in found.items():
            if not StateTrigger.named_by(text, word):
                problems.append(
                    f"{location} adds '{word}': a reason that the change has no state must name '{word}' and say what the change does not do with it"
                )
        return problems

    def _generators(
        self,
        items: list[str],
        diff: GitDiff | None,
        parser: type,
        label: str,
        generated: bool,
        tests: tuple[str, ...],
    ) -> tuple[list[str], tuple[str, ...]]:
        """A generator or test must occur in a declared test file the change contains. A generated law whose generation cannot be seen is could-not-verify."""
        problems: list[str] = []
        warnings: list[str] = []
        parsed: list[LawItem | MessageItem] = []
        for item in items:
            try:
                parsed.append(parser.parse(item))
            except ValueError as error:
                problems.append(f"'{item}' is not a valid {label}: {error}")
        if diff is None:
            return problems, ()
        changed = diff.names()
        declared = [
            diff.text(path)
            for path in tests
            if path in changed and diff.text(path) is not None
        ]
        for entry in parsed:
            name = entry.generator if isinstance(entry, LawItem) else entry.test
            if name is None:
                continue
            if not any(SymbolText.mentions(text, name) for text in declared):
                problems.append(
                    f"{entry.identifier}: test '{name}' occurs in no declared test file the change contains"
                )
            elif generated:
                warnings.append(
                    f"{entry.identifier}: could-not-verify: the tool cannot see whether '{name}' draws generated inputs "
                    "in this repository's language, so generation is not stated as checked; "
                    "what: the law's observation and mutant are recorded; "
                    "why: a generated law has no language-neutral construction yet; "
                    "how: keep the property test of this repository, which the review reads"
                )
        return problems, tuple(warnings)

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

    @staticmethod
    def _texts(diff: GitDiff) -> dict[str, str]:
        found: dict[str, str] = {}
        for path in sorted(diff.names()):
            source = diff.text(path)
            if source is not None:
                found[path] = source
        return found
