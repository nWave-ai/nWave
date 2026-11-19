"""The card line of a request: the card ids the board reads from the first line of REQUEST.md."""

from __future__ import annotations

import re
from dataclasses import dataclass


CARD_ID = re.compile(r"t-\d{4,}")
SEPARATOR = ", "


@dataclass(frozen=True)
class RequestCard:
    ids: tuple[str, ...]

    @classmethod
    def parse(cls, text: str) -> RequestCard | None:
        """The card ids named by text, separated by commas, or None when one of them is not an id the board reads."""
        ids = tuple(part.strip() for part in text.split(","))
        if not all(CARD_ID.fullmatch(card_id) for card_id in ids):
            return None
        return cls(ids)

    def text(self) -> str:
        """The ids as the card line writes them: separated by comma and space, the form the board reads."""
        return SEPARATOR.join(self.ids)
