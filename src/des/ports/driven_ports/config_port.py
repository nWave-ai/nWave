"""
ConfigPort interface for configuration management in DES.

Defines the contract for accessing configuration values, abstracting away
the configuration source (environment variables, in-memory, etc.).
"""

from abc import ABC, abstractmethod


class ConfigPort(ABC):
    """
    Port interface for configuration access.

    Implementations provide different configuration sources (environment
    variables for production, hardcoded values for testing, etc.) while
    maintaining a consistent interface.
    """

    @abstractmethod
    def get_max_turns_default(self) -> int:
        """
        Get the default maximum number of turns allowed.

        Returns:
            int: Default maximum turns
        """
        pass

    @abstractmethod
    def get_timeout_threshold_default(self) -> int:
        """
        Get the default timeout threshold in seconds.

        Returns:
            int: Default timeout threshold in seconds
        """
        pass
