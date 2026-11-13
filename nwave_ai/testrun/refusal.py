"""A refusal of the test queue or the test selector: what, why and how to repair."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Refusal:
    """Why nothing was done, in the three parts every nWave refusal has."""

    what: str
    why: str
    how: str

    def lines(self) -> tuple[str, str, str]:
        return (f"WHAT: {self.what}", f"WHY: {self.why}", f"HOW: {self.how}")

    def as_document(self) -> dict[str, str]:
        return {"what": self.what, "why": self.why, "how": self.how}
