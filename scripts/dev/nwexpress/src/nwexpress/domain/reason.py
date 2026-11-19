"""The reason a finding is withdrawn: the reviewer's words on why its case was wrong. It is never blank."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reason:
    """A reason whose text is not blank once stripped; the value is the stripped text."""

    value: str

    def __post_init__(self) -> None:
        if Reason.problems(self.value):
            raise ValueError("a withdrawal reason must not be blank")

    @staticmethod
    def problems(given: str | None) -> list[str]:
        if given is None:
            return ["--reason is missing: a withdrawal says why the case was wrong"]
        if not given.strip():
            return ["--reason is empty: a withdrawal says why the case was wrong"]
        return []
