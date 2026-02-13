"""
StructuredLogger adapter - production logging implementation.

Provides structured JSON logging for validation results, hook executions,
and errors in the DES system.
"""

import json
import sys
from datetime import datetime
from typing import Any, TextIO

from des.ports.driven_ports.logging_port import LoggingPort


class StructuredLogger(LoggingPort):
    """
    Production logging adapter that outputs structured JSON logs.

    Logs are written to the configured output stream (default: stdout)
    in JSON format for easy parsing and analysis.
    """

    def __init__(self, output_stream: TextIO | None = None):
        """
        Initialize the structured logger.

        Args:
            output_stream: Stream to write logs to (default: sys.stdout)
        """
        self.output_stream = output_stream or sys.stdout

    def log_validation_result(self, result: Any, context: dict[str, Any]) -> None:
        """
        Log a validation result as structured JSON.

        Args:
            result: The validation result object
            context: Additional context (step_file, turn, etc.)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "validation_result",
            "is_valid": getattr(result, "is_valid", None),
            "errors": getattr(result, "errors", []),
            "context": context,
        }
        self._write_log(log_entry)

    def log_hook_execution(self, result: Any, step_file: str) -> None:
        """
        Log a hook execution as structured JSON.

        Args:
            result: The hook execution result
            step_file: Path to the step file
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "hook_execution",
            "success": getattr(result, "success", None),
            "message": getattr(result, "message", ""),
            "step_file": step_file,
        }
        self._write_log(log_entry)

    def log_error(self, error: Exception, context: dict[str, Any]) -> None:
        """
        Log an error as structured JSON.

        Args:
            error: The exception that occurred
            context: Additional context about the error
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
        }
        self._write_log(log_entry)

    def _write_log(self, log_entry: dict[str, Any]) -> None:
        """
        Write a log entry as JSON to the output stream.

        Args:
            log_entry: The log entry to write
        """
        json_log = json.dumps(log_entry)
        self.output_stream.write(json_log + "\n")
        self.output_stream.flush()
