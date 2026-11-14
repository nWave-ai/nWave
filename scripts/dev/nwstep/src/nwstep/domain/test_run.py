"""The counts and timings of a run, read from its declared report so that no count is typed by the executor.

The counts are the report's testcases by status and add up to the testcase total; the seconds are the sum of the
testcase times the report gives. A report with no testcase is a run that names no test, which the record refuses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nwstep.domain.report_case import ReportCase
from nwstep.domain.report_status import ReportStatus


@dataclass(frozen=True)
class SlowTest:
    seconds: float
    phase: str
    test: str


@dataclass(frozen=True)
class TestRun:
    counts: tuple[tuple[str, int], ...]
    seconds: float
    slowest: tuple[SlowTest, ...]

    SLOWEST_KEPT = 10
    CALL = "call"

    @classmethod
    def of(cls, cases: tuple[ReportCase, ...]) -> TestRun:
        statuses = [case.status for case in cases]
        counts = (
            ("tests", len(cases)),
            ("passed", statuses.count(ReportStatus.PASSED)),
            ("failures", statuses.count(ReportStatus.FAILURE)),
            ("errors", statuses.count(ReportStatus.ERRORED)),
            ("skipped", statuses.count(ReportStatus.SKIPPED)),
        )
        ranked = sorted(cases, key=lambda case: case.seconds, reverse=True)
        return cls(
            counts=counts,
            seconds=sum(case.seconds for case in cases),
            slowest=tuple(
                SlowTest(case.seconds, cls.CALL, case.name)
                for case in ranked[: cls.SLOWEST_KEPT]
            ),
        )

    def as_value(self) -> dict[str, Any]:
        return {
            "counts": dict(self.counts),
            "seconds": round(self.seconds, 3),
            "slowest": [
                {"seconds": item.seconds, "phase": item.phase, "test": item.test}
                for item in self.slowest
            ],
        }
