"""The size of a delivery: S, M or L. A larger size makes every step of the smaller sizes due, and more besides.

A size is its label: a validated string, so a size compares equal to its label wherever a label is given.
"""

from __future__ import annotations

from nwstep.domain.refusal import Refusal


class Size(str):
    LABELS: tuple[str, ...] = ("S", "M", "L")
    # A schema without sizes runs every step, which is the size L of the earlier schemas.
    IMPLICIT_LABEL = "L"

    def __new__(cls, label: str) -> Size:
        if label not in cls.LABELS:
            raise ValueError(f"size '{label}' is not one of {', '.join(cls.LABELS)}")
        return super().__new__(cls, label)

    @classmethod
    def parse(cls, text: str) -> Size:
        """The size a command or a schema names; any other text is refused with the three sizes named."""
        if text not in cls.LABELS:
            raise Refusal(
                what=f"'{text}' is not a size: a delivery is size S, M or L",
                why="the size decides which steps are due; any other value would decide nothing",
                how="declare one of the three sizes, for example: nwstep size --size M --why '<one sentence>'",
            )
        return cls(text)

    @classmethod
    def implicit(cls) -> Size:
        return cls(cls.IMPLICIT_LABEL)

    @property
    def label(self) -> str:
        return str(self)

    @property
    def rank(self) -> int:
        return self.LABELS.index(self)

    def outranks(self, other: str) -> bool:
        return self.rank > Size(other).rank
