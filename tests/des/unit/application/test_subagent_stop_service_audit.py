"""Unit tests for SubagentStopService audit logging - step 02-01.

Tests that SubagentStopService passes feature_name and step_id as DIRECT
AuditEvent fields (not in the data dict) for all audit event types:
PASSED, FAILED, and SCOPE_VIOLATION.

Tested through the driving port (SubagentStopPort.validate) with mock
driven ports (AuditLogWriter, ExecutionLogReader, ScopeChecker, TimeProvider).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

from des.application.subagent_stop_service import SubagentStopService
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


# --- Test doubles (driven port implementations) ---


class SpyAuditWriter(AuditLogWriter):
    """Spy that captures all logged audit events for assertion."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def log_event(self, event: AuditEvent) -> None:
        self.events.append(event)


class StubTimeProvider(TimeProvider):
    """Stub returning a fixed timestamp."""

    def now_utc(self) -> datetime:
        return datetime(2026, 2, 6, 21, 0, 0, tzinfo=timezone.utc)


class StubExecutionLogReader(ExecutionLogReader):
    """Stub returning pre-configured project_id and PhaseEvent lists."""

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
    """Stub returning pre-configured scope check results."""

    def __init__(self, violations: list[str] | None = None) -> None:
        self._violations = violations or []

    def check_scope(
        self, project_root: Path, allowed_patterns: list[str]
    ) -> ScopeCheckResult:
        return ScopeCheckResult(
            has_violations=len(self._violations) > 0,
            out_of_scope_files=self._violations,
        )


# --- Helpers ---


def _make_complete_phase_events(step_id: str) -> list[PhaseEvent]:
    """Create a complete set of 7 TDD phase events that passes validation."""
    return [
        PhaseEvent(
            step_id=step_id,
            phase_name="PREPARE",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-06T21:00:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="RED_ACCEPTANCE",
            status="EXECUTED",
            outcome="FAIL",
            timestamp="2026-02-06T21:01:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="RED_UNIT",
            status="EXECUTED",
            outcome="FAIL",
            timestamp="2026-02-06T21:02:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="GREEN",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-06T21:03:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="COMMIT",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-06T21:04:00Z",
        ),
    ]


def _make_incomplete_phase_events(step_id: str) -> list[PhaseEvent]:
    """Create an incomplete set of events (missing COMMIT) that fails validation."""
    return [
        PhaseEvent(
            step_id=step_id,
            phase_name="PREPARE",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-06T21:00:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="RED_ACCEPTANCE",
            status="EXECUTED",
            outcome="FAIL",
            timestamp="2026-02-06T21:01:00Z",
        ),
    ]


def _build_service(
    project_id: str,
    events: list[PhaseEvent],
    violations: list[str] | None = None,
) -> tuple[SubagentStopService, SpyAuditWriter]:
    """Build a SubagentStopService with test doubles, return (service, audit_spy)."""
    audit_spy = SpyAuditWriter()
    service = SubagentStopService(
        log_reader=StubExecutionLogReader(project_id=project_id, events=events),
        completion_validator=StepCompletionValidator(schema=get_tdd_schema()),
        scope_checker=StubScopeChecker(violations=violations),
        audit_writer=audit_spy,
        time_provider=StubTimeProvider(),
    )
    return service, audit_spy


# --- AC1: All audit events use feature_name and step_id as direct AuditEvent fields ---


class TestAuditEventsUseDirectFields:
    """AC1: PASSED, FAILED, and SCOPE_VIOLATION events use feature_name and step_id
    as direct AuditEvent fields (not in data dict)."""

    def test_passed_event_has_feature_name_as_direct_field(self) -> None:
        """PASSED event has feature_name as direct AuditEvent field."""
        service, audit_spy = _build_service(
            project_id="my-feature",
            events=_make_complete_phase_events("02-01"),
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="02-01",
        )

        service.validate(context)

        passed = [
            e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_PASSED"
        ]
        assert len(passed) == 1
        assert passed[0].feature_name == "my-feature"

    def test_passed_event_has_step_id_as_direct_field(self) -> None:
        """PASSED event has step_id as direct AuditEvent field."""
        service, audit_spy = _build_service(
            project_id="my-feature",
            events=_make_complete_phase_events("02-01"),
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="02-01",
        )

        service.validate(context)

        passed = [
            e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_PASSED"
        ]
        assert len(passed) == 1
        assert passed[0].step_id == "02-01"

    def test_failed_event_has_feature_name_and_step_id_as_direct_fields(self) -> None:
        """FAILED event has both feature_name and step_id as direct AuditEvent fields."""
        service, audit_spy = _build_service(
            project_id="audit-log-refactor",
            events=_make_incomplete_phase_events("03-01"),
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="audit-log-refactor",
            step_id="03-01",
        )

        service.validate(context)

        failed = [
            e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_FAILED"
        ]
        assert len(failed) == 1
        assert failed[0].feature_name == "audit-log-refactor"
        assert failed[0].step_id == "03-01"

    def test_scope_violation_event_has_feature_name_and_step_id_as_direct_fields(
        self,
    ) -> None:
        """SCOPE_VIOLATION events have feature_name and step_id as direct AuditEvent fields."""
        service, audit_spy = _build_service(
            project_id="my-feature",
            events=_make_complete_phase_events("02-01"),
            violations=["src/other/file.py"],
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="02-01",
        )

        service.validate(context)

        scope_events = [
            e for e in audit_spy.events if e.event_type == "SCOPE_VIOLATION"
        ]
        assert len(scope_events) == 1
        assert scope_events[0].feature_name == "my-feature"
        assert scope_events[0].step_id == "02-01"


