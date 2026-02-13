"""Unit tests for SubagentStopService audit logging with feature_name and step_id.

Tests verify that all audit events (PASSED, FAILED, SCOPE_VIOLATION) log both
feature_name and step_id extracted from execution context.
"""

from datetime import datetime, timezone
from pathlib import Path

from des.application.subagent_stop_service import SubagentStopService
from des.domain.phase_event import PhaseEventParser
from des.domain.step_completion_validator import StepCompletionValidator
from des.domain.tdd_schema import get_tdd_schema
from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter
from des.ports.driven_ports.execution_log_reader import ExecutionLogReader
from des.ports.driven_ports.scope_checker import ScopeChecker, ScopeCheckResult
from des.ports.driven_ports.time_provider_port import TimeProvider
from des.ports.driver_ports.subagent_stop_port import SubagentStopContext


class MockAuditWriter(AuditLogWriter):
    """Mock audit writer that captures logged events."""

    def __init__(self):
        self.events: list[AuditEvent] = []

    def log_event(self, event: AuditEvent) -> None:
        self.events.append(event)


class MockTimeProvider(TimeProvider):
    """Mock time provider with fixed timestamp."""

    def now_utc(self) -> datetime:
        return datetime(2026, 2, 6, 15, 0, 0, tzinfo=timezone.utc)


class MockExecutionLogReader(ExecutionLogReader):
    """Mock execution log reader that parses string events into PhaseEvent objects."""

    def __init__(self, project_id: str, events: list[str]):
        self._project_id = project_id
        self._parser = PhaseEventParser()
        self._events = events

    def read_project_id(self, log_path: str) -> str:
        return self._project_id

    def read_step_events(self, log_path: str, step_id: str):
        return [
            e for e in (self._parser.parse(s) for s in self._events) if e is not None
        ]

    def read_all_events(self, log_path: str):
        return [
            e for e in (self._parser.parse(s) for s in self._events) if e is not None
        ]


class MockScopeChecker(ScopeChecker):
    """Mock scope checker."""

    def __init__(self, violations: list[str] | None = None):
        self._violations = violations or []

    def check_scope(
        self, project_root: Path, allowed_patterns: list[str]
    ) -> ScopeCheckResult:
        return ScopeCheckResult(
            has_violations=len(self._violations) > 0,
            out_of_scope_files=self._violations,
        )


# @pytest.mark.skip removed for RED phase
def test_audit_log_passed_includes_feature_name_and_step_id():
    """AC1: PASSED event logs feature_name and step_id."""
    # Given: Valid step completion
    log_reader = MockExecutionLogReader(
        project_id="audit-log-refactor",
        events=[
            "02-02|PREPARE|EXECUTED|PASS|2026-02-06T15:00:00Z",
            "02-02|RED_ACCEPTANCE|EXECUTED|FAIL|2026-02-06T15:01:00Z",
            "02-02|RED_UNIT|EXECUTED|FAIL|2026-02-06T15:02:00Z",
            "02-02|GREEN|EXECUTED|PASS|2026-02-06T15:03:00Z",
            "02-02|REVIEW|EXECUTED|PASS|2026-02-06T15:04:00Z",
            "02-02|REFACTOR_CONTINUOUS|SKIPPED|APPROVED_SKIP:Clean implementation|2026-02-06T15:05:00Z",
            "02-02|COMMIT|EXECUTED|PASS|2026-02-06T15:06:00Z",
        ],
    )
    scope_checker = MockScopeChecker(violations=[])
    audit_writer = MockAuditWriter()
    time_provider = MockTimeProvider()

    service = SubagentStopService(
        log_reader=log_reader,
        completion_validator=StepCompletionValidator(schema=get_tdd_schema()),
        scope_checker=scope_checker,
        audit_writer=audit_writer,
        time_provider=time_provider,
    )

    context = SubagentStopContext(
        execution_log_path="/fake/path/execution-log.yaml",
        project_id="audit-log-refactor",
        step_id="02-02",
    )

    # When: Validating successful completion
    decision = service.validate(context)

    # Then: PASSED event includes both feature_name and step_id
    assert decision.action == "allow"
    passed_events = [
        e for e in audit_writer.events if e.event_type == "HOOK_SUBAGENT_STOP_PASSED"
    ]
    assert len(passed_events) == 1

    passed_event = passed_events[0]
    assert passed_event.feature_name == "audit-log-refactor"
    assert passed_event.step_id == "02-02"


