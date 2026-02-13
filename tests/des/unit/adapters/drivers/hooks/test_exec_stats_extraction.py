"""Tests for execution stats extraction and propagation through audit events.

Stats (turns_used, tokens_used) are extracted from hook_input in handle_subagent_stop()
and propagated through SubagentStopContext to audit events emitted by SubagentStopService.

Test Budget: 6 behaviors x 2 = 12 max unit tests. Using 7 tests.

Behaviors covered:
1. handle_subagent_stop extracts num_turns/total_tokens from hook_input into SubagentStopContext
2. HOOK_SUBAGENT_STOP_PASSED includes turns_used/tokens_used when provided
3. HOOK_SUBAGENT_STOP_FAILED includes turns_used/tokens_used when provided
4. COMMIT_VERIFIED includes turns_used/tokens_used when provided
5. HOOK_COMPLETED for subagent_stop includes turns_used/tokens_used when available
6. Missing stats in hook_input gracefully default to None (no breakage)
"""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import patch


if TYPE_CHECKING:
    from pathlib import Path

from des.application.subagent_stop_service import SubagentStopService
from des.domain.phase_event import PhaseEvent
from des.domain.step_completion_validator import StepCompletionValidator
from des.domain.tdd_schema import get_tdd_schema
from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter
from des.ports.driven_ports.execution_log_reader import ExecutionLogReader
from des.ports.driven_ports.scope_checker import ScopeChecker, ScopeCheckResult
from des.ports.driven_ports.time_provider_port import TimeProvider
from des.ports.driver_ports.subagent_stop_port import SubagentStopContext


# --- Test doubles ---


