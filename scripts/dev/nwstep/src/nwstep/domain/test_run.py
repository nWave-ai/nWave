"""The counts and timings of a pytest run, read from its own output so that no count is typed by the executor."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


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

    _SUMMARY = re.compile(
        r"^(?:=+ )?((?:\d+ \w+(?:, )?)+) in (\d+(?:\.\d+)?)s(?: \([\d:]+\))?(?: =+)?$"
    )
    _COUNT = re.compile(r"(\d+) (\w+)")
    _SLOWEST = re.compile(r"^\s*(\d+(?:\.\d+)?)s (call|setup|teardown)\s+(\S+)")
    SLOWEST_KEPT = 10

    @classmethod
    def parse(cls, output: str) -> TestRun | None:
        """The last pytest summary line of the output, with the --durations lines that follow it; None when there is no summary."""
        summary = None
        slowest: list[SlowTest] = []
        for line in output.splitlines():
            found = cls._SUMMARY.match(line.strip())
            if found is not None:
                summary = found
            timing = cls._SLOWEST.match(line)
            if timing is not None:
                slowest.append(
                    SlowTest(float(timing.group(1)), timing.group(2), timing.group(3))
                )
        if summary is None:
            return None
        counts = tuple(
            (word, int(number)) for number, word in cls._COUNT.findall(summary.group(1))
        )
        return cls(
            counts=counts,
            seconds=float(summary.group(2)),
            slowest=tuple(slowest[: cls.SLOWEST_KEPT]),
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
