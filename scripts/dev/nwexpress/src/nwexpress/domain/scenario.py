"""One scenario as written: 'ID | PROMISE | GIVEN | WHEN | THEN', its five parts kept apart."""

from __future__ import annotations

import re


class Scenario:
    FORMAT = "ID | PROMISE | GIVEN ... | WHEN ... | THEN ..."
    _BARE = re.compile(r"[^\s:=|,]+")

    def __init__(
        self, identifier: str, promise: str, given: str, when: str, then: str
    ) -> None:
        self.identifier = identifier
        self.promise = promise
        self.given = given
        self.when = when
        self.then = then

    @classmethod
    def parse(cls, text: str) -> Scenario:
        parts = [part.strip() for part in text.split("|")]
        if len(parts) != 5 or not all(parts):
            raise ValueError(
                f"a scenario is written '{cls.FORMAT}' with five non-empty parts"
            )
        identifier, promise, given, when, then = parts
        if not (cls._BARE.fullmatch(identifier) and cls._BARE.fullmatch(promise)):
            raise ValueError(
                "the ID and the PROMISE are each one bare word without spaces, ':', '=', ',' or '|'"
            )
        return cls(
            identifier,
            promise,
            cls._clause(given, "GIVEN"),
            cls._clause(when, "WHEN"),
            cls._clause(then, "THEN"),
        )

    @classmethod
    def identifier_of(cls, text: str) -> str | None:
        """The ID a scenario opens with, before its first '|'; None when there is none."""
        head = text.split("|", 1)[0].strip()
        return head or None

    @staticmethod
    def _clause(part: str, keyword: str) -> str:
        """The content after the keyword label; the label itself is structure, not content."""
        head, _, content = part.partition(" ")
        if head != keyword or not content.strip():
            raise ValueError(
                f"the {keyword} part is written '{keyword} <content>' with content after the word {keyword}"
            )
        return content.strip()
