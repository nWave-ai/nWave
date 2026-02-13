"""
StaleExecution Value Object

DOMAIN LAYER: Represents a single stale execution detected during pre-execution scanning.

Business Rules:
- Immutable value object (frozen dataclass)
- age_minutes must be >= 0 (business validation)
- No external dependencies (pure domain entity)
- Value object equality semantics (compared by values, not identity)

Usage:
    stale = StaleExecution(
        step_file="steps/01-01.json",
        phase_name="RED_UNIT",
        age_minutes=45,
        started_at="2026-01-31T10:00:00Z"
    )
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StaleExecution:
    """
    Immutable value object representing a stale execution detection.

    Attributes:
        step_file: Path to the step file with stale execution (e.g., "steps/01-01.json")
        phase_name: Name of the phase that is IN_PROGRESS (e.g., "RED_UNIT")
        age_minutes: How many minutes since the phase started (must be >= 0)
        started_at: ISO 8601 timestamp when the phase started

    Raises:
        ValueError: If age_minutes < 0 (business validation)

    Example:
        >>> stale = StaleExecution(
        ...     step_file="steps/01-01.json",
        ...     phase_name="RED_UNIT",
        ...     age_minutes=45,
        ...     started_at="2026-01-31T10:00:00Z"
        ... )
        >>> stale.age_minutes
        45
    """

    step_file: str
    phase_name: str
    age_minutes: int
    started_at: str

    def __post_init__(self):
        """
        Validate business rules after dataclass initialization.

        Business Rule: age_minutes must be >= 0
        - Negative age doesn't make sense in the domain
        - Zero age is valid (execution just started and already detected as stale)

        Raises:
            ValueError: If age_minutes < 0
        """
        if self.age_minutes < 0:
            raise ValueError(
                f"age_minutes must be >= 0, got {self.age_minutes}. "
                "Negative age is invalid in the domain."
            )

    @property
    def message(self) -> str:
        """
        Format alert message with resolution instructions.

        Returns:
            Formatted alert message including step file, phase name, age, and resolution instructions

        Format:
            'Stale execution found: {step_file}, phase {phase_name} ({age} min). Resolve before proceeding.'

        Business Rule:
            Alert message must guide user to resolve the stale execution before proceeding
        """
        return (
            f"Stale execution found: {self.step_file}, "
            f"phase {self.phase_name} ({self.age_minutes} min). "
            "Resolve before proceeding."
        )