class SpyAuditWriter(AuditLogWriter):
    """Spy that captures all logged audit events."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def log_event(self, event: AuditEvent) -> None:
        self.events.append(event)


class StubTimeProvider(TimeProvider):
    def now_utc(self) -> datetime:
        return datetime(2026, 2, 11, 12, 0, 0, tzinfo=timezone.utc)


class StubExecutionLogReader(ExecutionLogReader):
    def __init__(self, project_id: str, events: list[PhaseEvent]) -> None:
        self._project_id = project_id
        self._events = events

    def read_project_id(self, log_path: str) -> str:
        return self._project_id

    def read_step_events(self, log_path: str, step_id: str) -> list[PhaseEvent]:
        return self._events

    def read_all_events(self, log_path: str) -> list[PhaseEvent]:
        return self._events


class StubScopeChecker(ScopeChecker):
    def check_scope(
        self, project_root: Path, allowed_patterns: list[str]
    ) -> ScopeCheckResult:
        return ScopeCheckResult(has_violations=False, out_of_scope_files=[])


# --- Helpers ---


def _make_complete_events(step_id: str) -> list[PhaseEvent]:
    """Complete 5-phase TDD events that pass validation."""
    return [
        PhaseEvent(
            step_id=step_id,
            phase_name="PREPARE",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-11T10:00:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="RED_ACCEPTANCE",
            status="EXECUTED",
            outcome="FAIL",
            timestamp="2026-02-11T10:01:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="RED_UNIT",
            status="EXECUTED",
            outcome="FAIL",
            timestamp="2026-02-11T10:02:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="GREEN",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-11T10:03:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="COMMIT",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-11T10:04:00Z",
        ),
    ]


def _make_incomplete_events(step_id: str) -> list[PhaseEvent]:
    """Incomplete events (missing COMMIT) that fail validation."""
    return [
        PhaseEvent(
            step_id=step_id,
            phase_name="PREPARE",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-11T10:00:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="RED_ACCEPTANCE",
            status="EXECUTED",
            outcome="FAIL",
            timestamp="2026-02-11T10:01:00Z",
        ),
    ]


def _build_service(
    project_id: str,
    events: list[PhaseEvent],
    commit_verifier=None,
) -> tuple[SubagentStopService, SpyAuditWriter]:
    """Build SubagentStopService with test doubles."""
    audit_spy = SpyAuditWriter()
    service = SubagentStopService(
        log_reader=StubExecutionLogReader(project_id=project_id, events=events),
        completion_validator=StepCompletionValidator(schema=get_tdd_schema()),
        scope_checker=StubScopeChecker(),
        audit_writer=audit_spy,
        time_provider=StubTimeProvider(),
        commit_verifier=commit_verifier,
    )
    return service, audit_spy


def _make_capturing_writer(events: list[AuditEvent]):
    """Create an AuditLogWriter that captures events."""
    from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter

    class CapturingWriter(NullAuditLogWriter):
        def log_event(self, event: AuditEvent) -> None:
            events.append(event)

    return CapturingWriter()


# --- Test 1: SubagentStopContext carries optional turns_used and tokens_used ---


def test_subagent_stop_context_defaults_stats_to_none():
    """SubagentStopContext defaults turns_used and tokens_used to None when not provided."""
    context = SubagentStopContext(
        execution_log_path="/fake/log.yaml",
        project_id="test",
        step_id="01-01",
    )
    assert context.turns_used is None
    assert context.tokens_used is None


def test_subagent_stop_context_carries_stats_when_provided():
    """SubagentStopContext carries turns_used and tokens_used when explicitly provided."""
    context = SubagentStopContext(
        execution_log_path="/fake/log.yaml",
        project_id="test",
        step_id="01-01",
        turns_used=25,
        tokens_used=150000,
    )
    assert context.turns_used == 25
    assert context.tokens_used == 150000


# --- Test 2: HOOK_SUBAGENT_STOP_PASSED includes stats when provided ---


def test_passed_event_includes_stats_when_provided():
    """HOOK_SUBAGENT_STOP_PASSED audit event includes turns_used and tokens_used in data."""
    service, audit_spy = _build_service(
        project_id="my-project",
        events=_make_complete_events("01-01"),
    )
    context = SubagentStopContext(
        execution_log_path="/fake/log.yaml",
        project_id="my-project",
        step_id="01-01",
        turns_used=20,
        tokens_used=100000,
    )

    service.validate(context)

    passed = [
        e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_PASSED"
    ]
    assert len(passed) == 1
    assert passed[0].data["turns_used"] == 20
    assert passed[0].data["tokens_used"] == 100000


# --- Test 3: HOOK_SUBAGENT_STOP_FAILED includes stats when provided ---


def test_failed_event_includes_stats_when_provided():
    """HOOK_SUBAGENT_STOP_FAILED audit event includes turns_used and tokens_used in data."""
    service, audit_spy = _build_service(
        project_id="my-project",
        events=_make_incomplete_events("01-01"),
    )
    context = SubagentStopContext(
        execution_log_path="/fake/log.yaml",
        project_id="my-project",
        step_id="01-01",
        turns_used=15,
        tokens_used=80000,
    )

    service.validate(context)

    failed = [
        e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_FAILED"
    ]
    assert len(failed) == 1
    assert failed[0].data["turns_used"] == 15
    assert failed[0].data["tokens_used"] == 80000


# --- Test 4: COMMIT_VERIFIED includes stats when provided ---


def test_commit_verified_event_includes_stats_when_provided():
    """COMMIT_VERIFIED audit event includes turns_used and tokens_used in data."""
    from des.ports.driven_ports.commit_verifier import (
        CommitVerificationResult,
        CommitVerifier,
    )

    class StubCommitVerifier(CommitVerifier):
        def verify_commit(self, step_id: str, cwd: str) -> CommitVerificationResult:
            return CommitVerificationResult(
                verified=True,
                commit_hash="abc123",
                commit_date="2026-02-11T10:05:00Z",
                commit_subject="feat: test commit",
            )

    service, audit_spy = _build_service(
        project_id="my-project",
        events=_make_complete_events("01-01"),
        commit_verifier=StubCommitVerifier(),
    )
    context = SubagentStopContext(
        execution_log_path="/fake/log.yaml",
        project_id="my-project",
        step_id="01-01",
        cwd="/tmp/repo",
        turns_used=30,
        tokens_used=200000,
    )

    service.validate(context)

    verified = [e for e in audit_spy.events if e.event_type == "COMMIT_VERIFIED"]
    assert len(verified) == 1
    assert verified[0].data["turns_used"] == 30
    assert verified[0].data["tokens_used"] == 200000


# --- Test 5: handle_subagent_stop extracts stats from hook_input ---


def test_handle_subagent_stop_extracts_stats_from_hook_input(monkeypatch, tmp_path):
    """handle_subagent_stop extracts num_turns and total_tokens from hook_input into HOOK_COMPLETED."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events: list[AuditEvent] = []
    writer = _make_capturing_writer(events)

    # Non-DES agent (passthrough) with stats in hook_input
    stop_stdin = json.dumps(
        {
            "session_id": "s1",
            "hook_event_name": "SubagentStop",
            "agent_id": "a1",
            "agent_type": "code",
            "cwd": str(tmp_path),
            "num_turns": 25,
            "total_tokens": 150000,
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(stop_stdin))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        adapter.handle_subagent_stop()

    completed = [e for e in events if e.event_type == "HOOK_COMPLETED"]
    assert len(completed) == 1
    assert completed[0].data["turns_used"] == 25
    assert completed[0].data["tokens_used"] == 150000


# --- Test 6: Missing stats gracefully default to None ---


def test_handle_subagent_stop_graceful_when_stats_missing(monkeypatch, tmp_path):
    """handle_subagent_stop does not break when hook_input lacks num_turns and total_tokens."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events: list[AuditEvent] = []
    writer = _make_capturing_writer(events)

    # No stats fields in hook_input
    stop_stdin = json.dumps(
        {
            "session_id": "s1",
            "hook_event_name": "SubagentStop",
            "agent_id": "a1",
            "agent_type": "code",
            "cwd": str(tmp_path),
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(stop_stdin))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        exit_code = adapter.handle_subagent_stop()

    assert exit_code == 0
    completed = [e for e in events if e.event_type == "HOOK_COMPLETED"]
    assert len(completed) == 1
    # Stats should not be in the data when not provided
    assert "turns_used" not in completed[0].data
    assert "tokens_used" not in completed[0].data


# --- Test 7: Stats absent from PASSED event when not provided ---


def test_passed_event_omits_stats_when_not_provided():
    """HOOK_SUBAGENT_STOP_PASSED omits turns_used and tokens_used from data when None."""
    service, audit_spy = _build_service(
        project_id="my-project",
        events=_make_complete_events("01-01"),
    )
    context = SubagentStopContext(
        execution_log_path="/fake/log.yaml",
        project_id="my-project",
        step_id="01-01",
        # No turns_used or tokens_used
    )

    service.validate(context)

    passed = [
        e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_PASSED"
    ]
    assert len(passed) == 1
    assert "turns_used" not in passed[0].data
    assert "tokens_used" not in passed[0].data
