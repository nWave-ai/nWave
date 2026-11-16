"""The Jev outcome a step records: one of four closed forms, kept as its canonical text."""

from __future__ import annotations


class TypesafeOutcome:
    FORMS = ("requested", "unavailable", "refused")
    NO_OPEN_CHOICE = "no open choice"
    FORMAT = (
        "requested: REFERENCE, unavailable: REASON, refused: REASON or no open choice"
    )

    def __init__(self, text: str) -> None:
        self._text = text

    @property
    def text(self) -> str:
        return self._text

    @classmethod
    def parse(cls, raw: str) -> TypesafeOutcome:
        """Accept exactly the four forms, with a non-empty detail after each colon; refuse everything else."""
        text = raw.strip()
        if text == cls.NO_OPEN_CHOICE:
            return cls(text)
        form, separator, detail = text.partition(":")
        if separator and form in cls.FORMS and detail.strip():
            return cls(f"{form}: {detail.strip()}")
        raise ValueError(f"the typesafe outcome must be {cls.FORMAT}, got {raw!r}")
