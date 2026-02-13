"""
LoggingPort interface for structured logging in DES.

Defines the contract for logging validation results, hook executions, and errors
throughout the DES lifecycle.
"""

from abc import ABC, abstractmethod
from typing import Any


class LoggingPort(ABC):
    """
    Port interface for logging operations in DES.

    Implementations provide different logging strategies (structured JSON,
    silent for testing, etc.) while maintaining a consistent interface.
    """

    @abstractmethod
    def log_validation_result(self, result: Any, context: dict[str, Any]) -> None:
        """
        Log the result of a validation operation.

        Args:
            result: The validation result object
            context: Additional context (step_file, turn number, etc.)
        """
        pass

    @abstractmethod
    def log_hook_execution(self, result: Any, step_file: str) -> None:
        """
        Log the execution of a hook.

        Args:
            result: The hook execution result
            step_file: Path to the step file being processed
        """
        pass

    @abstractmethod
    def log_error(self, error: Exception, context: dict[str, Any]) -> None:
        """
        Log an error that occurred during DES execution.

        Args:
            error: The exception that was raised
            context: Additional context about where the error occurred
        """
        pass