# --- AC2: feature_name populated from SubagentStopContext.project_id ---


class TestFeatureNameFromProjectId:
    """AC2: feature_name is populated from context.project_id for all event types."""

    @pytest.mark.parametrize(
        "project_id",
        [
            "audit-log-refactor",
            "another-project",
            "my-feature-123",
        ],
    )
    def test_passed_event_feature_name_equals_project_id(self, project_id: str) -> None:
        """PASSED event feature_name matches the context project_id."""
        service, audit_spy = _build_service(
            project_id=project_id,
            events=_make_complete_phase_events("01-01"),
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id=project_id,
            step_id="01-01",
        )

        service.validate(context)

        passed = [
            e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_PASSED"
        ]
        assert len(passed) == 1
        assert passed[0].feature_name == project_id


# --- AC3: All audit events retain existing fields in data dict ---


class TestExistingDataFieldsPreserved:
    """AC3: validation_errors and out_of_scope_file remain in data dict."""

    def test_failed_event_retains_validation_errors_in_data(self) -> None:
        """FAILED event still contains validation_errors in the data dict."""
        service, audit_spy = _build_service(
            project_id="my-feature",
            events=_make_incomplete_phase_events("01-01"),
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="01-01",
        )

        service.validate(context)

        failed = [
            e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_FAILED"
        ]
        assert len(failed) == 1
        assert "validation_errors" in failed[0].data
        assert isinstance(failed[0].data["validation_errors"], list)
        assert len(failed[0].data["validation_errors"]) > 0

    def test_failed_event_does_not_duplicate_step_id_in_data(self) -> None:
        """FAILED event should NOT have step_id in data dict (it is a direct field now)."""
        service, audit_spy = _build_service(
            project_id="my-feature",
            events=_make_incomplete_phase_events("01-01"),
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="01-01",
        )

        service.validate(context)

        failed = [
            e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_FAILED"
        ]
        assert len(failed) == 1
        assert "step_id" not in failed[0].data

    def test_scope_violation_retains_out_of_scope_file_in_data(self) -> None:
        """SCOPE_VIOLATION event still contains out_of_scope_file in data dict."""
        service, audit_spy = _build_service(
            project_id="my-feature",
            events=_make_complete_phase_events("02-01"),
            violations=["src/other/file.py"],
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="02-01",
        )

        service.validate(context)

        scope_events = [
            e for e in audit_spy.events if e.event_type == "SCOPE_VIOLATION"
        ]
        assert len(scope_events) == 1
        assert scope_events[0].data["out_of_scope_file"] == "src/other/file.py"

    def test_scope_violation_does_not_duplicate_step_id_in_data(self) -> None:
        """SCOPE_VIOLATION event should NOT have step_id in data dict."""
        service, audit_spy = _build_service(
            project_id="my-feature",
            events=_make_complete_phase_events("02-01"),
            violations=["src/other/file.py"],
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="02-01",
        )

        service.validate(context)

        scope_events = [
            e for e in audit_spy.events if e.event_type == "SCOPE_VIOLATION"
        ]
        assert len(scope_events) == 1
        assert "step_id" not in scope_events[0].data

    def test_passed_event_has_empty_data_dict(self) -> None:
        """PASSED event has no event-specific data, so data dict should be empty."""
        service, audit_spy = _build_service(
            project_id="my-feature",
            events=_make_complete_phase_events("02-01"),
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="02-01",
        )

        service.validate(context)

        passed = [
            e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_PASSED"
        ]
        assert len(passed) == 1
        assert passed[0].data == {}


