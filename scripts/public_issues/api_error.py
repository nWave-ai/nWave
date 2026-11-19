"""A refused GitHub call, always stated as WHAT failed, WHY, and HOW to fix it."""

from __future__ import annotations


class ApiError(Exception):
    def __init__(self, what: str, why: str, how: str) -> None:
        super().__init__(f"WHAT: {what}. WHY: {why}. HOW: {how}.")
        self.what = what
        self.why = why
        self.how = how
