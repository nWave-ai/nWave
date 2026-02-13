"""
SilentLogger adapter - test logging implementation.

Provides a no-op logging implementation for testing environments where
log output is not needed or desired.
"""

from typing import Any

from des.ports.driven_ports.logging_port import LoggingPort


class SilentLogger(LoggingPort):
    """
    Test logging adapter that performs no operations.

    All logging methods are no-ops, making this ideal for test environments
    where log output would clutter test results or is unnecessary.
    """

    def log_validation_result(self, result: Any, context: dict[str, Any]) -> None:
        """
        No-op implementation of log_validation_result.

        Args:
            result: Ignored
            context: Ignored
        """
        pass

    def log_hook_execution(self, result: Any, step_file: str) -> None:
        """
        No-op implementation of log_hook_execution.

        Args:
            result: Ignored
            step_file: Ignored
        """
        pass

    def log_error(self, error: Exception, context: dict[str, Any]) -> None:
        """
        No-op implementation of log_error.

        Args:
            error: Ignored
            context: Ignored
        """
        pass
