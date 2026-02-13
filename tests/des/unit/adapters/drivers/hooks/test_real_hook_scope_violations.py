"""Unit tests specifically for scope violation logging in SubagentStopService.

Comprehensive test coverage for SCOPE_VIOLATION audit events with feature_name and step_id.
"""

from datetime import datetime, timezone
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
    """Mock execution log reader returning PhaseEvent objects."""

    def __init__(self, project_id: str, events: list[PhaseEvent]):
        self._project_id = project_id
        self._events = events

    def read_project_id(self, log_path: str) -> str:
        return self._project_id

    def read_step_events(self, log_path: str, step_id: str) -> list[PhaseEvent]:
        return [e for e in self._events if e.step_id == step_id]

    def read_all_events(self, log_path: str) -> list[PhaseEvent]:
        return self._events


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


def _create_valid_events(step_id: str = "02-02") -> list[PhaseEvent]:
    """Helper: Create valid 7-phase TDD events as PhaseEvent objects."""
    phases = [
        ("PREPARE", "EXECUTED", "PASS", "2026-02-06T15:00:00Z"),
        ("RED_ACCEPTANCE", "EXECUTED", "FAIL", "2026-02-06T15:01:00Z"),
        ("RED_UNIT", "EXECUTED", "FAIL", "2026-02-06T15:02:00Z"),
        ("GREEN", "EXECUTED", "PASS", "2026-02-06T15:03:00Z"),
        ("REVIEW", "EXECUTED", "PASS", "2026-02-06T15:04:00Z"),
        (
            "REFACTOR_CONTINUOUS",
            "SKIPPED",
            "APPROVED_SKIP:Clean",
            "2026-02-06T15:05:00Z",
        ),
        ("COMMIT", "EXECUTED", "PASS", "2026-02-06T15:06:00Z"),
    ]
    return [
        PhaseEvent(
            step_id=step_id,
            phase_name=phase,
            status=status,
            outcome=outcome,
            timestamp=ts,
        )
        for phase, status, outcome, ts in phases
    ]


def test_single_scope_violation_logs_feature_name():
    """AC1: Single scope violation event includes feature_name and step_id."""
    # Given: Valid completion with one scope violation
    log_reader = MockExecutionLogReader(
        project_id="audit-log-refactor",
        events=_create_valid_events(),
    )
    scope_checker = MockScopeChecker(violations=["src/other/feature/file.py"])
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

    # When: Validating with scope violation
    decision = service.validate(context)

    # Then: SCOPE_VIOLATION event includes feature_name and step_id
    assert decision.action == "allow"  # Warnings don't block
    scope_events = [e for e in audit_writer.events if e.event_type == "SCOPE_VIOLATION"]
    assert len(scope_events) == 1

    violation_event = scope_events[0]
    assert violation_event.feature_name == "audit-log-refactor"
    assert violation_event.step_id == "02-02"
    assert violation_event.data["out_of_scope_file"] == "src/other/feature/file.py"


def test_multiple_scope_violations_each_log_feature_name():
    """AC2: Multiple scope violations each log feature_name and step_id."""
    # Given: Valid completion with multiple scope violations
    violations = [
        "src/other/feature/file1.py",
        "src/another/feature/file2.py",
        "docs/wrong-feature/README.md",
    ]
    log_reader = MockExecutionLogReader(
        project_id="test-feature",
        events=_create_valid_events(),
    )
    scope_checker = MockScopeChecker(violations=violations)
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
        step_id="02-02",
    )

    # When: Validating with multiple scope violations
    decision = service.validate(context)

    # Then: Each SCOPE_VIOLATION event includes feature_name and step_id
    assert decision.action == "allow"
    scope_events = [e for e in audit_writer.events if e.event_type == "SCOPE_VIOLATION"]
    assert len(scope_events) == 3

    for i, violation_event in enumerate(scope_events):
        assert violation_event.feature_name == "test-feature"
        assert violation_event.step_id == "02-02"
        assert violation_event.data["out_of_scope_file"] == violations[i]


def test_no_scope_violations_no_events_logged():
    """AC3: When no violations, no SCOPE_VIOLATION events logged."""
    # Given: Valid completion with no scope violations
    log_reader = MockExecutionLogReader(
        project_id="clean-feature",
        events=_create_valid_events(step_id="03-01"),
    )
    scope_checker = MockScopeChecker(violations=[])  # No violations
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
        project_id="clean-feature",
        step_id="03-01",
    )

    # When: Validating without scope violations
    decision = service.validate(context)

    # Then: No SCOPE_VIOLATION events logged
    assert decision.action == "allow"
    scope_events = [e for e in audit_writer.events if e.event_type == "SCOPE_VIOLATION"]
    assert len(scope_events) == 0

    # But PASSED event should still be logged
    passed_events = [
        e for e in audit_writer.events if e.event_type == "HOOK_SUBAGENT_STOP_PASSED"
    ]
    assert len(passed_events) == 1
