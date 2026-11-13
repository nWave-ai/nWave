"""Renders the request coverage and the edge matrix, each cell with its observed self-probe result."""

from __future__ import annotations

from collections.abc import Callable

from nwstep.domain.field import Field
from nwstep.domain.journal import Journal
from nwstep.domain.matrix_cell import MatrixCell
from nwstep.domain.prefixed_item import PrefixedItem
from nwstep.domain.request_sentences import RequestSentences
from nwstep.domain.schema import Schema
from nwstep.domain.sentence_coverage import SentenceCoverage


class CoverageBrief:
    def __init__(self, schema: Schema, journal: Journal) -> None:
        self._schema = schema
        self._journal = journal

    def lines(self) -> list[str]:
        return [*self._request_lines(), *self._matrix_lines()]

    def _fields(self, predicate: Callable[[Field], bool]) -> list[tuple[str, Field]]:
        return [
            (step.id, field)
            for step in self._schema.steps
            for field in step.fields
            if predicate(field)
        ]

    def _request_lines(self) -> list[str]:
        lines: list[str] = []
        for step_id, mapper in self._fields(lambda f: f.covers_sentences is not None):
            sentences = self._journal.latest_value(step_id, RequestSentences.KEY)
            if not sentences:
                continue
            mapping = self._bodies(step_id, mapper.name)
            tests = self._tests_by_promise(step_id)
            lines += ["## Request coverage", ""]
            for text in sentences:
                identifier = PrefixedItem(str(text)).identifier or ""
                lines.append(f"- {text}")
                body = mapping.get(identifier, "")
                if body.startswith(SentenceCoverage.NOT_TESTABLE):
                    reason = body[len(SentenceCoverage.NOT_TESTABLE) :].strip()
                    lines.append(f"  - not-testable (challenge this): {reason}")
                    continue
                promises = [name.strip() for name in body.split(",") if name.strip()]
                lines.append(f"  - promises: {', '.join(promises) or 'none'}")
                for promise in promises:
                    for test in tests.get(promise, []):
                        lines.append(f"  - tests {promise}: {test}")
            lines.append("")
        return lines

    def _tests_by_promise(self, sentence_step: str) -> dict[str, list[str]]:
        tests: dict[str, list[str]] = {}
        for step_id, field in self._fields(
            lambda f: f.covers == (sentence_step, SentenceCoverage.PROMISES)
        ):
            for text in self._journal.latest_value(step_id, field.name) or []:
                identifier = PrefixedItem(str(text)).identifier
                if identifier is not None:
                    tests.setdefault(identifier, []).append(self._body(str(text)))
        return tests

    def _matrix_lines(self) -> list[str]:
        lines: list[str] = []
        for step_id, matrix in self._fields(lambda f: f.cross_with is not None):
            cells = self._journal.latest_value(step_id, matrix.name) or []
            if not cells:
                continue
            probes = self._probes(step_id, matrix.name)
            lines += ["## Edge matrix", ""]
            for text in cells:
                lines.append(self._cell_line(str(text), probes))
            lines.append("")
        return lines

    def _probes(
        self, matrix_step: str, matrix_field: str
    ) -> dict[str, dict[str, object]]:
        observed: dict[str, dict[str, object]] = {}
        for step_id, cases in self._fields(
            lambda f: f.needs_ids == (matrix_step, matrix_field)
        ):
            for case in self._journal.latest_value(step_id, cases.name) or []:
                observed[str(case["id"])] = case
        return observed

    @staticmethod
    def _cell_line(text: str, probes: dict[str, dict[str, object]]) -> str:
        try:
            cell = MatrixCell.parse(text)
        except ValueError:
            return f"- {text}"
        if cell.not_applicable:
            return f"- {cell.identifier}: n/a (challenge this): {cell.reason}"
        case = probes.get(cell.identifier)
        if case is None:
            status = "not probed"
        elif case["held"]:
            status = f"held (exit {case['exit_code']})"
        else:
            status = f"NOT HELD: {case['observed']}"
        pre_feature = (
            "pre-feature not probed"
            if case is None
            else str(case.get("differential", "pre-feature not recorded"))
        )
        return (
            f"- {cell.identifier}: {cell.case} => {cell.expected} "
            f"| self-probe: {status} | {pre_feature}"
        )

    def _bodies(self, step_id: str, field_name: str) -> dict[str, str]:
        bodies: dict[str, str] = {}
        for text in self._journal.latest_value(step_id, field_name) or []:
            identifier = PrefixedItem(str(text)).identifier
            if identifier is not None:
                bodies[identifier] = self._body(str(text))
        return bodies

    @staticmethod
    def _body(text: str) -> str:
        return text.partition("=>")[2].strip()
