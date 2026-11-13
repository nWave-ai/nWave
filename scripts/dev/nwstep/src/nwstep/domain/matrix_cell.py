"""One cell of an edge matrix: 'I1.empty => case => expected', or 'I1.empty => n/a: reason' when the cell cannot occur."""

from __future__ import annotations

from nwstep.domain.prefixed_item import PrefixedItem


class MatrixCell:
    MIN_REASON = 15
    _SHAPE = "write 'I1.empty => case => expected' or 'I1.empty => n/a: reason'"

    def __init__(
        self,
        identifier: str,
        case: str | None,
        expected: str | None,
        reason: str | None,
    ) -> None:
        self.identifier = identifier
        self.case = case
        self.expected = expected
        self.reason = reason

    @property
    def not_applicable(self) -> bool:
        return self.reason is not None

    @classmethod
    def parse(cls, text: str) -> MatrixCell:
        identifier = PrefixedItem(text).identifier
        head, separator, body = text.partition("=>")
        if identifier is None or not separator or head.strip() != identifier:
            raise ValueError(cls._SHAPE)
        stripped = body.strip()
        if stripped.startswith("n/a:"):
            reason = stripped[len("n/a:") :].strip()
            if len(reason) < cls.MIN_REASON:
                raise ValueError(
                    f"a n/a reason needs at least {cls.MIN_REASON} characters"
                )
            return cls(identifier, None, None, reason)
        case, second, expected = stripped.partition("=>")
        if not second or not case.strip() or not expected.strip():
            raise ValueError(cls._SHAPE)
        return cls(identifier, case.strip(), expected.strip(), None)
