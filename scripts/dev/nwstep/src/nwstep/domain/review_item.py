"""One independent review item: 'REV1 | reviewer=ID | findings=TEXT | resolution=TEXT'.

The reviewer is recorded as written; the tool cannot verify that the reviewer is not the executor, so the brief
says so. The text parts are fixed in order and must not contain '|'.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewItem:
    identifier: str
    reviewer: str
    findings: str
    resolution: str

    SHAPE = "REV1 | reviewer=ID | findings=TEXT | resolution=TEXT"
    MIN_CHARS = 20
    _ID = re.compile(r"REV\d+")
    _KEYS = ("reviewer", "findings", "resolution")

    @classmethod
    def parse(cls, text: str) -> ReviewItem:
        parts = [part.strip() for part in text.split("|")]
        if len(parts) != 4 or not cls._ID.fullmatch(parts[0]):
            raise ValueError(f"write it as '{cls.SHAPE}'")
        values: dict[str, str] = {}
        for part, key in zip(parts[1:], cls._KEYS, strict=True):
            name, separator, value = part.partition("=")
            if not separator or name.strip() != key:
                raise ValueError(f"the part after the id must be '{key}=...'")
            values[key] = value.strip()
        if not values["reviewer"] or any(c.isspace() for c in values["reviewer"]):
            raise ValueError("the reviewer is one id without spaces")
        for key in ("findings", "resolution"):
            if len(values[key]) < cls.MIN_CHARS:
                raise ValueError(
                    f"{key} needs at least {cls.MIN_CHARS} characters, got {len(values[key])}"
                )
        return cls(
            parts[0], values["reviewer"], values["findings"], values["resolution"]
        )
