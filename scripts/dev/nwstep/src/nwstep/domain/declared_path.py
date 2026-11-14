"""A path a record declares: relative to the root, inside it, never escaping through '..'.

The field that holds a step's test files is named here once: the RED copies those files, the mapped names are found in
them, a refactor commit may not edit them, and the handoff claims read them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

TEST_FILES = "tests"


@dataclass(frozen=True)
class DeclaredPath:
    text: str

    @classmethod
    def parse(cls, text: str) -> DeclaredPath:
        """The path as declared; a ValueError names why it is not a relative path inside the root."""
        pure = PurePosixPath(text.strip())
        if not text.strip() or pure.is_absolute() or ".." in pure.parts:
            raise ValueError(f"'{text}' must be a relative path inside the root")
        return cls(pure.as_posix())
