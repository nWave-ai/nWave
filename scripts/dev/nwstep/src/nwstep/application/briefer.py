"""Renders Markdown from the journal: the summary, the decisions taken, or the trace of paths."""

from __future__ import annotations

import shlex
from typing import Any

from nwstep.application.change_facts import ChangeFacts
from nwstep.application.exploration_brief import ExplorationBrief
from nwstep.application.handoff_claims import ClaimsReport, HandoffClaims
from nwstep.application.coverage_brief import CoverageBrief
from nwstep.application.definition_of_done import DefinitionOfDone
from nwstep.application.owner_questions import OwnerQuestions
from nwstep.application.progress import Progress
from nwstep.application.review_lines import summary_lines
from nwstep.domain import prereview, review
from nwstep.domain.baseline import Baseline
from nwstep.domain.field import Field
from nwstep.domain.field_kind import FieldKind
from nwstep.domain.journal import Journal
from nwstep.domain.kit import KitState, UnknownKit
from nwstep.domain.record import Record
from nwstep.domain.schema import Schema
from nwstep.domain.review import ReviewLog
from nwstep.domain.step import Step

DECISION_TOKENS = frozenset({"decision", "decisions", "reason"})
UPSTREAM_STALE = "an earlier step was recorded again after it; record it again or say why it still holds"
FINDING_STALE = "an open finding reopened it; replay records it again once the case of the finding passes"


