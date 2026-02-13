"""Unit tests for SubagentStopService timestamp correction (zero-trust L2).

Tests that SubagentStopService detects fabricated timestamps via
LogIntegrityValidator and corrects them by interpolating real timestamps
between task_start_time and now().

Tested through the driving port (SubagentStopPort.validate) with real
YamlExecutionLogReader (reads from tmp_path) and real LogIntegrityValidator.
Mock driven ports only at port boundaries (AuditLogWriter, ScopeChecker,
TimeProvider).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

import yaml

from des.adapters.driven.hooks.yaml_execution_log_reader import YamlExecutionLogReader
from des.application.subagent_stop_service import SubagentStopService
from des.domain.log_integrity_validator import LogIntegrityValidator
from des.domain.step_completion_validator import StepCompletionValidator
from des.domain.tdd_schema import get_tdd_schema
from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter
from des.ports.driven_ports.scope_checker import ScopeChecker, ScopeCheckResult
from des.ports.driven_ports.time_provider_port import TimeProvider
from des.ports.driver_ports.subagent_stop_port import SubagentStopContext


# --- Test doubles (driven port implementations) ---


class SpyAuditWriter(AuditLogWriter):
    """Spy that captures all logged audit events for assertion."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def log_event(self, event: AuditEvent) -> None:
        self.events.append(event)


class StubTimeProvider(TimeProvider):
    """Stub returning a fixed timestamp for deterministic testing."""

    def __init__(self, fixed_time: datetime | None = None) -> None:
        self._fixed_time = fixed_time or datetime(
            2026, 2, 10, 22, 0, 0, tzinfo=timezone.utc
        )

    def now_utc(self) -> datetime:
        return self._fixed_time


class StubScopeChecker(ScopeChecker):
    """Stub returning no scope violations."""

    def check_scope(
        self, project_root: Path, allowed_patterns: list[str]
    ) -> ScopeCheckResult:
        return ScopeCheckResult(has_violations=False, out_of_scope_files=[])


