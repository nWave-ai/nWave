"""The size a delivery declares, with its motivation. A lowering keeps the owner's note and the owner's id."""

from __future__ import annotations

from typing import Any

from nwstep.domain.refusal import Refusal
from nwstep.domain.size import Size


class SizeDeclaration:
    """A size and the sentence that motivates it. When the size was lowered, the note and author of the owner are kept."""

    def __init__(
        self,
        size: Size,
        motivation: str,
        *,
        lowered_from: Size | None = None,
        owner_note: str | None = None,
        author: str | None = None,
    ) -> None:
        if not motivation.strip():
            raise ValueError("a size declaration needs its motivation")
        if lowered_from is not None and not (owner_note and author):
            raise ValueError("a lowered size needs the owner's note and the owner's id")
        self.size = size
        self.motivation = motivation.strip()
        self.lowered_from = lowered_from
        self.owner_note = owner_note
        self.author = author

    @classmethod
    def declare(
        cls,
        current: SizeDeclaration | None,
        size: Size,
        motivation: str,
        *,
        owner_note: str | None = None,
        author: str | None = None,
    ) -> SizeDeclaration:
        """The declaration a size command makes. The same size as now returns the current declaration unchanged;
        a lowering without the owner's note and id is refused, and a raise needs no note."""
        if current is None:
            return cls(size, motivation)
        if size == current.size:
            return current
        if size.outranks(current.size):
            return cls(size, motivation)
        if not (owner_note and author):
            raise Refusal(
                what=f"lowering the size from {current.size} to {size} needs an owner note and the owner's id",
                why="a smaller size drops steps the larger one made due, so only the owner may accept that in writing",
                how=(
                    f"nwstep size --size {size} --why '<one sentence>' "
                    "--owner-note '<the owner's note>' --author '<the owner's id>'"
                ),
            )
        return cls(
            size,
            motivation,
            lowered_from=current.size,
            owner_note=owner_note,
            author=author,
        )

    def describe(self) -> str:
        """The one line the status shows: the size, the motivation, and for a lowering the note and its author."""
        line = f"{self.size} - {self.motivation}"
        if self.lowered_from is None:
            return line
        return f"{line} (lowered from {self.lowered_from} by {self.author}: {self.owner_note})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "size": self.size.label,
            "motivation": self.motivation,
            "lowered_from": None
            if self.lowered_from is None
            else self.lowered_from.label,
            "owner_note": self.owner_note,
            "author": self.author,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SizeDeclaration:
        lowered = data.get("lowered_from")
        return cls(
            Size(data["size"]),
            data["motivation"],
            lowered_from=None if lowered is None else Size(lowered),
            owner_note=data.get("owner_note"),
            author=data.get("author"),
        )
