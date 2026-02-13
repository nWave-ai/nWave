"""Production implementation of time provider adapter."""

from datetime import datetime, timezone

from des.ports.driven_ports.time_provider_port import TimeProvider


class SystemTimeProvider(TimeProvider):
    """Production implementation of time provider.

    Returns actual system time in UTC.
    """

    def now_utc(self) -> datetime:
        """Get current UTC time.

        Returns:
            Current datetime in UTC timezone
        """
        return datetime.now(timezone.utc)
