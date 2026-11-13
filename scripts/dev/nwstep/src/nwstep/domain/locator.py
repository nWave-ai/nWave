"""A citation of one line of a file: 'src/app.py:12', found anywhere in an evidence text."""

from __future__ import annotations

import re


class Locator:
    _FORM = re.compile(r"(?P<path>[A-Za-z0-9_./-]+\.[A-Za-z0-9]+):(?P<line>\d+)")

    def __init__(self, path: str, line: int) -> None:
        self.path = path
        self.line = line

    @property
    def text(self) -> str:
        return f"{self.path}:{self.line}"

    @classmethod
    def find(cls, evidence: str) -> Locator | None:
        match = cls._FORM.search(evidence)
        if match is None:
            return None
        return cls(match.group("path"), int(match.group("line")))
