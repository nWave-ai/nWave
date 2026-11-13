"""The status of one step: how many revisions it has and what still blocks it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StepStatus:
    step_id: str
    revisions: int
    unmet: tuple[str, ...]

    @property
    def label(self) -> str:
        if self.revisions:
            return "ok"
        if self.unmet:
            return f"blocked(needs {', '.join(self.unmet)})"
        return "pending"
