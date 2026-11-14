"""What the shell found at a cited path, read and not yet interpreted."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Absent:
    """Nothing exists at the cited path."""


@dataclass(frozen=True)
class FolderAt:
    """A folder sits at the cited path."""


@dataclass(frozen=True)
class OutsideRoot:
    """The cited path resolves outside the repository root."""


@dataclass(frozen=True)
class NotText:
    """A file sits at the cited path but its bytes are not UTF-8 text."""


@dataclass(frozen=True)
class TextFile:
    """A readable text file, with its content."""

    content: str


Observation = Absent | FolderAt | OutsideRoot | NotText | TextFile
