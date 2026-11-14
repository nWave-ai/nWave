"""The observed result of a command field: argv, exit code, duration, output tail and, when the field declares a report, that report's outcome."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from nwstep.domain.report_outcome import NoReport, ReadReport, ReportOutcome
from nwstep.domain.test_run import TestRun


@dataclass(frozen=True)
class CommandOutcome:
    argv: tuple[str, ...]
    exit_code: int | None
    duration_s: float
    output_tail: tuple[str, ...]
    problem: str | None = None
    output: str = ""
    report: ReportOutcome = NoReport()
    timed_out_after: int | None = None

    def with_report(self, report: ReportOutcome) -> CommandOutcome:
        return replace(self, report=report)

    def as_value(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "argv": list(self.argv),
            "exit_code": self.exit_code,
            "duration_s": round(self.duration_s, 3),
            "output_tail": list(self.output_tail),
        }
        if isinstance(self.report, ReadReport):
            value["tests"] = TestRun.of(self.report.cases).as_value()
        return value
