from abc import ABC, abstractmethod
from datetime import datetime


class TimeProvider(ABC):
    """Port for time operations."""

    @abstractmethod
    def now_utc(self) -> datetime:
        """Get current UTC time.

        Returns:
            Current datetime in UTC timezone
        """
        pass
