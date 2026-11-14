"""Whether a preserve case protects a file the change touched.

A protection is never stated as executed: no language-neutral observation shows that a run executed a file, so a
protected file of the change is reported could-not-verify with its reason.
"""

from __future__ import annotations


class ProtectionCheck:
    NOT_APPLICABLE = "not-applicable"
    NOT_CHANGED = "not-changed"
    COULD_NOT_VERIFY = "could-not-verify"

    def __init__(self, status: str, path: str | None, detail: str = "") -> None:
        self.status = status
        self.path = path
        self.detail = detail

    @classmethod
    def not_applicable(cls) -> ProtectionCheck:
        return cls(cls.NOT_APPLICABLE, None)

    @classmethod
    def not_changed(cls, path: str) -> ProtectionCheck:
        return cls(
            cls.NOT_CHANGED, path, "it is not among the files changed from BASE to HEAD"
        )

    @classmethod
    def could_not_verify(cls, path: str, reason: str) -> ProtectionCheck:
        return cls(cls.COULD_NOT_VERIFY, path, reason)

    def describe(self) -> str:
        """The protection part of a brief line; empty when the case is not a preserve case."""
        if self.status == self.NOT_APPLICABLE:
            return ""
        if self.status == self.COULD_NOT_VERIFY:
            return f"protects {self.path}: could not be verified: {self.detail}"
        return f"protects {self.path}: {self.status} ({self.detail})"

    def as_value(self) -> dict[str, object]:
        return {"status": self.status, "path": self.path, "detail": self.detail}
