"""The id of the person who wrote a finding or a withdrawal, as the review log keeps it.

An author id is kept as given: the tool cannot verify who typed it. Its only rule is its length, which is owned here so
that every decision about an author reads the same rule.
"""

from __future__ import annotations

from dataclasses import dataclass


MIN_CHARS = 3


@dataclass(frozen=True)
class Author:
    """An author id that has passed `problems`; the value is the stripped text."""

    value: str

    def __post_init__(self) -> None:
        if Author.problems(self.value):
            raise ValueError(f"an author id needs at least {MIN_CHARS} characters")

    @staticmethod
    def problems(given: str) -> list[str]:
        length = len(given.strip())
        if length >= MIN_CHARS:
            return []
        return [f"--author needs at least {MIN_CHARS} characters, got {length}"]
