"""Jev consent: authorized or unauthorized, resolved from the first declared source in order."""

from __future__ import annotations

from enum import Enum


class JevConsent(Enum):
    AUTHORIZED = "authorized"
    UNAUTHORIZED = "unauthorized"

    @classmethod
    def parse(cls, raw: object) -> JevConsent:
        """Accept exactly the two declared values; any other value, including a non-text one, is refused."""
        for member in cls:
            if raw == member.value:
                return member
        raise ValueError(f"{raw!r} is not a declared Jev consent value")

    @staticmethod
    def first(*declared: JevConsent | None) -> JevConsent:
        """The first declared consent in precedence order; authorized when none is declared."""
        return next(
            (consent for consent in declared if consent is not None),
            JevConsent.AUTHORIZED,
        )
