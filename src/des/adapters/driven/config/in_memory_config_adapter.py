"""
InMemoryConfigAdapter - test configuration implementation.

Provides hardcoded configuration values for testing environments,
allowing predictable test behavior.
"""

from des.ports.driven_ports.config_port import ConfigPort


class InMemoryConfigAdapter(ConfigPort):
    """
    Test configuration adapter with hardcoded values.

    Returns predictable configuration values for testing, avoiding
    dependencies on environment variables or external configuration.
    """

    def __init__(self, max_turns: int = 10, timeout_threshold: int = 300):
        """
        Initialize with test configuration values.

        Args:
            max_turns: Default maximum turns (default: 10)
            timeout_threshold: Default timeout in seconds (default: 300)
        """
        self._max_turns = max_turns
        self._timeout_threshold = timeout_threshold

    def get_max_turns_default(self) -> int:
        """
        Get the hardcoded maximum turns default.

        Returns:
            int: Hardcoded max turns value
        """
        return self._max_turns

    def get_timeout_threshold_default(self) -> int:
        """
        Get the hardcoded timeout threshold default.

        Returns:
            int: Hardcoded timeout threshold in seconds
        """
        return self._timeout_threshold