# @pytest.mark.skip removed for RED phase
def test_audit_log_failed_includes_feature_name_and_step_id():
    """AC2: FAILED event logs feature_name and step_id."""
    # Given: Invalid step completion (missing COMMIT phase)
    log_reader = MockExecutionLogReader(
        project_id="audit-log-refactor",
        events=[
            "02-02|PREPARE|EXECUTED|PASS|2026-02-06T15:00:00Z",
            "02-02|RED_ACCEPTANCE|EXECUTED|FAIL|2026-02-06T15:01:00Z",
            # Missing COMMIT phase - invalid completion
        ],
    )
    scope_checker = MockScopeChecker(violations=[])
    audit_writer = MockAuditWriter()
    time_provider = MockTimeProvider()

    service = SubagentStopService(
        log_reader=log_reader,
        completion_validator=StepCompletionValidator(schema=get_tdd_schema()),
        scope_checker=scope_checker,
        audit_writer=audit_writer,
        time_provider=time_provider,
    )

    context = SubagentStopContext(
        execution_log_path="/fake/path/execution-log.yaml",
        project_id="audit-log-refactor",
        step_id="02-02",
    )

    # When: Validating failed completion
    decision = service.validate(context)

    # Then: FAILED event includes both feature_name and step_id
    assert decision.action == "block"
    failed_events = [
        e for e in audit_writer.events if e.event_type == "HOOK_SUBAGENT_STOP_FAILED"
    ]
    assert len(failed_events) == 1

    failed_event = failed_events[0]
    assert failed_event.feature_name == "audit-log-refactor"
    assert failed_event.step_id == "02-02"
    assert "validation_errors" in failed_event.data  # Existing field preserved


# @pytest.mark.skip removed for RED phase
def test_audit_log_scope_violation_includes_feature_name_and_step_id():
    """AC3: SCOPE_VIOLATION event logs feature_name and step_id."""
    # Given: Valid completion but with scope violations
    log_reader = MockExecutionLogReader(
        project_id="audit-log-refactor",
        events=[
            "02-02|PREPARE|EXECUTED|PASS|2026-02-06T15:00:00Z",
            "02-02|RED_ACCEPTANCE|EXECUTED|FAIL|2026-02-06T15:01:00Z",
            "02-02|RED_UNIT|EXECUTED|FAIL|2026-02-06T15:02:00Z",
            "02-02|GREEN|EXECUTED|PASS|2026-02-06T15:03:00Z",
            "02-02|REVIEW|EXECUTED|PASS|2026-02-06T15:04:00Z",
            "02-02|REFACTOR_CONTINUOUS|SKIPPED|APPROVED_SKIP:Clean|2026-02-06T15:05:00Z",
            "02-02|COMMIT|EXECUTED|PASS|2026-02-06T15:06:00Z",
        ],
    )
    scope_checker = MockScopeChecker(
        violations=[
            "src/some/other/feature/file.py",
            "docs/other-feature/README.md",
        ]
    )
    audit_writer = MockAuditWriter()
    time_provider = MockTimeProvider()

    service = SubagentStopService(
        log_reader=log_reader,
        completion_validator=StepCompletionValidator(schema=get_tdd_schema()),
        scope_checker=scope_checker,
        audit_writer=audit_writer,
        time_provider=time_provider,
    )

    context = SubagentStopContext(
        execution_log_path="/fake/path/execution-log.yaml",
        project_id="audit-log-refactor",
        step_id="02-02",
    )

    # When: Validating with scope violations
    decision = service.validate(context)

    # Then: SCOPE_VIOLATION events include both feature_name and step_id
    assert decision.action == "allow"  # Scope violations are warnings, not blockers
    scope_events = [e for e in audit_writer.events if e.event_type == "SCOPE_VIOLATION"]
    assert len(scope_events) == 2  # One per violation

    for scope_event in scope_events:
        assert scope_event.feature_name == "audit-log-refactor"
        assert scope_event.step_id == "02-02"
        assert "out_of_scope_file" in scope_event.data  # Existing field preserved


# @pytest.mark.skip removed for RED phase
def test_audit_log_retains_all_existing_fields():
    """AC4: All existing fields in audit events are preserved."""
    # Given: Failed validation with multiple error messages
    log_reader = MockExecutionLogReader(
        project_id="test-feature",
        events=[
            "01-01|PREPARE|EXECUTED|PASS|2026-02-06T15:00:00Z",
            # Missing all other phases
        ],
    )
    scope_checker = MockScopeChecker(violations=[])
    audit_writer = MockAuditWriter()
    time_provider = MockTimeProvider()

    service = SubagentStopService(
        log_reader=log_reader,
        completion_validator=StepCompletionValidator(schema=get_tdd_schema()),
        scope_checker=scope_checker,
        audit_writer=audit_writer,
        time_provider=time_provider,
    )

    context = SubagentStopContext(
        execution_log_path="/fake/path/execution-log.yaml",
        project_id="test-feature",
        step_id="01-01",
    )

    # When: Validating failed completion
    decision = service.validate(context)

    # Then: FAILED event preserves all existing fields
    assert decision.action == "block"
    failed_events = [
        e for e in audit_writer.events if e.event_type == "HOOK_SUBAGENT_STOP_FAILED"
    ]
    assert len(failed_events) == 1

    failed_event = failed_events[0]
    assert failed_event.event_type == "HOOK_SUBAGENT_STOP_FAILED"
    assert failed_event.timestamp == "2026-02-06T15:00:00+00:00"
    assert failed_event.feature_name == "test-feature"
    assert failed_event.step_id == "01-01"
    assert "validation_errors" in failed_event.data
    assert isinstance(failed_event.data["validation_errors"], list)
    assert len(failed_event.data["validation_errors"]) > 0
