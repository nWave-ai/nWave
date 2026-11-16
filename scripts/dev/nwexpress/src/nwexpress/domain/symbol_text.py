"""Whether a symbol occurs in a file's text as a whole word.

The check reads no grammar of any language: a dotted symbol is found when each of its parts occurs as a whole word,
and a word is a run of letters, digits and underscores that the text does not extend on either side. It cannot tell
a definition from a mention; a witness that only mentions a symbol passes, and the review of the diff owns that gap.
"""

from __future__ import annotations

import re

_IDENTIFIER = re.compile(r"[^\W\d]\w*")


class SymbolText:
    @staticmethod
    def mentions(text: str, symbol: str) -> bool:
        """True when every dotted part of the symbol occurs in the text as a whole word."""
        parts = [part for part in symbol.split(".") if part]
        return bool(parts) and all(
            re.search(rf"(?<!\w){re.escape(part)}(?!\w)", text) is not None
            for part in parts
        )

    @staticmethod
    def identifiers(text: str) -> frozenset[str]:
        """Every identifier-shaped word of the text."""
        return frozenset(_IDENTIFIER.findall(text))
