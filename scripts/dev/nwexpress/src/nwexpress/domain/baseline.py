"""The pre-feature baseline a workspace records: the repository top and the base commit, or the loud reason there is
none. The tree itself is never copied into the workspace; a step that needs it reads it from git while it runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Baseline:
    top: str | None
    sha: str | None
    reason: str | None

    @classmethod
    def available(cls, top: str, sha: str) -> Baseline:
        return cls(top=top, sha=sha, reason=None)

    @classmethod
    def unavailable(cls, reason: str) -> Baseline:
        return cls(top=None, sha=None, reason=reason)

    @property
    def is_available(self) -> bool:
        return self.reason is None

    def unverifiable_for(self, root: Path) -> str | None:
        """Why the differential cannot run for a record in this root; None when it can."""
        if self.reason is not None:
            return self.reason
        if self.top is None or Path(self.top).resolve() != root.resolve():
            return f"the record root {root} is not the repository {self.top} that the pre-feature tree was taken from"
        return None

    def to_value(self) -> dict[str, Any]:
        return {"top": self.top, "sha": self.sha, "reason": self.reason}

    @classmethod
    def from_value(cls, value: dict[str, Any]) -> Baseline:
        return cls(top=value["top"], sha=value["sha"], reason=value["reason"])
