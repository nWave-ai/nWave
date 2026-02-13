"""Timeout warning message builder.

Builds formatted timeout warning messages with elapsed time, percentage,
and remaining time information.
"""


class TimeoutWarningBuilder:
    """Builds formatted timeout warning messages."""

    def build_warning(
        self,
        phase_name: str,
        elapsed_minutes: int,
        threshold: int,
        duration_minutes: int | None = None,
    ) -> str:
        """Build formatted timeout warning message.

        Args:
            phase_name: Name of the phase being executed
            elapsed_minutes: Minutes elapsed since phase start
            threshold: Threshold value that was crossed
            duration_minutes: Total duration budget (optional)

        Returns:
            Formatted warning string with percentage and remaining time if duration provided
        """
        if duration_minutes:
            percentage = int((elapsed_minutes / duration_minutes) * 100)
            remaining = duration_minutes - elapsed_minutes
            return (
                f"TIMEOUT WARNING: Phase {phase_name} "
                f"{percentage}% elapsed ({elapsed_minutes}/{duration_minutes} minutes). "
                f"Remaining: {remaining} minutes."
            )
        else:
            return (
                f"TIMEOUT WARNING: Phase has been running for {elapsed_minutes} minutes "
                f"(crossed {threshold}-minute threshold). "
                f"Elapsed time: {elapsed_minutes}m"
            )
