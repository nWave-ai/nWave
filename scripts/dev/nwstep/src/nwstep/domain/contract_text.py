"""Splits a contract item on '|' into its named parts, and reads the explicit 'ID | none: reason' form."""

from __future__ import annotations


class ContractText:
    NONE_PREFIX = "none:"
    MIN_NONE_REASON = 20

    @classmethod
    def parts(cls, text: str, count: int, shape: str) -> list[str]:
        """The stripped parts; every part must be non-empty and there must be exactly count of them."""
        parts = [part.strip() for part in text.split("|")]
        if len(parts) != count or not all(parts):
            raise ValueError(f"write it as '{shape}'")
        return parts

    @classmethod
    def none_reason(cls, text: str, identifier: str) -> str | None:
        """The reason of an 'ID | none: reason' item, or None when the item is not that form."""
        parts = [part.strip() for part in text.split("|")]
        if len(parts) != 2 or not parts[1].startswith(cls.NONE_PREFIX):
            return None
        if parts[0] != identifier:
            raise ValueError(f"the none form is written '{identifier} | none: reason'")
        reason = parts[1][len(cls.NONE_PREFIX) :].strip()
        if len(reason) < cls.MIN_NONE_REASON:
            raise ValueError(
                f"a none reason needs at least {cls.MIN_NONE_REASON} characters"
            )
        return reason

    @staticmethod
    def keyed(part: str, key: str) -> str:
        """The value of a 'key=value' part; the key must be the one named."""
        name, separator, value = part.partition("=")
        if name.strip() != key or not separator or not value.strip():
            raise ValueError(f"the part '{part}' should read '{key}=...' with a value")
        return value.strip()
