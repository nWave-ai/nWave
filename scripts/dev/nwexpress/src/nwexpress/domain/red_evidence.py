"""The evidence an accepted RED keeps for one mapped test: the report case that failed, and why, as the report states it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    name: str
    case: str
    status: str
    kind: str
    message: str
