"""One numbered sentence of a request: its identifier S1..Sn and its text."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sentence:
    identifier: str
    text: str

    def line(self) -> str:
        return f"{self.identifier}: {self.text}"
