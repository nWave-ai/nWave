"""Test implementation of time provider adapter."""

from datetime import datetime, timedelta, timezone

from des.ports.driven_ports.time_provider_port import TimeProvider


class MockedTimeProvider(TimeProvider):
    """Test implementation of time provider.

    Returns fixed/controllable time for deterministic testing.
    Allows advancing time programmatically for timeout testing.
    """

    def __init__(self, fixed_time: datetime | None = None):
        """Initialize with optional fixed time.

        Args:
            fixed_time: Fixed datetime to return from now_utc().
                       Defaults to 2026-01-26T10:00:00Z if not provided.
        """
        if fixed_time is None:
            fixed_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        self._current_time = fixed_time

    def now_utc(self) -> datetime:
        """Get current mocked UTC time.

        Returns:
            Current datetime (fixed or advanced via advance())
        """
        return self._current_time

    def advance(self, minutes: int = 0, seconds: int = 0) -> None:
        """Advance mocked time forward.

        Convenience method for simulating time passage in tests.

        Args:
            minutes: Minutes to advance
            seconds: Seconds to advance
        """
        self._current_time += timedelta(minutes=minutes, seconds=seconds)

    def set_time(self, new_time: datetime) -> None:
        """Set mocked time to specific value.

        Convenience method for test scenarios requiring specific timestamps.

        Args:
            new_time: New datetime to use for subsequent now_utc() calls
        """
        self._current_time = new_time
