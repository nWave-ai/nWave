"""The closed set of actions the silence rule can answer, each with the reason it gives.

Each action is one short write sequence whose every call is idempotent. The pass applies one
action, reads the issue again and decides again, so a failed call leaves a state that the next
decision repairs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Nothing:
    reason: str
    verb: ClassVar[str] = "nothing"


@dataclass(frozen=True)
class RemoveMarker:
    reason: str
    verb: ClassVar[str] = "remove-marker"


@dataclass(frozen=True)
class Close:
    """Set the closed label, then close as completed."""

    reason: str
    verb: ClassVar[str] = "close"


@dataclass(frozen=True)
class Thank:
    """Post the approved thank-you of a close that is missing it."""

    reason: str
    verb: ClassVar[str] = "thank"


@dataclass(frozen=True)
class DropClosedLabel:
    reason: str
    verb: ClassVar[str] = "drop-closed-label"


@dataclass(frozen=True)
class Reopen:
    """Reopen a closed issue; announce first when the reply is not yet announced."""

    reason: str
    by_author: bool
    announce: bool
    verb: ClassVar[str] = "reopen"


Action = Nothing | RemoveMarker | Close | Thank | DropClosedLabel | Reopen
