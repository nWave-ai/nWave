"""Acceptance tests for log integrity validation (AT-1 through AT-7).

Tests verify the DES residue (invariants that survive perturbations)
identified in the residuality analysis.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from des.application.subagent_stop_service import SubagentStopService
from des.domain.log_integrity_validator import LogIntegrityValidator
from des.domain.phase_event import PhaseEvent
from des.domain.step_completion_validator import StepCompletionValidator
from des.domain.tdd_schema import get_tdd_schema
from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter
from des.ports.driven_ports.execution_log_reader import ExecutionLogReader
from des.ports.driven_ports.scope_checker import ScopeChecker, ScopeCheckResult
from des.ports.driven_ports.time_provider_port import TimeProvider
from des.ports.driver_ports.subagent_stop_port import SubagentStopContext


if TYPE_CHECKING:
    from pathlib import Path


# --- Test doubles ---


class SpyAuditWriter(AuditLogWriter):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def log_event(self, event: AuditEvent) -> None:
        self.events.append(event)


class StubTimeProvider(TimeProvider):
    def now_utc(self) -> datetime:
        return datetime(2026, 2, 10, 15, 0, 0, tzinfo=timezone.utc)


class StubLogReader(ExecutionLogReader):
    def __init__(self, project_id: str, events: list[PhaseEvent]) -> None:
        self._project_id = project_id
        self._events = events

    def read_project_id(self, log_path: str) -> str:
        return self._project_id

    def read_step_events(self, log_path: str, step_id: str) -> list[PhaseEvent]:
        return [e for e in self._events if e.step_id == step_id]

    def read_all_events(self, log_path: str) -> list[PhaseEvent]:
        return self._events


class StubScopeChecker(ScopeChecker):
    def check_scope(
        self, project_root: Path, allowed_patterns: list[str]
    ) -> ScopeCheckResult:
        return ScopeCheckResult(has_violations=False, out_of_scope_files=[])


# --- Helpers ---


def _make_complete_events(step_id: str) -> list[PhaseEvent]:
    """Create complete 7-phase events that pass StepCompletionValidator."""
    phases = get_tdd_schema().tdd_phases
    events = []
    for phase in phases:
        outcome = "FAIL" if phase in ("RED_ACCEPTANCE", "RED_UNIT") else "PASS"
        if phase == "REFACTOR_CONTINUOUS":
            events.append(
                PhaseEvent(
                    step_id=step_id,
                    phase_name=phase,
                    status="SKIPPED",
                    outcome="APPROVED_SKIP:Clean",
                    timestamp="2026-02-08T14:05:00+00:00",
                )
            )
        else:
            events.append(
                PhaseEvent(
                    step_id=step_id,
                    phase_name=phase,
                    status="EXECUTED",
                    outcome=outcome,
                    timestamp="2026-02-08T14:05:00+00:00",
                )
            )
    return events


def _build_service(
    events: list[PhaseEvent],
    project_id: str = "test-project",
) -> tuple[SubagentStopService, SpyAuditWriter]:
    audit_spy = SpyAuditWriter()
    schema = get_tdd_schema()
    time_provider = StubTimeProvider()
    service = SubagentStopService(
        log_reader=StubLogReader(project_id=project_id, events=events),
        completion_validator=StepCompletionValidator(schema=schema),
        scope_checker=StubScopeChecker(),
        audit_writer=audit_spy,
        time_provider=time_provider,
        integrity_validator=LogIntegrityValidator(
            schema=schema, time_provider=time_provider
        ),
    )
    return service, audit_spy


def _build_empty_stdin_service() -> tuple[SubagentStopService, SpyAuditWriter]:
    """Build a SubagentStopService with no events (empty stdin equivalent)."""
    return _build_service(events=[])


class TestAT1PhaseNameValidation:
    """AT-1: Crafter writes unrecognized phase name 'REFACTOR'."""

    def test_unrecognized_phase_name_warning(self) -> None:
        events = _make_complete_events("01-01")
        # Add an event with wrong phase name
        events.append(
            PhaseEvent(
                step_id="01-01",
                phase_name="REFACTOR",
                status="EXECUTED",
                outcome="PASS",
                timestamp="2026-02-08T14:06:00+00:00",
            )
        )
        service, audit_spy = _build_service(events)
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="test-project",
            step_id="01-01",
            task_start_time="2026-02-08T14:00:00+00:00",
        )
        decision = service.validate(context)

        # Integrity warnings are warn-only: step still passes
        assert decision.action == "allow"
        integrity_warnings = [
            e for e in audit_spy.events if e.event_type == "LOG_INTEGRITY_WARNING"
        ]
        assert len(integrity_warnings) >= 1
        assert "REFACTOR" in integrity_warnings[0].data["warning"]


class TestAT2CrossStepContamination:
    """AT-2: Crafter for 01-03 writes events for both 01-03 and 01-04."""

    def test_foreign_step_id_detected(self) -> None:
        events = _make_complete_events("01-03")
        # Add contamination: events for 01-04 in the task window
        events.append(
            PhaseEvent(
                step_id="01-04",
                phase_name="PREPARE",
                status="EXECUTED",
                outcome="PASS",
                timestamp="2026-02-08T14:05:00+00:00",
            )
        )
        service, audit_spy = _build_service(events)
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="test-project",
            step_id="01-03",
            task_start_time="2026-02-08T14:00:00+00:00",
        )
        decision = service.validate(context)

        assert decision.action == "allow"
        integrity_warnings = [
            e for e in audit_spy.events if e.event_type == "LOG_INTEGRITY_WARNING"
        ]
        foreign_warnings = [
            w for w in integrity_warnings if "Foreign step_id" in w.data["warning"]
        ]
        assert len(foreign_warnings) >= 1
        assert "01-04" in foreign_warnings[0].data["warning"]


class TestAT3FutureTimestamp:
    """AT-3: Event with timestamp 24h in the future."""

    def test_future_timestamp_warning(self) -> None:
        events = _make_complete_events("01-01")
        events.append(
            PhaseEvent(
                step_id="01-01",
                phase_name="PREPARE",
                status="EXECUTED",
                outcome="PASS",
                timestamp="2099-01-01T00:00:00+00:00",
            )
        )
        service, audit_spy = _build_service(events)
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="test-project",
            step_id="01-01",
            task_start_time="2026-02-08T14:00:00+00:00",
        )
        decision = service.validate(context)

        assert decision.action == "allow"
        integrity_warnings = [
            e for e in audit_spy.events if e.event_type == "LOG_INTEGRITY_WARNING"
        ]
        future_warnings = [
            w for w in integrity_warnings if "Future timestamp" in w.data["warning"]
        ]
        assert len(future_warnings) >= 1


class TestAT4PreTaskTimestamp:
    """AT-4: Event with timestamp before task_start_time."""

    def test_pre_task_timestamp_warning(self) -> None:
        events = _make_complete_events("01-01")
        events.append(
            PhaseEvent(
                step_id="01-01",
                phase_name="PREPARE",
                status="EXECUTED",
                outcome="PASS",
                timestamp="2026-02-08T13:00:00+00:00",
            )
        )
        service, audit_spy = _build_service(events)
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="test-project",
            step_id="01-01",
            task_start_time="2026-02-08T14:00:00+00:00",
        )
        decision = service.validate(context)

        assert decision.action == "allow"
        integrity_warnings = [
            e for e in audit_spy.events if e.event_type == "LOG_INTEGRITY_WARNING"
        ]
        pre_task_warnings = [
            w for w in integrity_warnings if "Pre-task timestamp" in w.data["warning"]
        ]
        assert len(pre_task_warnings) >= 1


class TestAT5EmptyStdinPassthrough:
    """AT-5: SubagentStop with no events (empty context) → allow.

    Port-to-port equivalent: when no events exist for a step and
    stop_hook_active=True, the service allows to prevent infinite loops.
    """

    def test_empty_context_allows(self) -> None:
        service, _audit_spy = _build_empty_stdin_service()
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="test-project",
            step_id="01-01",
            stop_hook_active=True,
        )
        decision = service.validate(context)
        assert decision.action == "allow"


class TestAT6MissingTranscript:
    """AT-6: transcript_path → non-existent file → returns None, no error."""

    def test_missing_transcript_returns_none(self, tmp_path: Path) -> None:
        from des.adapters.drivers.hooks.claude_code_hook_adapter import (
            extract_des_context_from_transcript,
        )

        result = extract_des_context_from_transcript(
            str(tmp_path / "does-not-exist.jsonl")
        )
        assert result is None


class TestAT7StopHookActiveEscapeHatch:
    """AT-7: stop_hook_active=True, still 0 events → allow + audit."""

    def test_stop_hook_active_allows_with_audit(self) -> None:
        audit_spy = SpyAuditWriter()
        schema = get_tdd_schema()
        time_provider = StubTimeProvider()
        service = SubagentStopService(
            log_reader=StubLogReader(project_id="test-project", events=[]),
            completion_validator=StepCompletionValidator(schema=schema),
            scope_checker=StubScopeChecker(),
            audit_writer=audit_spy,
            time_provider=time_provider,
            integrity_validator=LogIntegrityValidator(
                schema=schema, time_provider=time_provider
            ),
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="test-project",
            step_id="01-01",
            stop_hook_active=True,
        )
        decision = service.validate(context)

        assert decision.action == "allow"
        failed_events = [
            e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_FAILED"
        ]
        assert len(failed_events) == 1
        assert failed_events[0].data.get("allowed_despite_failure") is True
