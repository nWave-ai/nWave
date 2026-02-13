"""Phase event domain model and parser.

Pure domain types for representing TDD phase execution events
parsed from execution-log.yaml in two formats:

v2.0 pipe-delimited strings:
  Format (5-field legacy): "step_id|phase_name|status|outcome|timestamp"
  Format (7-field with stats): "step_id|phase_name|status|outcome|timestamp|turns_used|tokens_used"
  Example: "01-01|PREPARE|EXECUTED|PASS|2026-02-02T10:00:00Z"
  Example: "01-01|COMMIT|EXECUTED|PASS|2026-02-02T10:30:00Z|12|45000"

v3.0 structured YAML dicts:
  Format: {sid: step_id, p: phase, s: status, d: data, t: timestamp}
  Optional: {tu: turns_used, tk: tokens_used}
  Example: {sid: "01-01", p: "PREPARE", s: "EXECUTED", d: "PASS", t: "2026-02-02T10:00:00Z"}
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseEvent:
    """Immutable representation of a single TDD phase execution event.

    Attributes:
        step_id: Step identifier (e.g., "01-01")
        phase_name: TDD phase name (e.g., "PREPARE", "RED_ACCEPTANCE")
        status: Execution status (e.g., "EXECUTED", "SKIPPED")
        outcome: Outcome data (e.g., "PASS", "FAIL", or skip reason)
        timestamp: ISO 8601 timestamp string
        turns_used: Optional number of turns consumed (for COMMIT phase stats)
        tokens_used: Optional number of tokens consumed (for COMMIT phase stats)
    """

    step_id: str
    phase_name: str
    status: str
    outcome: str
    timestamp: str
    turns_used: int | None = None
    tokens_used: int | None = None


class PhaseEventParser:
    """Parses event entries into PhaseEvent domain objects.

    Supports two formats:
    - v2.0: pipe-delimited strings ("step_id|phase|status|data|timestamp")
    - v3.0: structured dicts ({sid, p, s, d, t} with optional tu, tk)

    This is a stateless parser with no I/O dependencies.
    """

    MINIMUM_FIELDS = 5
    STATS_FIELDS = 7
    FIELD_SEPARATOR = "|"

    # Required keys for v3.0 structured format
    STRUCTURED_REQUIRED_KEYS = frozenset({"sid", "p", "s", "d", "t"})

    def parse(self, event_str: str) -> PhaseEvent | None:
        """Parse a pipe-delimited event string into a PhaseEvent.

        Args:
            event_str: Raw event string in format
                "step_id|phase_name|status|outcome|timestamp" (5-field legacy)
                or "step_id|phase_name|status|outcome|timestamp|turns|tokens" (7-field)

        Returns:
            PhaseEvent if the string has enough fields, None otherwise.
        """
        parts = event_str.split(self.FIELD_SEPARATOR)
        if len(parts) < self.MINIMUM_FIELDS:
            return None

        turns_used = None
        tokens_used = None
        if len(parts) >= self.STATS_FIELDS:
            try:
                turns_used = int(parts[5])
                tokens_used = int(parts[6])
            except ValueError:
                pass  # Non-integer extra fields: ignore gracefully

        return PhaseEvent(
            step_id=parts[0],
            phase_name=parts[1],
            status=parts[2],
            outcome=parts[3],
            timestamp=parts[4],
            turns_used=turns_used,
            tokens_used=tokens_used,
        )

    def parse_structured(self, event_dict: dict) -> PhaseEvent | None:
        """Parse a structured dict (v3.0 format) into a PhaseEvent.

        Args:
            event_dict: Dict with short keys {sid, p, s, d, t} and
                optional {tu, tk} for execution stats.

        Returns:
            PhaseEvent if all required keys are present, None otherwise.
        """
        if not self.STRUCTURED_REQUIRED_KEYS.issubset(event_dict.keys()):
            return None

        turns_used = event_dict.get("tu")
        tokens_used = event_dict.get("tk")

        return PhaseEvent(
            step_id=event_dict["sid"],
            phase_name=event_dict["p"],
            status=event_dict["s"],
            outcome=event_dict["d"],
            timestamp=event_dict["t"],
            turns_used=turns_used,
            tokens_used=tokens_used,
        )

    def parse_auto(self, event: str | dict) -> PhaseEvent | None:
        """Auto-detect event format and parse accordingly.

        Routes string events to parse() (v2.0 pipe format) and
        dict events to parse_structured() (v3.0 structured format).

        Args:
            event: Either a pipe-delimited string or a structured dict.

        Returns:
            PhaseEvent if parsing succeeds, None otherwise.
        """
        if isinstance(event, str):
            return self.parse(event)
        if isinstance(event, dict):
            return self.parse_structured(event)
        return None

    def parse_many(self, event_entries: list, step_id: str) -> list[PhaseEvent]:
        """Parse multiple events, filtering by step_id.

        Supports both pipe-delimited strings and structured dicts via auto-detection.

        Args:
            event_entries: List of raw event entries (strings or dicts)
            step_id: Only return events matching this step_id

        Returns:
            List of PhaseEvent objects matching the step_id
        """
        events = []
        for entry in event_entries:
            event = self.parse_auto(entry)
            if event is not None and event.step_id == step_id:
                events.append(event)
        return events

    def parse_all(self, event_entries: list) -> list[PhaseEvent]:
        """Parse all events without filtering by step_id.

        Supports both pipe-delimited strings and structured dicts via auto-detection.

        Args:
            event_entries: List of raw event entries (strings or dicts)

        Returns:
            List of all successfully parsed PhaseEvent objects
        """
        events = []
        for entry in event_entries:
            event = self.parse_auto(entry)
            if event is not None:
                events.append(event)
        return events
