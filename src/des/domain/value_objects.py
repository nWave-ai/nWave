"""Domain value objects for type-safe identifiers and statuses.

Replaces primitive obsession with explicit domain types that make
invalid states unrepresentable.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Self


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
    VALID_COMMANDS = ["/nw:execute", "/nw:develop", "/nw:research"]

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
        return self.value in ["/nw:execute", "/nw:develop"]
