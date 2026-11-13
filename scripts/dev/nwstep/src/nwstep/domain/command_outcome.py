"""The observed result of a command field: argv, exit code, duration, output tail and, when the output holds one, the pytest run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nwstep.domain.test_run import TestRun


@dataclass(frozen=True)
class CommandOutcome:
    argv: tuple[str, ...]
    exit_code: int | None
    duration_s: float
    output_tail: tuple[str, ...]
    problem: str | None = None
    output: str = ""

    def as_value(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "argv": list(self.argv),
            "exit_code": self.exit_code,
            "duration_s": round(self.duration_s, 3),
            "output_tail": list(self.output_tail),
        }
        run = TestRun.parse(self.output)
        if run is not None:
            value["tests"] = run.as_value()
        return value
