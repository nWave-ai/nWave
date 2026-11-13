"""One prediction made in the oracle, before any code exists: 'ID => base held' or 'ID => base differs'.

It names the outcome a probe case is expected to show on the pre-feature tree. The probe compares it with what
was observed; a mismatch is a surprise the brief shows, never a refusal.
"""

from __future__ import annotations

import re


class Prediction:
    HELD = "held"
    DIFFERS = "differs"
    SHAPE = "ID => base held | base differs"
    _ITEM = re.compile(r"^\s*([^\s=]+)\s*=>\s*base\s+(held|differs)\s*$")

    def __init__(self, identifier: str, status: str) -> None:
        self.identifier = identifier
        self.status = status

    @classmethod
    def parse(cls, text: str) -> Prediction:
        found = cls._ITEM.match(text)
        if found is None:
            raise ValueError(f"write a prediction as '{cls.SHAPE}'")
        return cls(found.group(1), found.group(2))
