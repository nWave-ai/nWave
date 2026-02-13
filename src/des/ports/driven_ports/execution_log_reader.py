"""ExecutionLogReader - driven port for reading execution log data.

Abstract interface defining how the application layer reads step execution
events from the append-only execution log.

Defined by: Application layer needs (NOT by YAML format).
Implemented by: YamlExecutionLogReader (infrastructure adapter).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from des.domain.phase_event import PhaseEvent


class LogFileNotFound(Exception):
    """Raised when the execution log file does not exist."""


class LogFileCorrupted(Exception):
    """Raised when the execution log file cannot be parsed."""


class ExecutionLogReader(ABC):
    """Driven port: reads step execution events from the execution log.

    The application layer defines WHAT data it needs (project ID, phase events).
    The adapter decides HOW to read it (YAML, JSON, database, etc.).
    """

    @abstractmethod
    def read_project_id(self, log_path: str) -> str | None:
        """Read the project_id from the execution log.

        Args:
            log_path: Absolute path to the execution log file

        Returns:
            Project ID string, or None if not found in the log

        Raises:
            LogFileNotFound: If the log file does not exist
            LogFileCorrupted: If the log file cannot be parsed
        """
        ...

    @abstractmethod
    def read_step_events(self, log_path: str, step_id: str) -> list[PhaseEvent]:
        """Read and parse phase events for a specific step.

        Translates raw log format into domain PhaseEvent objects.

        Args:
            log_path: Absolute path to the execution log file
            step_id: Step identifier to filter events for

        Returns:
            List of PhaseEvent objects matching the step_id

        Raises:
            LogFileNotFound: If the log file does not exist
            LogFileCorrupted: If the log file cannot be parsed
        """
        ...

    @abstractmethod
    def read_all_events(self, log_path: str) -> list[PhaseEvent]:
        """Read and parse all phase events without step_id filtering.

        Args:
            log_path: Absolute path to the execution log file

        Returns:
            List of all PhaseEvent objects in the log

        Raises:
            LogFileNotFound: If the log file does not exist
            LogFileCorrupted: If the log file cannot be parsed
        """
        ...
