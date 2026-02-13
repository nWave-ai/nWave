"""YamlExecutionLogReader - driven adapter for reading execution log data.

Implements the ExecutionLogReader port by reading YAML execution-log files
and converting event entries into domain PhaseEvent objects.

Supports two event formats via PhaseEventParser.parse_auto():
- v2.0: pipe-delimited strings ("step_id|phase|status|data|timestamp")
- v3.0: structured YAML dicts ({sid, p, s, d, t} with optional tu, tk)

Infrastructure details (YAML format, file I/O) are hidden behind the port interface.
The application layer only sees PhaseEvent domain objects.
"""

from __future__ import annotations

import yaml

from des.domain.phase_event import PhaseEvent, PhaseEventParser
from des.ports.driven_ports.execution_log_reader import (
    ExecutionLogReader,
    LogFileCorrupted,
    LogFileNotFound,
)


class YamlExecutionLogReader(ExecutionLogReader):
    """Reads execution log data from YAML files.

    Supports both v2.0 (pipe-delimited) and v3.0 (structured dict) formats.
    Format auto-detection is per-event via PhaseEventParser.parse_auto().

    File format (Schema v2.0 - pipe-delimited strings):
        schema_version: "2.0"
        events:
          - "01-01|PREPARE|EXECUTED|PASS|2026-02-02T10:00:00Z"

    File format (Schema v3.0 - structured YAML objects):
        schema_version: "3.0"
        events:
          - {sid: "01-01", p: PREPARE, s: EXECUTED, d: PASS, t: "2026-02-02T10:00:00Z"}
    """

    def __init__(self) -> None:
        self._parser = PhaseEventParser()

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
        data = self._load_yaml(log_path)
        return data.get("project_id")

    def read_step_events(self, log_path: str, step_id: str) -> list[PhaseEvent]:
        """Read and parse phase events for a specific step.

        Translates raw YAML event entries (strings or dicts) into domain
        PhaseEvent objects using PhaseEventParser, filtered by step_id.

        Args:
            log_path: Absolute path to the execution log file
            step_id: Step identifier to filter events for

        Returns:
            List of PhaseEvent objects matching the step_id

        Raises:
            LogFileNotFound: If the log file does not exist
            LogFileCorrupted: If the log file cannot be parsed
        """
        data = self._load_yaml(log_path)
        raw_events = data.get("events", [])
        return self._parser.parse_many(raw_events, step_id)

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
        data = self._load_yaml(log_path)
        raw_events = data.get("events", [])
        return self._parser.parse_all(raw_events)

    def _load_yaml(self, log_path: str) -> dict:
        """Load and parse a YAML file.

        Args:
            log_path: Absolute path to the YAML file

        Returns:
            Parsed YAML data as a dictionary

        Raises:
            LogFileNotFound: If the file does not exist
            LogFileCorrupted: If the YAML cannot be parsed
        """
        try:
            with open(log_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise LogFileNotFound(f"Execution log not found: {log_path}")
        except yaml.YAMLError as e:
            raise LogFileCorrupted(f"Invalid YAML in execution log: {e}")

        if not isinstance(data, dict):
            raise LogFileCorrupted(
                f"Execution log must be a YAML mapping, got {type(data).__name__}"
            )

        return data
