"""Questions for the owner: each CONFLICT line of the request, and whether the oracle has decided it."""

from __future__ import annotations

from nwstep.domain.conflict_line import ConflictLine
from nwstep.domain.field import Field
from nwstep.domain.field_kind import FieldKind
from nwstep.domain.journal import Journal
from nwstep.domain.prefixed_item import PrefixedItem
from nwstep.domain.schema import Schema


class OwnerQuestions:
    HEADING = "## Questions for the owner"

    def __init__(self, schema: Schema, journal: Journal) -> None:
        self._schema = schema
        self._journal = journal

    def lines(self) -> list[str]:
        conflict_lists = self._conflict_lists()
        if not conflict_lists:
            return []
        decided = self._decided_ids(conflict_lists)
        lines = [self.HEADING, ""]
        asked = 0
        for step_id, field in conflict_lists:
            for text in self._journal.latest_value(step_id, field.name) or []:
                line = ConflictLine.parse(str(text))
                if not line.is_conflict:
                    continue
                asked += 1
                status = "decided at oracle" if line.identifier in decided else "open"
                lines += [
                    f"- {line.identifier}: {line.question}",
                    f"  - existing behaviour: {line.reason}",
                    f"  - status: {status}",
                ]
        if asked == 0:
            lines.append("- none")
        lines.append("")
        return lines

    def _conflict_lists(self) -> list[tuple[str, Field]]:
        return [
            (step.id, field)
            for step in self._schema.steps
            for field in step.fields
            if field.kind is FieldKind.CONFLICTS
        ]

    def _decided_ids(self, conflict_lists: list[tuple[str, Field]]) -> set[str]:
        decided: set[str] = set()
        for step_id, conflicts in conflict_lists:
            for step in self._schema.steps:
                for field in step.fields:
                    if field.decides != (step_id, conflicts.name):
                        continue
                    for text in self._journal.latest_value(step.id, field.name) or []:
                        identifier = PrefixedItem(str(text)).identifier
                        if identifier is not None:
                            decided.add(identifier)
        return decided
