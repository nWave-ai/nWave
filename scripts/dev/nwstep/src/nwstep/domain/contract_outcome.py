"""What a contract check reports: its problems, and the warnings for each property it could not verify.

A warning is a could-not-verify statement: loud, with what, why and how, and never a pass.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContractOutcome:
    problems: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
