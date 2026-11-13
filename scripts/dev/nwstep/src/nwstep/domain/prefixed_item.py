"""An item that may open with a prefix id: 'P1: text' or 'P1 => test'."""

from __future__ import annotations

import re


class PrefixedItem:
    _SEPARATOR = re.compile(r":|=>")

    def __init__(self, text: str) -> None:
        self.text = text
        match = self._SEPARATOR.search(text)
        identifier = text[: match.start()].strip() if match else ""
        self.identifier: str | None = identifier or None
        body = text[match.end() :].strip() if match else ""
        self.not_applicable = body.startswith("n/a:")
