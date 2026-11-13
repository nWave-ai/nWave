"""The edge categories every interface is crossed with, unless the schema names its own."""

from __future__ import annotations


class EdgeCategory:
    DEFAULT: tuple[str, ...] = (
        "empty",
        "unknown",
        "malformed",
        "dependency-gone",
        "repeated",
        "concurrent",
        "crash",
    )