# --- AC4: All existing audit logging conditions preserved ---


class TestAuditLoggingConditionsPreserved:
    """AC4: Events are logged under the same conditions as before."""

    def test_passed_event_logged_on_successful_validation(self) -> None:
        """PASSED event is logged when validation succeeds."""
        service, audit_spy = _build_service(
            project_id="my-feature",
            events=_make_complete_phase_events("02-01"),
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="02-01",
        )

        decision = service.validate(context)

        assert decision.action == "allow"
        passed = [
            e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_PASSED"
        ]
        assert len(passed) == 1

    def test_failed_event_logged_on_incomplete_validation(self) -> None:
        """FAILED event is logged when validation fails."""
        service, audit_spy = _build_service(
            project_id="my-feature",
            events=_make_incomplete_phase_events("01-01"),
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="01-01",
        )

        decision = service.validate(context)

        assert decision.action == "block"
        failed = [
            e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_FAILED"
        ]
        assert len(failed) == 1

    def test_scope_violations_logged_as_warnings_without_blocking(self) -> None:
        """Scope violations are logged as warnings but do not block."""
        service, audit_spy = _build_service(
            project_id="my-feature",
            events=_make_complete_phase_events("02-01"),
            violations=["src/a.py", "src/b.py"],
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="02-01",
        )

        decision = service.validate(context)

        assert decision.action == "allow"
        scope_events = [
            e for e in audit_spy.events if e.event_type == "SCOPE_VIOLATION"
        ]
        assert len(scope_events) == 2


# --- UT-18/UT-19: Integrity validation integration ---


class TestIntegrityValidationIntegration:
    """UT-18/UT-19: LogIntegrityValidator integration in SubagentStopService."""

    def test_integrity_warnings_logged_as_log_integrity_warning(self) -> None:
        """UT-18: Integrity warnings produce LOG_INTEGRITY_WARNING audit events."""
        from des.domain.log_integrity_validator import LogIntegrityValidator

        # Include an event with wrong phase name to trigger integrity warning
        events = _make_complete_phase_events("02-01")
        events.append(
            PhaseEvent(
                step_id="02-01",
                phase_name="REFACTOR",
                status="EXECUTED",
                outcome="PASS",
                timestamp="2026-02-06T21:07:00Z",
            )
        )

        audit_spy = SpyAuditWriter()
        schema = get_tdd_schema()
        service = SubagentStopService(
            log_reader=StubExecutionLogReader(project_id="my-feature", events=events),
            completion_validator=StepCompletionValidator(schema=schema),
            scope_checker=StubScopeChecker(),
            audit_writer=audit_spy,
            time_provider=StubTimeProvider(),
            integrity_validator=LogIntegrityValidator(schema=schema),
        )
        context = SubagentStopContext(
            execution_log_path="/fake/execution-log.yaml",
            project_id="my-feature",
            step_id="02-01",
        )

        decision = service.validate(context)

        assert decision.action == "allow"
        integrity_events = [
            e for e in audit_spy.events if e.event_type == "LOG_INTEGRITY_WARNING"
        ]
        assert len(integrity_events) >= 1
        assert "REFACTOR" in integrity_events[0].data["warning"]

    def test_integrity_check_does_not_block_on_warnings(self) -> None:
        """UT-19: Integrity warnings are warn-only, step still passes."""
        from des.domain.log_integrity_validator import LogIntegrityValidator

        events = _make_complete_phase_events("02-01")
        # Add a fabricated future-timestamp event
        events.append(
            PhaseEvent(
                step_id="02-01",
                phase_name="PREPARE",
                status="EXECUTED",
                outcome="PASS",
                timestamp="2099-01-01T00:00:00+00:00",
            )
        )

        audit_spy = SpyAuditWriter()
        schema = get_tdd_schema()
        time_provider = StubTimeProvider()
        service = SubagentStopService(
            log_reader=StubExecutionLogReader(project_id="my-feature", events=events),
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
            project_id="my-feature",
            step_id="02-01",
            task_start_time="2026-02-06T21:00:00+00:00",
        )

        decision = service.validate(context)

        # Step STILL passes despite integrity warnings
        assert decision.action == "allow"
        # Verify warnings were logged
        integrity_events = [
            e for e in audit_spy.events if e.event_type == "LOG_INTEGRITY_WARNING"
        ]
        assert len(integrity_events) >= 1
        # Verify PASSED event also logged
        passed = [
            e for e in audit_spy.events if e.event_type == "HOOK_SUBAGENT_STOP_PASSED"
        ]
        assert len(passed) == 1
