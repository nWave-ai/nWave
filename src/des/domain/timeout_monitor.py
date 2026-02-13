"""TimeoutMonitor component for tracking phase execution time.

This module provides functionality to monitor elapsed time from a phase start
timestamp and detect when duration thresholds are crossed.
"""

from datetime import datetime, timezone

from des.ports.driven_ports.time_provider_port import TimeProvider


class TimeoutMonitor:
    """Monitors elapsed time from phase start and detects threshold crossings.

    Tracks time elapsed since a phase started and can check if specific
    duration thresholds have been crossed.
    """

    def __init__(self, started_at: str, time_provider: TimeProvider):
        """Initialize TimeoutMonitor with phase start timestamp and time provider.

        Args:
            started_at: ISO 8601 format timestamp string (timezone-aware)
            time_provider: TimeProvider port for time operations

        Raises:
            ValueError: If started_at is None or invalid format
        """
        if started_at is None:
            raise ValueError("started_at cannot be None")

        try:
            self.started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid timestamp format: {started_at}") from e

        # Ensure timezone-aware
        if self.started_at.tzinfo is None:
            self.started_at = self.started_at.replace(tzinfo=timezone.utc)

        # Store injected time provider
        self._time_provider = time_provider

    def get_elapsed_seconds(self) -> float:
        """Calculate elapsed seconds from phase start to now.

        Returns:
            Number of seconds elapsed (can be negative if started_at is in future)
        """
        now = self._time_provider.now_utc()
        elapsed = (now - self.started_at).total_seconds()
        return elapsed

    def check_thresholds(self, duration_minutes: list[int]) -> list[int]:
        """Check which duration thresholds have been crossed.

        Args:
            duration_minutes: List of threshold values in minutes to check against

        Returns:
            Sorted list of thresholds that have been crossed (in ascending order)
        """
        if not duration_minutes:
            return []

        elapsed_minutes = self.get_elapsed_seconds() / 60

        # Find all crossed thresholds
        crossed = [
            threshold for threshold in duration_minutes if threshold <= elapsed_minutes
        ]

        # Return in ascending order
        return sorted(crossed)
