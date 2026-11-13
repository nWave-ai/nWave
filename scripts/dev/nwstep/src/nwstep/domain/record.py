"""One accepted record: a revision of a step with the values it captured and the submission it was given from."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Record:
    seq: int
    step: str
    revision: int
    recorded_at: str
    values: dict[str, Any]
    given: dict[str, list[list[str]]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "seq": self.seq,
            "step": self.step,
            "revision": self.revision,
            "recorded_at": self.recorded_at,
            "values": self.values,
            "given": self.given,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Record:
        return cls(
            seq=int(data["seq"]),
            step=str(data["step"]),
            revision=int(data["revision"]),
            recorded_at=str(data["recorded_at"]),
            values=dict(data["values"]),
            given=dict(data.get("given", {})),
        )
