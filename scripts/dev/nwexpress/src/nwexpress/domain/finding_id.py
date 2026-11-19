"""The identifier of a finding, as the status prints it, such as F1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FindingId:
    """A finding identifier whose text is not blank once stripped; the value is the stripped text."""

    value: str

    def __post_init__(self) -> None:
        if FindingId.problems(self.value):
            raise ValueError("a finding identifier must not be blank")

    @staticmethod
    def problems(given: str) -> list[str]:
        if given.strip():
            return []
        return [
            "--finding is empty: name the finding by the identifier the status prints, such as F1"
        ]
