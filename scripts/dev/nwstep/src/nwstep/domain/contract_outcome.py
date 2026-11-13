"""What a contract check reports: its problems, the could-not-verify warnings, and the diff lint it recorded."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContractOutcome:
    problems: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    lint: dict[str, object] | None = None
