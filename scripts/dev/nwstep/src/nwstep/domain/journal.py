"""The journal as a value: ordered records and the questions the rules ask of them."""

from __future__ import annotations

from typing import Any

from nwstep.domain.record import Record


class Journal:
    def __init__(self, records: tuple[Record, ...] = ()) -> None:
        self._records = records

    @property
    def records(self) -> tuple[Record, ...]:
        return self._records

    def recorded(self, step_id: str) -> bool:
        return self.revisions(step_id) > 0

    def revisions(self, step_id: str) -> int:
        return sum(1 for record in self._records if record.step == step_id)

    def last_position(self, step_id: str) -> int:
        """Index of the latest record of the step, or -1 when it has none."""
        for index in range(len(self._records) - 1, -1, -1):
            if self._records[index].step == step_id:
                return index
        return -1

    def latest_value(self, step_id: str, field_name: str) -> Any:
        for record in reversed(self._records):
            if record.step == step_id:
                return record.values.get(field_name)
        return None

    def appended(self, record: Record) -> Journal:
        return Journal((*self._records, record))

    def to_list(self) -> list[dict[str, object]]:
        return [record.to_dict() for record in self._records]
