"""The rule a scenario's GIVEN and THEN must meet to be concrete."""

from __future__ import annotations

import re

from nwstep.domain.scenario import Scenario


class ScenarioRules:
    MIN_CHARS = 15
    QUOTES = ("'", '"', "`")
    LITERAL = re.compile(r"\b(true|false|null|none|empty)\b", re.IGNORECASE)
    DIGIT = re.compile(r"\d")

    def __init__(self, scenario: Scenario) -> None:
        self._scenario = scenario

    def problems(self) -> list[str]:
        return [
            f"{label} '{text}' needs at least {self.MIN_CHARS} characters and a digit, a quote or a literal (true, false, null, none, empty)"
            for label, text in (
                ("GIVEN", self._scenario.given),
                ("THEN", self._scenario.then),
            )
            if not self.concrete(text)
        ]

    @classmethod
    def concrete(cls, text: str) -> bool:
        return len(text) >= cls.MIN_CHARS and (
            cls.DIGIT.search(text) is not None
            or any(quote in text for quote in cls.QUOTES)
            or cls.LITERAL.search(text) is not None
        )
