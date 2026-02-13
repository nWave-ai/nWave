"""Log integrity validator - detects crafter log manipulation.

Checks execution-log events for anomalies that indicate fabrication,
cross-step contamination, or timestamp manipulation. Warn-only: does
not block step completion.

Three checks:
1. Phase names: events with phase_name not in TDDSchema.tdd_phases
2. Foreign step_ids: events for OTHER step_ids within the task window
3. Timestamp plausibility: future timestamps or pre-task-start timestamps
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from difflib import get_close_matches
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from des.domain.phase_event import PhaseEvent
    from des.domain.tdd_schema import TDDSchema
    from des.ports.driven_ports.time_provider_port import TimeProvider


_TOLERANCE = timedelta(seconds=60)


@dataclass(frozen=True)
class CorrectableEntry:
    """An entry with a fabricated timestamp that can be corrected."""

    index: int  # Position in the all_events list
    step_id: str
    phase_name: str
    original_timestamp: str
    reason: str  # "pre_task" or "future"


@dataclass(frozen=True)
class IntegrityResult:
    """Result of log integrity validation. Warnings only, never blocks."""

    warnings: list[str] = field(default_factory=list)
    correctable_entries: list[CorrectableEntry] = field(default_factory=list)


class LogIntegrityValidator:
    """Validates execution-log events for integrity anomalies.

    Warn-only: produces warnings that are logged to the audit trail
    but never block step completion.
    """

    def __init__(
        self, schema: TDDSchema, time_provider: TimeProvider | None = None
    ) -> None:
        self._valid_phases = set(schema.tdd_phases)
        self._time_provider = time_provider

    def validate(
        self,
        step_id: str,
        all_events: list[PhaseEvent],
        task_start_time: str | None = None,
    ) -> IntegrityResult:
        """Validate events for integrity anomalies.

        Args:
            step_id: The current step being validated
            all_events: ALL events from the execution log (unfiltered)
            task_start_time: ISO 8601 timestamp when the task started (optional)

        Returns:
            IntegrityResult with any warnings found
        """
        warnings: list[str] = []
        warnings.extend(self._check_phase_names(step_id, all_events))
        warnings.extend(
            self._check_foreign_step_ids(step_id, all_events, task_start_time)
        )
        ts_warnings, correctable = self._check_timestamps(
            step_id, all_events, task_start_time
        )
        warnings.extend(ts_warnings)
        return IntegrityResult(warnings=warnings, correctable_entries=correctable)

    def _check_phase_names(
        self, step_id: str, all_events: list[PhaseEvent]
    ) -> list[str]:
        """Check for unrecognized phase names in events for this step."""
        warnings: list[str] = []
        for event in all_events:
            if event.step_id != step_id:
                continue
            if event.phase_name not in self._valid_phases:
                suggestion = ""
                matches = get_close_matches(
                    event.phase_name, list(self._valid_phases), n=1, cutoff=0.5
                )
                if matches:
                    suggestion = f" (did you mean '{matches[0]}'?)"
                warnings.append(
                    f"Unrecognized phase name '{event.phase_name}'{suggestion}"
                )
        return warnings

    def _check_foreign_step_ids(
        self,
        step_id: str,
        all_events: list[PhaseEvent],
        task_start_time: str | None,
    ) -> list[str]:
        """Check for events written for other step_ids during task window."""
        if not task_start_time:
            return []

        try:
            start_dt = datetime.fromisoformat(task_start_time)
        except (ValueError, TypeError):
            return []

        warnings: list[str] = []
        foreign_ids: set[str] = set()
        for event in all_events:
            if event.step_id == step_id:
                continue
            try:
                event_dt = datetime.fromisoformat(event.timestamp)
            except (ValueError, TypeError):
                continue
            if event_dt >= start_dt:
                foreign_ids.add(event.step_id)

        for fid in sorted(foreign_ids):
            warnings.append(
                f"Foreign step_id '{fid}' has events written during task window"
            )
        return warnings

    def _check_timestamps(
        self,
        step_id: str,
        all_events: list[PhaseEvent],
        task_start_time: str | None,
    ) -> tuple[list[str], list[CorrectableEntry]]:
        """Check for implausible timestamps in events for this step.

        Future-timestamp detection always runs (needs only now()).
        Pre-task detection runs only when task_start_time is available.
        Timestamps within 60s before task_start_time are warned but not
        considered correctable (clock-skew tolerance).
        """
        if self._time_provider:
            now = self._time_provider.now_utc()
        else:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        start_dt = None
        if task_start_time:
            try:
                start_dt = datetime.fromisoformat(task_start_time)
            except (ValueError, TypeError):
                pass

        warnings: list[str] = []
        correctable: list[CorrectableEntry] = []
        for idx, event in enumerate(all_events):
            if event.step_id != step_id:
                continue
            try:
                event_dt = datetime.fromisoformat(event.timestamp)
            except (ValueError, TypeError):
                continue
            if event_dt > now:
                warnings.append(
                    f"Future timestamp on {event.phase_name}: {event.timestamp}"
                )
                correctable.append(
                    CorrectableEntry(
                        index=idx,
                        step_id=event.step_id,
                        phase_name=event.phase_name,
                        original_timestamp=event.timestamp,
                        reason="future",
                    )
                )
            elif start_dt and event_dt < (start_dt - _TOLERANCE):
                warnings.append(
                    f"Pre-task timestamp on {event.phase_name}: {event.timestamp}"
                )
                correctable.append(
                    CorrectableEntry(
                        index=idx,
                        step_id=event.step_id,
                        phase_name=event.phase_name,
                        original_timestamp=event.timestamp,
                        reason="pre_task",
                    )
                )
            elif start_dt and event_dt < start_dt:
                # Within tolerance - warn but not correctable
                warnings.append(
                    f"Pre-task timestamp on {event.phase_name}: {event.timestamp}"
                )
        return warnings, correctable
