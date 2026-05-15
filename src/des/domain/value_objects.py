"""Domain value objects for type-safe identifiers and statuses.

Replaces primitive obsession with explicit domain types that make
invalid states unrepresentable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


try:
    from typing import Self
except ImportError:  # pragma: no cover — only hit on Python 3.10
    from typing_extensions import Self


class PhaseStatus(str, Enum):
    """Valid phase execution statuses.

    Makes invalid status values unrepresentable at the type level.
    """

    NOT_EXECUTED = "NOT_EXECUTED"
    IN_PROGRESS = "IN_PROGRESS"
    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"

    def is_complete(self) -> bool:
        """Check if phase is in a completed state."""
        return self in (PhaseStatus.EXECUTED, PhaseStatus.SKIPPED)

    def is_incomplete(self) -> bool:
        """Check if phase is in an incomplete state."""
        return not self.is_complete()


class PhaseOutcome(str, Enum):
    """Valid phase execution outcomes.

    Only applies to EXECUTED phases. Makes invalid outcome values
    unrepresentable at the type level.
    """

    PASS = "PASS"
    FAIL = "FAIL"


class PhaseName(str, Enum):
    """Valid TDD phase names across all schema versions.

    Dual-canon (ADR-025, 2026-05-07):
    - v5 canonical (3-phase): RED, GREEN, COMMIT.
    - v4 legacy (5-phase): PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT.
    All legacy members are retained for audit-log replay of pre-2026-05-07
    commits. ``is_canonical`` / ``to_canonical`` resolve between canons.
    """

    # v5.0 canonical (3-phase, ADR-025)
    RED = "RED"
    # v4.0 (5-phase streamlined) — legacy
    PREPARE = "PREPARE"
    RED_ACCEPTANCE = "RED_ACCEPTANCE"
    RED_UNIT = "RED_UNIT"
    GREEN = "GREEN"
    COMMIT = "COMMIT"
    # v3.0 additions (7-phase consolidated)
    REVIEW = "REVIEW"
    REFACTOR_CONTINUOUS = "REFACTOR_CONTINUOUS"
    # v2.0 additions (8-phase optimized)
    REFACTOR_L4 = "REFACTOR_L4"
    # v1.0 additions (14-phase full)
    GREEN_UNIT = "GREEN_UNIT"
    CHECK_ACCEPTANCE = "CHECK_ACCEPTANCE"
    GREEN_ACCEPTANCE = "GREEN_ACCEPTANCE"
    REFACTOR_L1 = "REFACTOR_L1"
    REFACTOR_L2 = "REFACTOR_L2"
    REFACTOR_L3 = "REFACTOR_L3"
    POST_REFACTOR_REVIEW = "POST_REFACTOR_REVIEW"
    FINAL_VALIDATE = "FINAL_VALIDATE"

    def is_canonical(self) -> bool:
        """True iff this phase belongs to the v5 canonical 3-phase contract.

        Canonical members: RED, GREEN, COMMIT.
        Everything else (PREPARE, RED_ACCEPTANCE, RED_UNIT, REVIEW, ...) is
        legacy and present only for backward-compat audit-log replay.
        """
        return self in (PhaseName.RED, PhaseName.GREEN, PhaseName.COMMIT)

    def to_canonical(self) -> PhaseName:
        """Collapse a legacy phase name onto its canonical (v5) equivalent.

        Mapping (per ADR-025):
        - PREPARE, RED_ACCEPTANCE, RED_UNIT → RED
        - GREEN, GREEN_UNIT, GREEN_ACCEPTANCE, CHECK_ACCEPTANCE → GREEN
        - COMMIT, POST_REFACTOR_REVIEW, FINAL_VALIDATE → COMMIT
        - REVIEW, REFACTOR_* → COMMIT (collapsed into the COMMIT-side
          refactor/review pass that the canonical cycle treats as part of
          post-GREEN COMMIT activity)

        Canonical members map to themselves.
        """
        if self in (PhaseName.RED, PhaseName.GREEN, PhaseName.COMMIT):
            return self
        if self in (
            PhaseName.PREPARE,
            PhaseName.RED_ACCEPTANCE,
            PhaseName.RED_UNIT,
        ):
            return PhaseName.RED
        if self in (
            PhaseName.GREEN_UNIT,
            PhaseName.GREEN_ACCEPTANCE,
            PhaseName.CHECK_ACCEPTANCE,
        ):
            return PhaseName.GREEN
        # REVIEW, REFACTOR_*, POST_REFACTOR_REVIEW, FINAL_VALIDATE all
        # collapse to COMMIT in the canonical cycle.
        return PhaseName.COMMIT


class ValidationStatus(str, Enum):
    """Valid validation result statuses."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class StepId:
    """Strongly-typed step identifier.

    Prevents accidental confusion between step IDs and other string values.
    Immutable to ensure identity consistency.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate step ID format."""
        if not self.value:
            raise ValueError("Step ID cannot be empty")
        if not self.value.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"Step ID must be alphanumeric with hyphens/underscores: {self.value}"
            )

    def __str__(self) -> str:
        """Return string representation for display."""
        return self.value

    @classmethod
    def from_step_file_path(cls, step_file: str) -> Self:
        """Extract step ID from step file path.

        Args:
            step_file: Path to step file (e.g., "step-01-setup.json")

        Returns:
            StepId extracted from filename without extension
        """
        import os

        basename = os.path.basename(step_file)
        step_id = os.path.splitext(basename)[0]
        return cls(step_id)


@dataclass(frozen=True)
class FeatureName:
    """Strongly-typed feature/project identifier.

    Prevents accidental confusion between feature names and other string values.
    Immutable to ensure identity consistency.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate feature name format."""
        if not self.value:
            raise ValueError("Feature name cannot be empty")

    def __str__(self) -> str:
        """Return string representation for display."""
        return self.value


@dataclass(frozen=True)
class AgentName:
    """Strongly-typed agent identifier.

    Prevents accidental confusion between agent names and other string values.
    Immutable to ensure identity consistency.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate agent name format."""
        if not self.value:
            raise ValueError("Agent name cannot be empty")
        if not self.value.replace("-", "").isalnum():
            raise ValueError(
                f"Agent name must be alphanumeric with hyphens: {self.value}"
            )

    def __str__(self) -> str:
        """Return string representation for display."""
        return self.value


@dataclass(frozen=True)
class CommandName:
    """Strongly-typed command identifier.

    Ensures commands are validated and prevents typos.
    Immutable to ensure identity consistency.
    """

    value: str

    # Valid DES commands
    VALID_COMMANDS = ["/nw-execute", "/nw-develop", "/nw-research"]

    def __post_init__(self) -> None:
        """Validate command format."""
        if not self.value:
            raise ValueError("Command name cannot be empty")
        if not self.value.startswith("/"):
            raise ValueError(f"Command must start with '/': {self.value}")

    def __str__(self) -> str:
        """Return string representation for display."""
        return self.value

    def is_validation_command(self) -> bool:
        """Check if this command requires DES validation."""
        return self.value in ["/nw-execute", "/nw-develop"]