class Briefer:
    def __init__(
        self,
        schema: Schema,
        baseline: Baseline | None = None,
        kit: KitState | None = None,
        review_log: ReviewLog | None = None,
    ) -> None:
        self._schema = schema
        self._kit = UnknownKit() if kit is None else kit
        self._baseline = baseline or Baseline.unavailable(
            "the briefer was given no baseline"
        )
        self._review = ReviewLog() if review_log is None else review_log
        green = schema.green_step()
        self._green = None if green is None else green.id

    def render(self, kind: str, journal: Journal) -> str:
        if kind == "summary":
            return self._summary(journal)
        if kind == "decisions":
            return self._decisions(journal)
        return self._trace(journal)

    def _summary(self, journal: Journal) -> str:
        lines = ["# nwstep summary", "", self._kit.describe(), ""]
        if not self._schema.declares(FieldKind.TYPESAFE):
            lines += [
                "- typesafe: not recorded: this workspace's schema has no typesafe field, so Jev outcomes of its steps are not shown",
                "",
            ]
        lines += CoverageBrief(self._schema, journal).lines()
        lines += DefinitionOfDone(self._schema, journal).lines()
        lines += ExplorationBrief(self._schema, journal).lines()
        lines += OwnerQuestions(self._schema, journal).lines()
        lines += ChangeFacts(self._baseline).lines()
        lines += summary_lines(self._review, journal, self._green)
        stale = self._stale(journal)
        claims = HandoffClaims(self._baseline)
        checked: list[ClaimsReport] = []
        for record in self._current(journal):
            step = self._step(record)
            lines += [
                f"## {record.seq}. {step.id}: {step.title} ({self._label(record, stale)})",
                "",
            ]
            lines += self._values(
                step, record, decisions_only=False, claims=claims, checked=checked
            )
            lines.append("")
        lines += self._not_backed(checked)
        return self._document(lines)

    def _decisions(self, journal: Journal) -> str:
        lines = ["# nwstep decisions", "", self._kit.describe(), ""]
        stale = self._stale(journal)
        for record in self._current(journal):
            step = self._step(record)
            entries = self._values(step, record, decisions_only=True)
            if entries:
                lines += [
                    f"## {step.id} ({self._label(record, stale)})",
                    "",
                    *entries,
                    "",
                ]
        return self._document(lines)

    def _stale(self, journal: Journal) -> dict[str, str]:
        """Recorded steps whose values may no longer hold, each with its cause: an earlier step was recorded again
        after it, or an open finding reopened it."""
        progress = Progress(self._schema)
        reopened = review.reopened(self._review, journal, self._green)
        causes = dict.fromkeys(progress.stale(journal, reopened), FINDING_STALE)
        causes.update(dict.fromkeys(progress.stale(journal), UPSTREAM_STALE))
        return causes

    @staticmethod
    def _label(record: Record, stale: dict[str, str]) -> str:
        label = f"revision {record.revision}"
        if record.step in stale:
            label += f", STALE: {stale[record.step]}"
        return label

    @staticmethod
    def _current(journal: Journal) -> tuple[Record, ...]:
        """The latest revision of each step: a superseded statement is not shown as if it still held."""
        return tuple(
            record
            for record in journal.records
            if record.revision == journal.revisions(record.step)
        )

    def _trace(self, journal: Journal) -> str:
        lines = ["# nwstep trace", "", self._kit.describe(), ""]
        for record in journal.records:
            step = self._step(record)
            for field in step.fields:
                if field.kind is FieldKind.PATHS and field.name in record.values:
                    for path in record.values[field.name]:
                        lines.append(
                            f"- {step.id} (revision {record.revision}) `{field.name}`: {path}"
                        )
        return self._document(lines)

    def _step(self, record: Record) -> Step:
        step = self._schema.find(record.step)
        if step is None:
            raise ValueError(
                f"the journal holds step '{record.step}', which the schema does not declare"
            )
        return step

    def _values(
        self,
        step: Step,
        record: Record,
        *,
        decisions_only: bool,
        claims: HandoffClaims | None = None,
        checked: list[ClaimsReport] | None = None,
    ) -> list[str]:
        lines: list[str] = []
        for field in step.fields:
            if field.name not in record.values:
                continue
            if decisions_only and not self._is_decision(field.name):
                continue
            if field.checked_claims and claims is not None and checked is not None:
                lines += self._claim_lines(
                    field, str(record.values[field.name]), claims, checked
                )
                continue
            lines += self._field_lines(field, record.values[field.name])
        if not decisions_only and prereview.KEY in record.values:
            lines += prereview.lines(record.values[prereview.KEY])
        return lines

    @staticmethod
    def _claim_lines(
        field: Field, text: str, claims: HandoffClaims, checked: list[ClaimsReport]
    ) -> list[str]:
        """A checked text shows only the sentences the diff backs; when git cannot read the change, it shows them as not verified."""
        report = claims.judge(text)
        checked.append(report)
        if not report.verified:
            return [
                f"- **{field.name}** (not verified against the diff: {report.reason}):",
                *(f"  - {sentence}" for sentence in claims.split(text)),
            ]
        return [
            f"- **{field.name}** (sentences the diff backs):",
            *(f"  - {sentence}" for sentence in report.backed),
        ]

    @staticmethod
    def _not_backed(reports: list[ClaimsReport]) -> list[str]:
        if not reports:
            return []
        lines = ["## Not backed by the diff", ""]
        for report in reports:
            if not report.verified:
                lines.append(f"- not verified: {report.reason}")
            elif not report.not_backed:
                lines.append(
                    "- none: every checked sentence names a test or a file of the change"
                )
            else:
                lines += [
                    f"- {sentence}: {reason}" for sentence, reason in report.not_backed
                ]
        return [*lines, ""]

    @staticmethod
    def _receipt_lines(receipts: list[dict[str, Any]]) -> list[str]:
        return [
            f"  - {receipt['commit'][:12]} ({receipt['subject']}): before exit {receipt['before']['exit_code']}, after exit {receipt['after']['exit_code']}"
            for receipt in receipts
        ]

    @staticmethod
    def _field_lines(field: Field, value: Any) -> list[str]:
        if field.kind is FieldKind.COMMAND:
            if "commits" in value:
                return [
                    f"- **{field.name}**: the check ran on the parent and on each refactor commit",
                    *Briefer._receipt_lines(value["commits"]),
                ]
            command = shlex.join(value["argv"])
            lines = [
                f"- **{field.name}**: `{command}` exited {value['exit_code']} in {value['duration_s']}s"
            ]
            if "failing" in value:
                lines.append(
                    f"  - failing on the pre-feature tree ({len(value['failing'])}): {', '.join(value['failing'])}"
                )
            if "fallback" in value:
                lines.append(
                    f"  - the declared checker could not start ({value['fallback']['primary_problem']}); "
                    f"the fallback '{value['fallback']['used']}' ran instead and is the checker recorded here"
                )
            if "tests" in value:
                lines += Briefer._test_lines(value["tests"])
            if value["output_tail"]:
                lines += [
                    "  ```text",
                    *(f"  {line}" for line in value["output_tail"]),
                    "  ```",
                ]
            return lines
        if field.kind is FieldKind.CASES:
            lines = [
                f"- **{field.name}** (self-probe: run by the executor, not an independent review):"
            ]
            for case in value:
                verdict = "held" if case["held"] else "NOT HELD"
                lines.append(
                    f"  - {case['id']}: {verdict}; expected {case['expect']}; observed {case['observed']}; {case.get('differential', 'pre-feature not recorded')}"
                )
            return lines
        if field.kind.is_multi:
            return [f"- **{field.name}**:", *(f"  - {item}" for item in value)]
        return [f"- **{field.name}**: {value}"]

    @staticmethod
    def _test_lines(tests: dict[str, Any]) -> list[str]:
        """The counts and timings the tool read from the pytest summary of this command: never typed by the executor."""
        counted = ", ".join(
            f"{number} {word}" for word, number in tests["counts"].items()
        )
        lines = [f"  - tests (read from the run): {counted} in {tests['seconds']:.2f}s"]
        lines += [
            f"  - slowest: {item['seconds']:.2f}s {item['phase']} {item['test']}"
            for item in tests["slowest"]
        ]
        return lines

    @staticmethod
    def _is_decision(name: str) -> bool:
        return any(token in DECISION_TOKENS for token in name.split("_"))

    @staticmethod
    def _document(lines: list[str]) -> str:
        """The single render point: no brief line ends in a blank, whatever a field carried into it."""
        return "\n".join(line.rstrip() for line in lines).rstrip() + "\n"