def _parse_iso(s: str) -> datetime:
    """Parse ISO 8601 timestamp, handling 'Z' suffix for Python 3.10 compat."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# --- Helpers ---


def _make_complete_events_strings(step_id: str, timestamps: list[str]) -> list[str]:
    """Create 7 pipe-delimited event strings for a complete TDD cycle.

    Args:
        step_id: Step identifier
        timestamps: List of 7 ISO 8601 timestamps, one per phase
    """
    phases = [
        ("PREPARE", "EXECUTED", "PASS"),
        ("RED_ACCEPTANCE", "EXECUTED", "FAIL"),
        ("RED_UNIT", "EXECUTED", "FAIL"),
        ("GREEN", "EXECUTED", "PASS"),
        ("REVIEW", "EXECUTED", "PASS"),
        ("REFACTOR_CONTINUOUS", "SKIPPED", "APPROVED_SKIP:Clean"),
        ("COMMIT", "EXECUTED", "PASS"),
    ]
    return [
        f"{step_id}|{name}|{status}|{outcome}|{ts}"
        for (name, status, outcome), ts in zip(phases, timestamps, strict=False)
    ]


def _write_execution_log(
    log_path: Path,
    project_id: str,
    event_strings: list[str],
) -> None:
    """Write an execution-log.yaml file with the given event strings."""
    log_data = {
        "schema_version": "2.0",
        "project_id": project_id,
        "events": event_strings,
    }
    log_path.write_text(yaml.dump(log_data, default_flow_style=False, sort_keys=False))


def _read_execution_log_events(log_path: Path) -> list[str]:
    """Read back the raw event strings from an execution-log.yaml."""
    data = yaml.safe_load(log_path.read_text())
    return data.get("events", [])


def _build_service_with_integrity(
    audit_spy: SpyAuditWriter,
    time_provider: StubTimeProvider,
) -> SubagentStopService:
    """Build SubagentStopService with real YamlExecutionLogReader and LogIntegrityValidator."""
    schema = get_tdd_schema()
    return SubagentStopService(
        log_reader=YamlExecutionLogReader(),
        completion_validator=StepCompletionValidator(schema=schema),
        scope_checker=StubScopeChecker(),
        audit_writer=audit_spy,
        time_provider=time_provider,
        integrity_validator=LogIntegrityValidator(
            schema=schema, time_provider=time_provider
        ),
    )


# --- Test: Fabricated timestamps are corrected in log ---


class TestTimestampCorrection:
    """Tests for zero-trust timestamp correction in SubagentStopService."""

    def test_fabricated_timestamps_corrected_in_log(self, tmp_path: Path) -> None:
        """Fabricated pre-task timestamps are rewritten to interpolated values
        within the task window [task_start, now]."""
        step_id = "01-03"
        project_id = "my-feature"
        task_start = "2026-02-10T21:00:00+00:00"
        # Now is 2026-02-10T22:00:00Z (1 hour after task start)
        now_time = datetime(2026, 2, 10, 22, 0, 0, tzinfo=timezone.utc)
        time_provider = StubTimeProvider(fixed_time=now_time)

        # Fabricated timestamps: all set to BEFORE task_start (pre-task)
        # Must be more than 60s before task_start to be correctable
        fabricated_ts = [
            "2026-02-10T19:00:00+00:00",  # PREPARE - 2h before task start
            "2026-02-10T19:01:00+00:00",  # RED_ACCEPTANCE
            "2026-02-10T19:02:00+00:00",  # RED_UNIT
            "2026-02-10T19:03:00+00:00",  # GREEN
            "2026-02-10T19:04:00+00:00",  # REVIEW
            "2026-02-10T19:05:00+00:00",  # REFACTOR_CONTINUOUS
            "2026-02-10T19:06:00+00:00",  # COMMIT
        ]

        event_strings = _make_complete_events_strings(step_id, fabricated_ts)
        log_path = tmp_path / "execution-log.yaml"
        _write_execution_log(log_path, project_id, event_strings)

        audit_spy = SpyAuditWriter()
        service = _build_service_with_integrity(audit_spy, time_provider)

        context = SubagentStopContext(
            execution_log_path=str(log_path),
            project_id=project_id,
            step_id=step_id,
            task_start_time=task_start,
        )

        service.validate(context)

        # Read back the corrected YAML
        corrected_events = _read_execution_log_events(log_path)

        # All 7 timestamps should have been corrected (no longer fabricated)
        task_start_dt = datetime.fromisoformat(task_start)
        for event_str in corrected_events:
            parts = event_str.split("|")
            ts_str = parts[4]
            ts_dt = _parse_iso(ts_str)
            # Each corrected timestamp must be between task_start and now
            assert ts_dt >= task_start_dt, (
                f"Corrected timestamp {ts_str} is before task_start {task_start}"
            )
            assert ts_dt <= now_time, (
                f"Corrected timestamp {ts_str} is after now {now_time}"
            )

        # Verify none of the original fabricated timestamps remain
        for orig_ts in fabricated_ts:
            for event_str in corrected_events:
                assert orig_ts not in event_str, (
                    f"Original fabricated timestamp {orig_ts} still present in: {event_str}"
                )

    def test_correction_logged_as_audit_event(self, tmp_path: Path) -> None:
        """Corrected timestamps produce LOG_INTEGRITY_CORRECTED audit events,
        not LOG_INTEGRITY_WARNING."""
        step_id = "01-03"
        project_id = "my-feature"
        task_start = "2026-02-10T21:00:00+00:00"
        now_time = datetime(2026, 2, 10, 22, 0, 0, tzinfo=timezone.utc)
        time_provider = StubTimeProvider(fixed_time=now_time)

        # Single fabricated pre-task timestamp
        timestamps = [
            "2026-02-10T19:00:00+00:00",  # PREPARE - fabricated (2h before)
            "2026-02-10T21:01:00+00:00",  # RED_ACCEPTANCE - valid
            "2026-02-10T21:02:00+00:00",  # RED_UNIT - valid
            "2026-02-10T21:03:00+00:00",  # GREEN - valid
            "2026-02-10T21:04:00+00:00",  # REVIEW - valid
            "2026-02-10T21:05:00+00:00",  # REFACTOR_CONTINUOUS - valid
            "2026-02-10T21:06:00+00:00",  # COMMIT - valid
        ]

        event_strings = _make_complete_events_strings(step_id, timestamps)
        log_path = tmp_path / "execution-log.yaml"
        _write_execution_log(log_path, project_id, event_strings)

        audit_spy = SpyAuditWriter()
        service = _build_service_with_integrity(audit_spy, time_provider)

        context = SubagentStopContext(
            execution_log_path=str(log_path),
            project_id=project_id,
            step_id=step_id,
            task_start_time=task_start,
        )

        service.validate(context)

        # Should have LOG_INTEGRITY_CORRECTED events
        corrected_events = [
            e for e in audit_spy.events if e.event_type == "LOG_INTEGRITY_CORRECTED"
        ]
        assert len(corrected_events) >= 1
        assert corrected_events[0].data["phase"] == "PREPARE"
        assert (
            corrected_events[0].data["original_timestamp"]
            == "2026-02-10T19:00:00+00:00"
        )
        assert "corrected_timestamp" in corrected_events[0].data

        # Should NOT have LOG_INTEGRITY_WARNING for the corrected entry
        warning_events = [
            e for e in audit_spy.events if e.event_type == "LOG_INTEGRITY_WARNING"
        ]
        for w in warning_events:
            assert "2026-02-10T19:00:00+00:00" not in w.data.get("warning", ""), (
                "Corrected entry should not also appear as LOG_INTEGRITY_WARNING"
            )

    def test_correct_timestamps_not_modified(self, tmp_path: Path) -> None:
        """Events with valid timestamps (within task window) are not modified."""
        step_id = "01-03"
        project_id = "my-feature"
        task_start = "2026-02-10T21:00:00+00:00"
        now_time = datetime(2026, 2, 10, 22, 0, 0, tzinfo=timezone.utc)
        time_provider = StubTimeProvider(fixed_time=now_time)

        # All timestamps valid (within task window)
        valid_ts = [
            "2026-02-10T21:10:00Z",
            "2026-02-10T21:15:00Z",
            "2026-02-10T21:20:00Z",
            "2026-02-10T21:25:00Z",
            "2026-02-10T21:30:00Z",
            "2026-02-10T21:35:00Z",
            "2026-02-10T21:40:00Z",
        ]

        event_strings = _make_complete_events_strings(step_id, valid_ts)
        log_path = tmp_path / "execution-log.yaml"
        _write_execution_log(log_path, project_id, event_strings)

        # Capture original content
        original_events = _read_execution_log_events(log_path)

        audit_spy = SpyAuditWriter()
        service = _build_service_with_integrity(audit_spy, time_provider)

        context = SubagentStopContext(
            execution_log_path=str(log_path),
            project_id=project_id,
            step_id=step_id,
            task_start_time=task_start,
        )

        service.validate(context)

        # Events should be unchanged
        after_events = _read_execution_log_events(log_path)
        assert after_events == original_events

        # No CORRECTED audit events
        corrected_events = [
            e for e in audit_spy.events if e.event_type == "LOG_INTEGRITY_CORRECTED"
        ]
        assert len(corrected_events) == 0

    def test_correction_runs_before_stop_hook_active_check(
        self, tmp_path: Path
    ) -> None:
        """Timestamp correction runs even when stop_hook_active=True (retry).

        When completion fails AND timestamps are fabricated, correction STILL
        happens because it runs before the stop_hook_active bypass check.
        """
        step_id = "01-03"
        project_id = "my-feature"
        task_start = "2026-02-10T21:00:00+00:00"
        now_time = datetime(2026, 2, 10, 22, 0, 0, tzinfo=timezone.utc)
        time_provider = StubTimeProvider(fixed_time=now_time)

        # Incomplete events (only 2 phases) with fabricated timestamps
        fabricated_ts = "2026-02-10T19:00:00+00:00"  # 2h before task start
        event_strings = [
            f"{step_id}|PREPARE|EXECUTED|PASS|{fabricated_ts}",
            f"{step_id}|RED_ACCEPTANCE|EXECUTED|FAIL|{fabricated_ts}",
        ]

        log_path = tmp_path / "execution-log.yaml"
        _write_execution_log(log_path, project_id, event_strings)

        audit_spy = SpyAuditWriter()
        service = _build_service_with_integrity(audit_spy, time_provider)

        context = SubagentStopContext(
            execution_log_path=str(log_path),
            project_id=project_id,
            step_id=step_id,
            stop_hook_active=True,  # Retry scenario
            task_start_time=task_start,
        )

        # Validation will fail (incomplete phases) but allow (retry)
        decision = service.validate(context)
        assert decision.action == "allow"  # Allowed on retry

        # Despite being a retry, timestamps should STILL be corrected
        corrected_events = [
            e for e in audit_spy.events if e.event_type == "LOG_INTEGRITY_CORRECTED"
        ]
        assert len(corrected_events) >= 1, (
            "Timestamp correction must run before stop_hook_active bypass"
        )

        # Verify the YAML file was actually corrected
        after_events = _read_execution_log_events(log_path)
        for event_str in after_events:
            assert fabricated_ts not in event_str, (
                f"Fabricated timestamp still present after correction: {event_str}"
            )
