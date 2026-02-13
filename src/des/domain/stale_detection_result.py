"""
StaleDetectionResult Domain Entity

DOMAIN LAYER: Encapsulates the result of a stale execution detection scan.

Business Rules:
- Aggregates multiple StaleExecution instances
- is_blocked = True if stale_executions list is not empty
- Alert message format: 'Stale execution found: {step_file}, phase {phase_name} ({age} min)'
- Supports multiple stale executions
- Encapsulates stale_executions list to prevent external modification
- Collects warnings for corrupted/malformed step files during scan
- Warnings include file_path and error message for debugging

Usage:
    stale1 = StaleExecution(step_file="steps/01-01.json", phase_name="RED_UNIT",
                           age_minutes=45, started_at="2026-01-31T10:00:00Z")
    stale2 = StaleExecution(step_file="steps/02-01.json", phase_name="GREEN_UNIT",
                           age_minutes=60, started_at="2026-01-31T09:00:00Z")

    result = StaleDetectionResult(stale_executions=[stale1, stale2])

    if result.is_blocked:
        print(result.alert_message)
"""

from typing import Any

from des.domain.stale_execution import StaleExecution


class StaleDetectionResult:
    """
    Domain entity representing the result of a stale execution detection scan.

    Aggregates multiple StaleExecution instances and provides blocking logic
    and alert formatting.

    Attributes:
        stale_executions: List of detected StaleExecution instances (immutable copy)
        warnings: List of warnings for corrupted/malformed step files

    Properties:
        is_blocked: True if any stale executions exist, False otherwise
        alert_message: Formatted alert message for all stale executions

    Example:
        >>> stale = StaleExecution(
        ...     step_file="steps/01-01.json",
        ...     phase_name="RED_UNIT",
        ...     age_minutes=45,
        ...     started_at="2026-01-31T10:00:00Z"
        ... )
        >>> result = StaleDetectionResult(stale_executions=[stale])
        >>> result.is_blocked
        True
        >>> result.alert_message
        'Stale execution found: steps/01-01.json, phase RED_UNIT (45 min)'
    """

    def __init__(
        self,
        stale_executions: list[StaleExecution],
        warnings: list[dict[str, Any]] | None = None,
    ):
        """
        Initialize StaleDetectionResult with list of stale executions and warnings.

        Args:
            stale_executions: List of StaleExecution instances detected during scan
            warnings: List of warning dicts for corrupted files (default: empty list)
                     Each warning dict has keys: file_path, error

        Note:
            Lists are copied to prevent external modification (encapsulation)
        """
        # Create defensive copy to prevent external modification
        self._stale_executions = list(stale_executions)
        self._warnings = list(warnings) if warnings else []

    @property
    def stale_executions(self) -> list[StaleExecution]:
        """
        Get immutable copy of stale executions list.

        Returns:
            List of StaleExecution instances (defensive copy)

        Business Rule:
            Prevent external modification by returning copy
        """
        return list(self._stale_executions)

    @property
    def warnings(self) -> list[dict[str, Any]]:
        """
        Get immutable copy of warnings list.

        Returns:
            List of warning dicts (defensive copy)
            Each warning dict has keys: file_path, error

        Business Rule:
            Prevent external modification by returning copy
        """
        return list(self._warnings)

    @property
    def is_blocked(self) -> bool:
        """
        Determine if execution should be blocked due to stale executions.

        Returns:
            True if stale_executions list is not empty, False otherwise

        Business Rule:
            Execution is blocked if ANY stale executions exist
        """
        return len(self._stale_executions) > 0

    @property
    def alert_message(self) -> str:
        """
        Format alert message for all stale executions.

        Returns:
            Formatted alert message, empty string if no stale executions

        Format (single stale execution):
            'Stale execution found: {step_file}, phase {phase_name} ({age} min)'

        Format (multiple stale executions):
            Combined message with newlines separating each stale execution alert

        Business Rule:
            Alert message includes step file, phase name, and age for each stale execution
        """
        if not self._stale_executions:
            return ""

        if len(self._stale_executions) == 1:
            # Single stale execution - return single-line message
            stale = self._stale_executions[0]
            return self._format_single_alert(stale)

        # Multiple stale executions - combine with newlines
        alerts = [self._format_single_alert(stale) for stale in self._stale_executions]
        return "\n".join(alerts)

    def _format_single_alert(self, stale: StaleExecution) -> str:
        """
        Format alert message for a single stale execution.

        Args:
            stale: StaleExecution instance to format

        Returns:
            Formatted alert message

        Format:
            'Stale execution found: {step_file}, phase {phase_name} ({age} min)'
        """
        return (
            f"Stale execution found: {stale.step_file}, "
            f"phase {stale.phase_name} ({stale.age_minutes} min)"
        )
