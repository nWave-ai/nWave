"""One typed input of a step: what it accepts, what it refuses and how it is shown."""

from __future__ import annotations

from pathlib import Path

from nwstep.domain.case_result import CaseResult
from nwstep.domain.case_spec import CaseSpec
from nwstep.domain.command_line import CommandLine, Operator, UnquotedOperator
from nwstep.domain.command_outcome import CommandOutcome
from nwstep.domain.edge_category import EdgeCategory
from nwstep.domain.fault import Fault
from nwstep.domain.field_kind import FieldKind
from nwstep.domain.prefixed_item import PrefixedItem
from nwstep.domain.refusal import Refusal
from nwstep.domain.review_item import ReviewItem
from nwstep.domain.scenario import Scenario
from nwstep.domain.scenario_rules import ScenarioRules
from nwstep.domain.self_review_verdict import SelfReviewVerdict
from nwstep.domain.size import Size
from nwstep.domain.typesafe_outcome import TypesafeOutcome


class Field:
    """Checks one declared input. Every refusal names this field and quotes its help as the reason."""

    CONTRACTS = ("invariant", "law", "message", "stateless", "model")

    RUNS_ON_PRE_FEATURE = "pre-feature"
    RUNS_ON_REFACTOR = "refactor"

    def __init__(
        self,
        name: str,
        kind: FieldKind,
        help_text: str,
        *,
        required: bool = True,
        choices: tuple[str, ...] = (),
        min_items: int | None = None,
        max_items: int | None = None,
        min_chars: int | None = None,
        expect: str | None = None,
        covers: str | None = None,
        covers_sentences: str | None = None,
        cross_with: str | None = None,
        categories: tuple[str, ...] = (),
        needs_ids: str | None = None,
        prefix_ids: bool = False,
        ids: tuple[str, ...] = (),
        evidence_chars: int | None = None,
        decides: str | None = None,
        contract: str | None = None,
        locator_ids: tuple[str, ...] = (),
        verifies: tuple[str, ...] = (),
        after_craft: bool = False,
        runs_on: str | None = None,
        generated: bool = False,
        predicted_by: str | None = None,
        decided_by: str | None = None,
        checked_claims: bool = False,
        review: bool = False,
        must_fail: tuple[str, ...] = (),
        names_tests: bool = False,
        compare_baseline: bool = False,
        fallback: str | None = None,
        required_sizes: tuple[Size, ...] = (),
    ) -> None:
        if (
            not name
            or name.startswith("-")
            or "=" in name
            or any(c.isspace() for c in name)
        ):
            raise ValueError(f"field name '{name}' must be one bare word")
        if not help_text.strip():
            raise ValueError(f"field '{name}' needs a help sentence")
        if (kind is FieldKind.ENUM) != bool(choices):
            raise ValueError(
                f"field '{name}': choices are required on enum fields and only allowed there"
            )
        if min_items is not None and (not kind.is_multi or min_items < 0):
            raise ValueError(
                f"field '{name}': min_items applies to multi-valued fields and cannot be negative"
            )
        if max_items is not None and (not kind.is_multi or max_items < 1):
            raise ValueError(
                f"field '{name}': max_items applies to multi-valued fields and must be at least 1"
            )
        if min_chars is not None and (kind is not FieldKind.TEXT or min_chars < 0):
            raise ValueError(
                f"field '{name}': min_chars applies to text fields and cannot be negative"
            )
        if expect is not None and (
            kind is not FieldKind.COMMAND or expect not in ("pass", "fail")
        ):
            raise ValueError(
                f"field '{name}': expect is 'pass' or 'fail' and applies to command fields"
            )
        rules = [
            option
            for option in (covers, covers_sentences, cross_with, decides)
            if option is not None
        ]
        if ids:
            rules.append("ids")
        if len(rules) > 1:
            raise ValueError(
                f"field '{name}': choose one of covers, covers_sentences, cross_with, decides or ids"
            )
        if covers is not None and kind is not FieldKind.LIST:
            raise ValueError(f"field '{name}': covers applies to list fields")
        if (covers_sentences is not None or cross_with is not None) and (
            kind is not FieldKind.LIST
        ):
            raise ValueError(
                f"field '{name}': covers_sentences and cross_with apply to list fields"
            )
        if prefix_ids and covers is None:
            raise ValueError(
                f"field '{name}': prefix_ids is only meaningful with covers"
            )
        if ids and kind is not FieldKind.LIST:
            raise ValueError(f"field '{name}': ids applies to list fields")
        if categories and cross_with is None:
            raise ValueError(f"field '{name}': categories applies to cross_with")
        if len(set(categories)) != len(categories):
            raise ValueError(f"field '{name}': categories must be distinct")
        if needs_ids is not None and kind is not FieldKind.CASES:
            raise ValueError(f"field '{name}': needs_ids applies to cases fields")
        if evidence_chars is not None and (not ids or evidence_chars < 0):
            raise ValueError(
                f"field '{name}': evidence_chars applies to fields with ids and cannot be negative"
            )
        if decides is not None and kind is not FieldKind.LIST:
            raise ValueError(f"field '{name}': decides applies to list fields")
        if contract is not None and (
            kind is not FieldKind.LIST or contract not in Field.CONTRACTS
        ):
            raise ValueError(
                f"field '{name}': contract is one of {', '.join(Field.CONTRACTS)} and applies to list fields"
            )
        if locator_ids and (
            kind is not FieldKind.LIST or not set(locator_ids) <= set(ids)
        ):
            raise ValueError(
                f"field '{name}': locator_ids names ids of this field and applies to list fields with ids"
            )
        if verifies and kind is not FieldKind.LIST:
            raise ValueError(f"field '{name}': verifies applies to list fields")
        if must_fail and runs_on != Field.RUNS_ON_PRE_FEATURE:
            raise ValueError(
                f"field '{name}': must_fail applies to a runs_on=pre-feature command"
            )
        if names_tests and (kind is not FieldKind.LIST or covers is None):
            raise ValueError(
                f"field '{name}': names_tests applies to list fields with covers"
            )
        if compare_baseline and (kind is not FieldKind.COMMAND or expect is not None):
            raise ValueError(
                f"field '{name}': compare_baseline applies to command fields without expect"
            )
        if fallback is not None and kind is not FieldKind.COMMAND:
            raise ValueError(f"field '{name}': fallback applies to command fields")
        if runs_on is not None:
            expected = {
                Field.RUNS_ON_PRE_FEATURE: "fail",
                Field.RUNS_ON_REFACTOR: "pass",
            }
            if (
                runs_on not in expected
                or kind is not FieldKind.COMMAND
                or expect != expected[runs_on]
            ):
                raise ValueError(
                    f"field '{name}': runs_on is 'pre-feature' with expect=fail, or 'refactor' with expect=pass, and applies to command fields"
                )
        if generated and (kind is not FieldKind.LIST or contract != "law"):
            raise ValueError(f"field '{name}': generated applies to law list fields")
        if predicted_by is not None and kind is not FieldKind.CASES:
            raise ValueError(f"field '{name}': predicted_by applies to cases fields")
        if decided_by is not None and kind is not FieldKind.LIST:
            raise ValueError(f"field '{name}': decided_by applies to list fields")
        if checked_claims and kind is not FieldKind.TEXT:
            raise ValueError(f"field '{name}': checked_claims applies to text fields")
        if review and kind is not FieldKind.LIST:
            raise ValueError(f"field '{name}': review applies to list fields")

        self.name = name
        self.kind = kind
        self.help = help_text.strip()
        self.required = required
        self.choices = choices
        self.min_items = min_items if min_items is not None else (1 if required else 0)
        self.max_items = max_items
        if max_items is not None and self.min_items > max_items:
            raise ValueError(
                f"field '{name}': min_items ({self.min_items}) exceeds max_items ({max_items})"
            )
        self.min_chars = min_chars or 0
        self.expect = expect
        self.covers = self._parse_reference(covers, "covers")
        self.covers_sentences = covers_sentences
        self.cross_with = cross_with
        self.categories = (
            (categories or EdgeCategory.DEFAULT) if cross_with is not None else ()
        )
        self.needs_ids = self._parse_reference(needs_ids, "needs_ids")
        self.prefix_ids = prefix_ids
        self.ids = ids
        self.evidence_chars = evidence_chars
        self.decides = self._parse_reference(decides, "decides")
        self.contract = contract
        self.locator_ids = locator_ids
        self.verifies = tuple(
            self._parse_reference(reference, "verifies") for reference in verifies
        )
        if after_craft and contract not in ("law", "message"):
            raise ValueError(
                f"field '{name}': after_craft applies to law and message contracts, whose generator and test names exist only in the committed change"
            )
        self.after_craft = after_craft
        self.runs_on = runs_on
        self.generated = generated
        self.predicted_by = self._parse_reference(predicted_by, "predicted_by")
        self.decided_by = self._parse_reference(decided_by, "decided_by")
        self.checked_claims = checked_claims
        self.review = review
        self.must_fail = must_fail
        self.names_tests = names_tests
        self.compare_baseline = compare_baseline
        self.fallback = fallback
        self.required_sizes = frozenset(required_sizes)

    @staticmethod
    def _parse_reference(reference: str | None, option: str) -> tuple[str, str] | None:
        if reference is None:
            return None
        step_id, dot, field_name = reference.partition(".")
        if not (dot and step_id and field_name):
            raise ValueError(f"{option} must read 'step.field', got '{reference}'")
        return step_id, field_name

    def refuse(
        self,
        what: str,
        *,
        rejected: tuple[str, ...] = (),
        missing: tuple[str, ...] = (),
        fault: Fault = Fault.VALUE,
    ) -> Refusal:
        return Refusal(
            what=what,
            why=self.help,
            field=self.name,
            rejected=rejected,
            missing=missing,
            fault=fault,
        )

    def refuse_missing(self) -> Refusal:
        return self.refuse(
            f"required field '{self.name}' is missing", fault=Fault.MISSING
        )

    def accept_value(self, raw: str) -> object:
        """Check a single-value field (text, enum, int, bool, typesafe) and return its typed value."""
        match self.kind:
            case FieldKind.TEXT:
                return self._text(raw)
            case FieldKind.ENUM:
                return self._enum(raw)
            case FieldKind.INT:
                return self._int(raw)
            case FieldKind.BOOL:
                return self._bool(raw)
            case FieldKind.TYPESAFE:
                return self._typesafe(raw)
            case _:
                raise ValueError(f"field '{self.name}' takes items, not a single value")

    def accept_command(self, raw: str) -> list[str]:
        """Read a command field as the one invocation it holds, without a shell. The argv is run later, after all shape checks."""
        try:
            argv = list(CommandLine.parse(raw).argv)
        except UnquotedOperator as error:
            raise self._refuse_operator(error.operator) from None
        except ValueError as error:
            raise self.refuse(
                f"field '{self.name}' is not a valid command line: {error}"
            ) from None
        if not argv:
            raise self.refuse(f"field '{self.name}' is an empty command")
        return argv

    def _refuse_operator(self, operator: Operator) -> Refusal:
        """A shell operator outside quotes: named as written, with why no shell would make it work; the HOW repairs it."""
        shown = "a newline" if operator.text == "\n" else f"'{operator.text}'"
        if operator.expands:
            scope = "outside single quotes"
            why = (
                "a POSIX shell would expand it, but the command runs without a shell, so the program receives the text "
                "as written and the check does not mean what the command says; put the value inside single quotes to "
                "keep it literal, or remove it"
            )
        else:
            scope = "outside quotes"
            why = (
                "the command runs without a shell, so the operator would reach the program as an argument and the check "
                "would not run; record one check per revision of this field"
            )
        return Refusal(
            what=f"field '{self.name}' holds the shell operator {shown} {scope}",
            why=why,
            field=self.name,
            fault=Fault.SHELL_OPERATOR,
        )

    def accept_items(self, items: list[str], root: Path) -> list[str]:
        """Check a list, paths, cases or scenarios field. Paths resolve against root and must exist."""
        if not items:
            if self.required:
                raise self.refuse_missing()
            return []
        if len(items) < self.min_items:
            raise self.refuse(
                f"field '{self.name}' needs at least {self.min_items} item(s), got {len(items)}"
            )
        if self.max_items is not None and len(items) > self.max_items:
            raise self.refuse(
                f"field '{self.name}' takes at most {self.max_items} item(s), got {len(items)}",
                rejected=tuple(items[self.max_items :]),
            )
        blank = tuple(item for item in items if not item.strip())
        if blank:
            raise self.refuse(
                f"field '{self.name}' has an empty item",
                rejected=blank,
                fault=Fault.SYNTAX,
            )
        if self.kind is FieldKind.SCENARIOS:
            self._check_scenarios(items)
        if self.kind is FieldKind.PATHS:
            absent = tuple(
                item for item in items if not self._resolve(item, root).exists()
            )
            if absent:
                raise self.refuse(
                    f"field '{self.name}' names a path that does not exist: {', '.join(absent)}",
                    rejected=absent,
                    fault=Fault.ABSENT_PATH,
                )
        if self.review:
            self._check_reviews(items)
        return [item.strip() for item in items]

    def _check_scenarios(self, items: list[str]) -> None:
        problems: list[str] = []
        for item in items:
            try:
                scenario = Scenario.parse(item)
            except ValueError as error:
                problems.append(f"'{item}' is not a scenario: {error}")
                continue
            problems += [
                f"{scenario.identifier}: {problem}"
                for problem in ScenarioRules(scenario).problems()
            ]
        if problems:
            raise self.refuse(
                f"field '{self.name}' refuses {len(problems)} scenario problem(s): {'; '.join(problems)}"
            )

    def _check_reviews(self, items: list[str]) -> None:
        problems: list[str] = []
        for item in items:
            try:
                ReviewItem.parse(item)
            except ValueError as error:
                problems.append(f"'{item}' is not a review: {error}")
        if problems:
            raise self.refuse(
                f"field '{self.name}' refuses {len(problems)} review(s): {'; '.join(problems)}"
            )

    def identifiers_of(self, texts: list[str] | tuple[str, ...]) -> list[str]:
        """The ids the items open with: a scenario's ID before its first '|', else the prefix id."""
        if self.kind is FieldKind.SCENARIOS:
            identifiers = [Scenario.identifier_of(text) for text in texts]
        else:
            identifiers = [PrefixedItem(str(text)).identifier for text in texts]
        return [identifier for identifier in identifiers if identifier is not None]

    def read_single_file(self, items: list[str], root: Path) -> str:
        """Read the one file a field names, relative to root."""
        path = self._resolve(items[0], root)
        if not path.is_file():
            raise self.refuse(
                f"field '{self.name}' must name one readable file, got '{items[0]}'"
            )
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise self.refuse(
                f"field '{self.name}' cannot be read as text: {error}"
            ) from None

    def parse_cases(self, items: list[str]) -> list[CaseSpec]:
        specs: list[CaseSpec] = []
        for item in items:
            try:
                specs.append(CaseSpec.parse(item))
            except ValueError as error:
                raise self.refuse(
                    f"case '{item}' is not valid: {error}",
                    rejected=(item,),
                    fault=Fault.SYNTAX,
                ) from None
        return specs

    def refuse_cases(self, failing: list[CaseResult]) -> Refusal:
        """A failing case is not repaired by the tool, so the HOW line keeps it as written for correction."""
        details = "; ".join(
            f"{result.identifier} expected {result.expectation}, observed {result.observed}; {result.differential_text()}"
            for result in failing
        )
        return self.refuse(
            f"{len(failing)} case(s) of '{self.name}' did not hold: {details}",
            fault=Fault.COMMAND,
        )

    def refuse_unproven(self, unproven: list[tuple[CaseResult, str]]) -> Refusal:
        """A case whose kind does not hold against the pre-feature tree proves nothing; HOW is the runnable record with the cases as written, so the executor edits only the cases named."""
        details = "; ".join(
            f"{result.identifier}: {reason}; candidate {result.observed}; {result.differential_text()}"
            for result, reason in unproven
        )
        return Refusal(
            what=f"{len(unproven)} case(s) of '{self.name}' do not prove the change: {details}",
            why="a probe case proves the change only when its kind is checked against the pre-feature tree: kind=new needs an argv that fails there and prints baseline-contains=TEXT; kind=preserve needs an argv that holds on both trees and protects=PATH, a file changed from BASE to HEAD",
            field=self.name,
            fault=Fault.COMMAND,
        )

    def check_outcome(
        self, outcome: CommandOutcome, kept_at: Path | None = None
    ) -> None:
        """A refused command keeps its last output lines in the refusal, and names the file its full output was kept in."""
        kept = "" if kept_at is None else f"; full output kept in {kept_at}"
        if outcome.problem is not None:
            raise self.refuse(
                f"command for '{self.name}' did not finish: {outcome.problem}",
                fault=Fault.COMMAND,
            )
        if self.expect == "pass" and outcome.exit_code != 0:
            raise self.refuse(
                f"command for '{self.name}' exited {outcome.exit_code} but expect is pass{self._tail(outcome)}{kept}",
                fault=Fault.COMMAND,
            )
        if self.expect == "fail" and outcome.exit_code == 0:
            raise self.refuse(
                f"command for '{self.name}' exited 0 but expect is fail{self._tail(outcome)}{kept}",
                fault=Fault.COMMAND,
            )

    @staticmethod
    def _tail(outcome: CommandOutcome) -> str:
        lines = [line.strip() for line in outcome.output_tail if line.strip()][-3:]
        return f"; last output: {' | '.join(lines)}" if lines else ""

    def check_coverage(
        self, items: list[str], required: list[str] | tuple[str, ...], source: str
    ) -> None:
        """Every required id must open at least one item. With prefix_ids, every item must open with one."""
        present: set[str] = set()
        for item in items:
            identifier = PrefixedItem(item).identifier
            if identifier is None:
                if self.prefix_ids:
                    raise self.refuse(
                        f"item '{item}' has no prefix id; write it as 'ID => ...'",
                        rejected=(item,),
                        fault=Fault.SYNTAX,
                    )
                continue
            present.add(identifier)
        self._require_present(present, required, source)

    def check_identifiers(
        self, identifiers: list[str], required: list[str] | tuple[str, ...], source: str
    ) -> None:
        """Every required id must be the identifier of at least one item."""
        self._require_present(set(identifiers), required, source)

    def check_evidence(self, items: list[str]) -> None:
        """Each item with one of the fixed ids gives a verdict whose evidence is at least evidence_chars."""
        if self.evidence_chars is None:
            return
        problems: list[str] = []
        rejected: list[str] = []
        missing: list[str] = []
        for item in items:
            identifier = PrefixedItem(item).identifier
            if identifier not in self.ids:
                continue
            try:
                verdict = SelfReviewVerdict.parse(item)
            except ValueError as error:
                problems.append(f"{identifier}: {error}")
            else:
                if len(verdict.evidence) >= self.evidence_chars:
                    continue
                problems.append(
                    f"{identifier}: {verdict.word} evidence is shorter than {self.evidence_chars} characters"
                )
            rejected.append(item)
            missing.append(identifier)
        if problems:
            raise self.refuse(
                f"field '{self.name}' refuses {len(problems)} answer(s): {'; '.join(problems)}",
                rejected=tuple(rejected),
                missing=tuple(missing),
            )

    def placeholder(self) -> str:
        """What a HOW line shows where the executor must supply content the tool cannot know."""
        match self.kind:
            case FieldKind.TEXT:
                return f"<text of at least {max(self.min_chars, 1)} characters>"
            case FieldKind.ENUM:
                return f"<one of {'|'.join(self.choices)}>"
            case FieldKind.INT:
                return "<integer>"
            case FieldKind.BOOL:
                return "<true|false>"
            case FieldKind.PATHS:
                return "<existing path>"
            case FieldKind.CASES:
                return "<ID | ARGV | EXPECT>"
            case FieldKind.SCENARIOS:
                return "<ID | PROMISE | GIVEN ... | WHEN ... | THEN ...>"
            case FieldKind.CONFLICTS:
                return "<ID | NONE | reason> or <ID | CONFLICT | existing behaviour | question?>"
            case FieldKind.COMMAND:
                return {
                    "pass": "<command exiting 0>",
                    "fail": "<command exiting non-zero>",
                }.get(self.expect or "", "<command>")
            case FieldKind.LIST if self.covers is not None:
                return "<ID => test that proves it>"
            case FieldKind.LIST if self.covers_sentences is not None:
                return "<ID => promise ids, or not-testable: reason>"
            case FieldKind.LIST if self.cross_with is not None:
                return "<ID => case => expected result>"
            case FieldKind.LIST if self.ids:
                return "<ID: pass - evidence | fixed:evidence | n/a:reason>"
            case FieldKind.LIST if self.decides is not None:
                return "<ID: decision of at least 20 characters>"
            case _:
                return "<item>"

    def template_for(self, identifier: str) -> str:
        """The item a HOW line shows for a required id that is still missing."""
        if self.kind is FieldKind.SCENARIOS:
            return f"<ID> | {identifier} | <GIVEN concrete data> | <WHEN concrete input> | <THEN concrete observable result>"
        if self.kind is FieldKind.CONFLICTS:
            return f"{identifier} | <NONE | reason of at least 20 characters> or <CONFLICT | existing behaviour of at least 20 characters | question ending with ?>"
        if self.decides is not None:
            return f"{identifier}: <decision of at least 20 characters>"
        if self.covers_sentences is not None:
            return f"{identifier} => <promise ids, or not-testable: reason>"
        if self.cross_with is not None:
            return f"{identifier} => <case> => <expected result>"
        if self.needs_ids is not None:
            return f"{identifier} | <argv> | <expectation>"
        if self.covers is not None:
            return f"{identifier} => <test that proves it>"
        return f"{identifier}: pass - <evidence> | fixed:<evidence> | n/a:<reason>"

    def example(self) -> str:
        """One valid way to give this field, in the form the record command takes; the step's help lists it."""
        flag = f"--item {self.name}=" if self.kind.is_multi else f"--{self.name} "
        match self.kind:
            case FieldKind.TEXT:
                return f'{flag}"<text of at least {max(self.min_chars, 1)} characters>"'
            case FieldKind.ENUM:
                return f"{flag}{self.choices[0]}"
            case FieldKind.INT:
                return f"{flag}1"
            case FieldKind.BOOL:
                return f"{flag}true"
            case FieldKind.PATHS:
                return f"{flag}<existing path>"
            case FieldKind.COMMAND:
                code = 1 if self.expect == "fail" else 0
                return f'{flag}"<command exiting {code}>"'
            case FieldKind.CASES:
                return f'{flag}"I1.empty | <argv> | exit=0,kind=new,baseline-contains=<text>"'
            case FieldKind.SCENARIOS:
                return f'{flag}"SC1 | P1 | GIVEN <data with a digit> | WHEN <input> | THEN <result with a digit>"'
            case FieldKind.CONFLICTS:
                return f'{flag}"S1 | NONE | <reason of at least 20 characters naming what was checked>"'
            case _:
                return f'{flag}"{self._list_example()}"'

    def _list_example(self) -> str:
        if self.covers is not None:
            return "P1 => test_name"
        if self.covers_sentences is not None:
            return "S1 => P1"
        if self.cross_with is not None:
            return "I1.empty => case => expected result"
        if self.decides is not None:
            return "S2: <decision of at least 20 characters>"
        if self.review:
            return "REV1 | reviewer=ID | findings=<text> | resolution=<text>"
        if self.contract == "law":
            return "LAW1 | <law> | generator=test_name | observation=<text> | mutant=<text>"
        if self.contract == "message":
            return "MSG1 | <input> | <what> | <why> | <how> | test=test_name"
        if self.contract == "invariant":
            return "INV1 | <invariant> | witness=path.py:Symbol | bypass=none"
        if self.contract == "model":
            return "INV1 | <model invariant name> | witness=path.py:Symbol"
        if self.contract == "stateless":
            return "<reason of at least 30 characters>"
        if self.ids:
            return f"{self.ids[0]}: pass - <evidence of at least {max(self.evidence_chars or 1, 1)} characters>"
        return "<item>"

    def describe(self) -> str:
        facts = [self.kind.value, "required" if self.required else "optional"]
        if self.choices:
            facts.append("choices=" + "|".join(self.choices))
        if self.min_chars:
            facts.append(f"min_chars={self.min_chars}")
        if self.kind.is_multi and self.min_items:
            facts.append(f"min_items={self.min_items}")
        if self.max_items is not None:
            facts.append(f"max_items={self.max_items}")
        if self.expect:
            facts.append(f"expect={self.expect}")
        if self.covers is not None:
            facts.append(f"covers={self.covers[0]}.{self.covers[1]}")
        if self.covers_sentences is not None:
            facts.append(f"covers_sentences={self.covers_sentences}")
        if self.cross_with is not None:
            facts.append(f"cross_with={self.cross_with}")
            facts.append("categories=" + "|".join(self.categories))
        if self.needs_ids is not None:
            facts.append(f"needs_ids={self.needs_ids[0]}.{self.needs_ids[1]}")
        if self.prefix_ids:
            facts.append("prefix_ids")
        if self.ids:
            facts.append("ids=" + ",".join(self.ids))
        if self.evidence_chars is not None:
            facts.append(f"evidence_chars={self.evidence_chars}")
        if self.decides is not None:
            facts.append(f"decides={self.decides[0]}.{self.decides[1]}")
        if self.runs_on is not None:
            facts.append(f"runs_on={self.runs_on}")
        if self.generated:
            facts.append("generated")
        if self.predicted_by is not None:
            facts.append(f"predicted_by={self.predicted_by[0]}.{self.predicted_by[1]}")
        if self.decided_by is not None:
            facts.append(f"decided_by={self.decided_by[0]}.{self.decided_by[1]}")
        if self.checked_claims:
            facts.append("checked_claims")
        if self.review:
            facts.append("review")
        passed = (
            f"--item {self.name}=VALUE (repeat per entry)"
            if self.kind.is_multi
            else f"--{self.name} VALUE"
        )
        example = self.example()
        return f"{self.name} ({', '.join(facts)}; give as {passed}; for example {example}): {self.help}"

    def _require_present(
        self, present: set[str], required: list[str] | tuple[str, ...], source: str
    ) -> None:
        missing = tuple(
            dict.fromkeys(
                identifier for identifier in required if identifier not in present
            )
        )
        if missing:
            raise self.refuse(
                f"field '{self.name}' lacks id(s) {', '.join(missing)} (required by {source})",
                missing=missing,
                fault=Fault.COVERAGE,
            )

    def _text(self, raw: str) -> str:
        value = raw.strip()
        needed = max(self.min_chars, 1)
        if len(value) < needed:
            raise self.refuse(
                f"field '{self.name}' needs at least {needed} characters, got {len(value)}"
            )
        return value

    def _enum(self, raw: str) -> str:
        if raw not in self.choices:
            raise self.refuse(
                f"field '{self.name}' must be one of {'|'.join(self.choices)}, got '{raw}'"
            )
        return raw

    def _typesafe(self, raw: str) -> str:
        try:
            return TypesafeOutcome.parse(raw).text
        except ValueError as error:
            raise self.refuse(f"field '{self.name}': {error}") from None

    def _int(self, raw: str) -> int:
        try:
            return int(raw)
        except ValueError:
            raise self.refuse(
                f"field '{self.name}' must be an integer, got '{raw}'"
            ) from None

    def _bool(self, raw: str) -> bool:
        if raw not in ("true", "false"):
            raise self.refuse(f"field '{self.name}' must be true or false, got '{raw}'")
        return raw == "true"

    @staticmethod
    def _resolve(item: str, root: Path) -> Path:
        path = Path(item)
        return path if path.is_absolute() else root / path
