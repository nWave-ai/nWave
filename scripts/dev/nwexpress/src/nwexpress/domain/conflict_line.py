"""One conflict line: 'S1 | NONE | reason' or 'S1 | CONFLICT | existing behaviour | question?'."""

from __future__ import annotations


class ConflictLine:
    NONE = "NONE"
    CONFLICT = "CONFLICT"
    MIN_CHARS = 20
    FORMAT = "'S1 | NONE | reason' or 'S1 | CONFLICT | existing behaviour | question ending with ?'"

    def __init__(
        self, identifier: str, verdict: str, reason: str, question: str
    ) -> None:
        self.identifier = identifier
        self.verdict = verdict
        self.reason = reason
        self.question = question

    @property
    def is_conflict(self) -> bool:
        return self.verdict == self.CONFLICT

    @classmethod
    def parse(cls, text: str) -> ConflictLine:
        parts = [part.strip() for part in text.split("|")]
        if len(parts) < 3:
            raise ValueError(f"a line is written {cls.FORMAT}")
        identifier, verdict = parts[0], parts[1]
        if verdict == cls.NONE:
            if len(parts) != 3:
                raise ValueError(f"a NONE line is written {cls.FORMAT}")
            question = ""
        elif verdict == cls.CONFLICT:
            if len(parts) != 4:
                raise ValueError(f"a CONFLICT line is written {cls.FORMAT}")
            question = parts[3]
            if not question.endswith("?"):
                raise ValueError("the question of a CONFLICT line ends with '?'")
        else:
            raise ValueError(f"the verdict is NONE or CONFLICT, got '{verdict}'")
        reason = parts[2]
        if len(reason) < cls.MIN_CHARS:
            label = "the reason" if verdict == cls.NONE else "the existing behaviour"
            raise ValueError(
                f"{label} needs at least {cls.MIN_CHARS} characters, got {len(reason)}"
            )
        return cls(identifier, verdict, reason, question)
