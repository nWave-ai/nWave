"""ShapeNormalizer — pure function canonicalising type-shape strings.

Tier-1 collision detection compares normalized strings for exact equality.
Two shapes that mean the same thing must produce the same canonical form.

Rules (this step — keep minimal, expand in 02-01):
  1. Strip all whitespace.
  2. Strip parameter names from tuple-form `(name: T, name: T)` → `(T,T)`.
  3. Idempotent: f(f(x)) == f(x).
"""

from __future__ import annotations

import re
from itertools import accumulate, pairwise


_WHITESPACE = re.compile(r"\s+")


def normalize_shape(raw: str) -> str:
    """Return the canonical form of a type-shape string."""
    no_ws = _WHITESPACE.sub("", raw)
    if not (no_ws.startswith("(") and no_ws.endswith(")")):
        return no_ws
    inner = no_ws[1:-1]
    return (
        "("
        + ",".join(
            normalize_shape(_take_type(part)) for part in _split_top_level(inner, ",")
        )
        + ")"
    )


def _split_top_level(text: str, separator: str) -> tuple[str, ...]:
    depths = tuple(accumulate(int(char in "([") - int(char in ")]") for char in text))
    boundaries = (
        -1,
        *(
            index
            for index, (char, depth) in enumerate(zip(text, depths, strict=True))
            if char == separator and depth == 0
        ),
        len(text),
    )
    return tuple(text[start + 1 : end] for start, end in pairwise(boundaries))


def _take_type(part: str) -> str:
    """For `name:T` return `T`; otherwise return the part unchanged."""
    parts = _split_top_level(part, ":")
    return ":".join(parts[1:]) if len(parts) > 1 else part
