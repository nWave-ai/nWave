"""The definition of done: each scenario of the request, its test, and whether a self-probe case held it."""

from __future__ import annotations

from typing import Any

from nwstep.domain.field import Field
from nwstep.domain.field_kind import FieldKind
from nwstep.domain.journal import Journal
from nwstep.domain.prefixed_item import PrefixedItem
from nwstep.domain.scenario import Scenario
from nwstep.domain.schema import Schema


class DefinitionOfDone:
    HEADING = "## Definition of done"

    def __init__(self, schema: Schema, journal: Journal) -> None:
        self._schema = schema
        self._journal = journal

    def lines(self) -> list[str]:
        texts = self._scenarios()
        if not texts:
            return []
        probes = self._probes()
        tests = self._tests()
        lines = [self.HEADING, ""]
        for text in texts:
            scenario = Scenario.parse(text)
            case = probes.get(scenario.identifier)
            if case is not None and case["held"]:
                status = f"held by the self-probe (exit {case['exit_code']}); {case.get('differential', 'pre-feature not recorded')}"
            else:
                status = "not-held (no held self-probe case)"
            lines.append(f"- {scenario.identifier} ({scenario.promise}): {status}")
            lines += [
                f"  - GIVEN {scenario.given}",
                f"  - WHEN {scenario.when}",
                f"  - THEN {scenario.then}",
            ]
            lines += [
                f"  - test: {test}" for test in tests.get(scenario.identifier, [])
            ]
        lines.append("")
        return lines

    def _scenarios(self) -> list[str]:
        texts: list[str] = []
        for step in self._schema.steps:
            for field in step.fields:
                if field.kind is FieldKind.SCENARIOS:
                    values = self._journal.latest_value(step.id, field.name) or []
                    texts += [str(text) for text in values]
        return texts

    def _probes(self) -> dict[str, dict[str, Any]]:
        observed: dict[str, dict[str, Any]] = {}
        for step in self._schema.steps:
            for field in step.fields:
                if field.kind is FieldKind.CASES:
                    for case in self._journal.latest_value(step.id, field.name) or []:
                        observed[str(case["id"])] = case
        return observed

    def _tests(self) -> dict[str, list[str]]:
        tests: dict[str, list[str]] = {}
        for step_id, consumer in self._covering_fields():
            for text in self._journal.latest_value(step_id, consumer.name) or []:
                identifier = PrefixedItem(str(text)).identifier
                if identifier is not None:
                    body = str(text).partition("=>")[2].strip()
                    tests.setdefault(identifier, []).append(body)
        return tests

    def _covering_fields(self) -> list[tuple[str, Field]]:
        scenario_lists = {
            (step.id, field.name)
            for step in self._schema.steps
            for field in step.fields
            if field.kind is FieldKind.SCENARIOS
        }
        return [
            (step.id, field)
            for step in self._schema.steps
            for field in step.fields
            if field.covers in scenario_lists
        ]
