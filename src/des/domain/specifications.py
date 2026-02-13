"""Specification pattern for composable business rules.

Provides composable specifications for validating domain objects,
making complex validation logic explicit and testable.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar


T = TypeVar("T")


class Specification(ABC, Generic[T]):
    """Abstract specification for validating domain objects.

    Specifications encapsulate business rules and can be composed
    using logical operators (and, or, not).
    """

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if the candidate satisfies this specification.

        Args:
            candidate: The object to validate

        Returns:
            True if candidate satisfies the specification, False otherwise
        """
        pass

    def and_(self, other: "Specification[T]") -> "AndSpecification[T]":
        """Combine this specification with another using AND logic.

        Args:
            other: Another specification to combine with

        Returns:
            Combined specification that requires both to be satisfied
        """
        return AndSpecification(self, other)

    def or_(self, other: "Specification[T]") -> "OrSpecification[T]":
        """Combine this specification with another using OR logic.

        Args:
            other: Another specification to combine with

        Returns:
            Combined specification that requires at least one to be satisfied
        """
        return OrSpecification(self, other)

    def not_(self) -> "NotSpecification[T]":
        """Negate this specification.

        Returns:
            Specification that is satisfied when this one is not
        """
        return NotSpecification(self)


class AndSpecification(Specification[T]):
    """Specification that combines two specifications with AND logic."""

    def __init__(self, left: Specification[T], right: Specification[T]):
        """Initialize with two specifications to combine.

        Args:
            left: First specification
            right: Second specification
        """
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies both specifications."""
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(
            candidate
        )


class OrSpecification(Specification[T]):
    """Specification that combines two specifications with OR logic."""

    def __init__(self, left: Specification[T], right: Specification[T]):
        """Initialize with two specifications to combine.

        Args:
            left: First specification
            right: Second specification
        """
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies at least one specification."""
        return self._left.is_satisfied_by(candidate) or self._right.is_satisfied_by(
            candidate
        )


class NotSpecification(Specification[T]):
    """Specification that negates another specification."""

    def __init__(self, spec: Specification[T]):
        """Initialize with specification to negate.

        Args:
            spec: Specification to negate
        """
        self._spec = spec

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate does NOT satisfy the wrapped specification."""
        return not self._spec.is_satisfied_by(candidate)


# Concrete specifications for phase validation


class PhaseIsExecutedSpecification(Specification[dict[str, Any]]):
    """Specification for checking if a phase is EXECUTED."""

    def is_satisfied_by(self, phase: dict[str, Any]) -> bool:
        """Check if phase status is EXECUTED."""
        return phase.get("status") == "EXECUTED"


class PhaseIsSkippedSpecification(Specification[dict[str, Any]]):
    """Specification for checking if a phase is SKIPPED."""

    def is_satisfied_by(self, phase: dict[str, Any]) -> bool:
        """Check if phase status is SKIPPED."""
        return phase.get("status") == "SKIPPED"


class PhaseIsInProgressSpecification(Specification[dict[str, Any]]):
    """Specification for checking if a phase is IN_PROGRESS."""

    def is_satisfied_by(self, phase: dict[str, Any]) -> bool:
        """Check if phase status is IN_PROGRESS."""
        return phase.get("status") == "IN_PROGRESS"


class PhaseHasOutcomeSpecification(Specification[dict[str, Any]]):
    """Specification for checking if a phase has an outcome field."""

    def is_satisfied_by(self, phase: dict[str, Any]) -> bool:
        """Check if phase has non-empty outcome."""
        outcome = phase.get("outcome")
        return outcome is not None and (
            not isinstance(outcome, str) or outcome.strip() != ""
        )


class PhaseHasBlockedByReasonSpecification(Specification[dict[str, Any]]):
    """Specification for checking if a phase has a blocked_by reason."""

    def is_satisfied_by(self, phase: dict[str, Any]) -> bool:
        """Check if phase has non-empty blocked_by reason."""
        blocked_by = phase.get("blocked_by")
        return blocked_by is not None and (
            not isinstance(blocked_by, str) or blocked_by.strip() != ""
        )


class ValidExecutedPhaseSpecification(Specification[dict[str, Any]]):
    """Specification for a valid EXECUTED phase (has outcome)."""

    def __init__(self):
        """Initialize composite specification."""
        self._executed = PhaseIsExecutedSpecification()
        self._has_outcome = PhaseHasOutcomeSpecification()

    def is_satisfied_by(self, phase: dict[str, Any]) -> bool:
        """Check if phase is EXECUTED and has outcome."""
        if not self._executed.is_satisfied_by(phase):
            return True  # Not EXECUTED, so rule doesn't apply
        return self._has_outcome.is_satisfied_by(phase)


class ValidSkippedPhaseSpecification(Specification[dict[str, Any]]):
    """Specification for a valid SKIPPED phase (has blocked_by reason)."""

    def __init__(self):
        """Initialize composite specification."""
        self._skipped = PhaseIsSkippedSpecification()
        self._has_reason = PhaseHasBlockedByReasonSpecification()

    def is_satisfied_by(self, phase: dict[str, Any]) -> bool:
        """Check if phase is SKIPPED and has blocked_by reason."""
        if not self._skipped.is_satisfied_by(phase):
            return True  # Not SKIPPED, so rule doesn't apply
        return self._has_reason.is_satisfied_by(phase)
