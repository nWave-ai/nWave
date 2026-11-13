"""The explored scenarios of the probe: each case that names an artifact, with the outcome the oracle predicted on
the pre-feature tree and the outcome observed there. A mismatch is shown as a surprise, never refused."""

from __future__ import annotations

from typing import Any

from nwstep.domain.field_kind import FieldKind
from nwstep.domain.journal import Journal
from nwstep.domain.schema import Schema


class ExplorationBrief:
    HEADING = "## Explored scenarios (artifact, predicted and observed on the pre-feature tree)"

    def __init__(self, schema: Schema, journal: Journal) -> None:
        self._schema = schema
        self._journal = journal

    def lines(self) -> list[str]:
        rows = [self._row(case) for case in self._cases() if "artifact" in case]
        if not rows:
            return []
        return [self.HEADING, "", *rows, ""]

    def _cases(self) -> list[dict[str, Any]]:
        cases: list[dict[str, Any]] = []
        for step in self._schema.steps:
            for field in step.fields:
                if field.kind is FieldKind.CASES:
                    cases += list(self._journal.latest_value(step.id, field.name) or [])
        return cases

    @staticmethod
    def _row(case: dict[str, Any]) -> str:
        observed = case.get("baseline", {}).get("status", "could-not-verify")
        predicted = case.get("predicted")
        if predicted is None:
            verdict = "no prediction recorded"
        elif observed == "could-not-verify":
            verdict = "could not be verified on the pre-feature tree"
        elif predicted == observed:
            verdict = "as predicted"
        else:
            verdict = f"SURPRISE: predicted base {predicted}, observed base {observed}"
        return (
            f"- {case['id']}: artifact `{case['artifact']}`; predicted base {predicted or 'none'}; "
            f"observed base {observed}; {verdict}"
        )
