"""Acceptance tests for log integrity validation (AT-1 through AT-7).

Tests verify the DES residue (invariants that survive perturbations)
identified in the residuality analysis.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

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
    """Create complete events that pass StepCompletionValidator.

    F6 sweep (2026-05-18): RED-family predicate updated to include the
    canonical "RED" phase (ADR-025) alongside legacy "RED_ACCEPTANCE" /
    "RED_UNIT". Iterates whatever the default ``tdd_phases`` returns —
    canonical 3-phase post-flip, legacy 5-phase pre-flip.
    """
    phases = get_tdd_schema().tdd_phases
    events = []
    for phase in phases:
        outcome = "FAIL" if phase in ("RED", "RED_ACCEPTANCE", "RED_UNIT") else "PASS"
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


class TestAT1ThroughAT4IntegrityAnomalies:
    """AT-1 through AT-4: Anomalous events produce integrity warnings (warn-only).

    Each scenario appends one anomalous event to a complete step log and
    verifies that the service allows execution while emitting the expected
    integrity warning.
    """

    @pytest.mark.parametrize(
        ("target_step_id", "anomalous_event", "warning_keyword", "extra_keyword"),
        [
            pytest.param(
                "01-01",
                PhaseEvent(
                    step_id="01-01",
                    phase_name="REFACTOR",
                    status="EXECUTED",
                    outcome="PASS",
                    timestamp="2026-02-08T14:06:00+00:00",
                ),
                "REFACTOR",
                None,
                id="unrecognized_phase",
            ),
            pytest.param(
                "01-03",
                PhaseEvent(
                    step_id="01-04",
                    phase_name="PREPARE",
                    status="EXECUTED",
                    outcome="PASS",
                    timestamp="2026-02-08T14:05:00+00:00",
                ),
                "Foreign step_id",
                "01-04",
                id="foreign_step_id",
            ),
            pytest.param(
                "01-01",
                PhaseEvent(
                    step_id="01-01",
                    phase_name="PREPARE",
                    status="EXECUTED",
                    outcome="PASS",
                    timestamp="2099-01-01T00:00:00+00:00",
                ),
                "Future timestamp",
                None,
                id="future_timestamp",
            ),
            pytest.param(
                "01-01",
                PhaseEvent(
                    step_id="01-01",
                    phase_name="PREPARE",
                    status="EXECUTED",
                    outcome="PASS",
                    timestamp="2026-02-08T13:00:00+00:00",
                ),
                "Pre-task timestamp",
                None,
                id="pre_task_timestamp",
            ),
        ],
    )
    def test_anomalous_event_produces_integrity_warning(
        self,
        target_step_id: str,
        anomalous_event: PhaseEvent,
        warning_keyword: str,
        extra_keyword: str | None,
    ) -> None:
        events = _make_complete_events(target_step_id)
        events.append(anomalous_event)

        service, audit_spy = _build_service(events)
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.json",
            project_id="test-project",
            step_id=target_step_id,
            task_start_time="2026-02-08T14:00:00+00:00",
        )
        decision = service.validate(context)

        # Integrity warnings are warn-only: step still passes
        assert decision.action == "allow"
        integrity_warnings = [
            e for e in audit_spy.events if e.event_type == "LOG_INTEGRITY_WARNING"
        ]
        matched_warnings = [
            w for w in integrity_warnings if warning_keyword in w.data["warning"]
        ]
        assert len(matched_warnings) >= 1
        if extra_keyword is not None:
            assert extra_keyword in matched_warnings[0].data["warning"]


class TestAT5EmptyStdinPassthrough:
    """AT-5: SubagentStop with no events (empty context) → allow.

    Port-to-port equivalent: when no events exist for a step and
    stop_hook_active=True, the service allows to prevent infinite loops.
    """

    def test_empty_context_allows(self) -> None:
        service, _audit_spy = _build_empty_stdin_service()
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.json",
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
            execution_log_path="/fake/execution-log.json",
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
