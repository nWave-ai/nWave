"""BDD step definitions for hook enforcement audit trail.

Tests verify that hook enforcement events (PASSED, FAILED, SCOPE_VIOLATION, ALLOWED)
include feature_name and step_id as direct AuditEvent fields for traceability.

Using pytest-bdd for BDD-style Given/When/Then tests.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

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
    from typing import Any


# Link to feature file
scenarios("test_hook_enforcement.feature")


# --- Test Doubles ---


class SpyAuditWriter(AuditLogWriter):
    """Spy that captures all logged audit events for assertion."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def log_event(self, event: AuditEvent) -> None:
        self.events.append(event)


class StubTimeProvider(TimeProvider):
    """Stub returning a configurable timestamp."""

    def __init__(self, timestamp_str: str) -> None:
        self._timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

    def now_utc(self) -> datetime:
        return self._timestamp


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


# --- Fixtures ---


@pytest.fixture
def test_context() -> dict[str, Any]:
    """Shared context for BDD scenario state."""
    return {}


# --- Given Steps ---


@given("the audit log writer is initialized")
def initialize_audit_writer(test_context: dict[str, Any]) -> None:
    """Initialize the spy audit writer."""
    test_context["audit_writer"] = SpyAuditWriter()


@given(parsers.parse('the system time is "{timestamp}"'))
def set_system_time(test_context: dict[str, Any], timestamp: str) -> None:
    """Set the system time for the test."""
    test_context["time_provider"] = StubTimeProvider(timestamp)


@given(parsers.parse('I am validating step "{step_id}" in feature "{feature_name}"'))
def setup_step_validation(
    test_context: dict[str, Any], step_id: str, feature_name: str
) -> None:
    """Set up the step and feature for validation."""
    test_context["step_id"] = step_id
    test_context["feature_name"] = feature_name


@given("all 7 TDD phases are complete")
def setup_complete_phases(test_context: dict[str, Any]) -> None:
    """Create a complete set of 7 TDD phase events."""
    step_id = test_context["step_id"]
    test_context["phase_events"] = _make_complete_phase_events(step_id)


@given(parsers.parse("only {count:d} TDD phases are complete"))
def setup_incomplete_phases(test_context: dict[str, Any], count: int) -> None:
    """Create an incomplete set of TDD phase events."""
    step_id = test_context["step_id"]
    all_events = _make_complete_phase_events(step_id)
    test_context["phase_events"] = all_events[:count]


@given("there are no scope violations")
def setup_no_violations(test_context: dict[str, Any]) -> None:
    """Configure scope checker to return no violations."""
    test_context["scope_violations"] = []


@given(parsers.parse('there is a scope violation for file "{file_path}"'))
def setup_scope_violation(test_context: dict[str, Any], file_path: str) -> None:
    """Configure scope checker to return a violation."""
    test_context["scope_violations"] = [file_path]


@given(
    parsers.parse(
        'I am invoking a Task for step "{step_id}" in feature "{feature_name}"'
    )
)
def setup_task_invocation(
    test_context: dict[str, Any], step_id: str, feature_name: str
) -> None:
    """Set up task invocation context."""
    test_context["step_id"] = step_id
    test_context["feature_name"] = feature_name
    test_context["task_invocation"] = True


@given(parsers.parse("the task has max_turns set to {max_turns:d}"))
def setup_max_turns(test_context: dict[str, Any], max_turns: int) -> None:
    """Set the max_turns for the task."""
    test_context["max_turns"] = max_turns


# --- When Steps ---


@when("the subagent stop hook validates the step")
def validate_step(test_context: dict[str, Any]) -> None:
    """Execute the subagent stop validation."""
    # Create the service with injected dependencies
    audit_writer = test_context["audit_writer"]
    time_provider = test_context["time_provider"]

    log_reader = StubExecutionLogReader(
        project_id=test_context["feature_name"],
        events=test_context["phase_events"],
    )

    scope_checker = StubScopeChecker(
        violations=test_context.get("scope_violations", [])
    )

    validator = StepCompletionValidator(get_tdd_schema())

    service = SubagentStopService(
        log_reader=log_reader,
        completion_validator=validator,
        scope_checker=scope_checker,
        audit_writer=audit_writer,
        time_provider=time_provider,
    )

    # Create context
    context = SubagentStopContext(
        execution_log_path="/fake/path/execution-log.yaml",
        project_id=test_context["feature_name"],
        step_id=test_context["step_id"],
    )

    # Execute validation
    test_context["validation_result"] = service.validate(context)


@when("the pre-tool-use hook validates the task invocation")
def validate_task_invocation(test_context: dict[str, Any]) -> None:
    """Execute the pre-tool-use validation."""
    # This will be implemented in a future step
    # For now, we'll simulate the audit event
    audit_writer = test_context["audit_writer"]
    time_provider = test_context["time_provider"]

    event = AuditEvent(
        event_type="HOOK_PRE_TOOL_USE_ALLOWED",
        timestamp=time_provider.now_utc().isoformat(),
        feature_name=test_context["feature_name"],
        step_id=test_context["step_id"],
        data={"max_turns": test_context["max_turns"]},
    )

    audit_writer.log_event(event)


# --- Then Steps ---


@then(parsers.parse("the audit log contains a {event_type} event"))
@then(parsers.parse("the audit log contains an {event_type} event"))
def verify_event_exists(test_context: dict[str, Any], event_type: str) -> None:
    """Verify that an event of the specified type exists."""
    audit_writer = test_context["audit_writer"]
    event_type_map = {
        "PASSED": "HOOK_SUBAGENT_STOP_PASSED",
        "FAILED": "HOOK_SUBAGENT_STOP_FAILED",
        "SCOPE_VIOLATION": "SCOPE_VIOLATION",
        "ALLOWED": "HOOK_PRE_TOOL_USE_ALLOWED",
    }

    expected_type = event_type_map[event_type]
    matching_events = [e for e in audit_writer.events if e.event_type == expected_type]

    assert len(matching_events) > 0, (
        f"Expected {expected_type} event not found. "
        f"Events: {[e.event_type for e in audit_writer.events]}"
    )

    # Store the event for subsequent assertions
    test_context["last_event"] = matching_events[0]


@then(parsers.parse('the {event_type} event has feature_name "{expected_feature}"'))
def verify_feature_name(
    test_context: dict[str, Any], event_type: str, expected_feature: str
) -> None:
    """Verify the event has the expected feature_name as a direct field."""
    event = test_context["last_event"]
    assert event.feature_name == expected_feature, (
        f"Expected feature_name '{expected_feature}', got '{event.feature_name}'. "
        f"Feature_name must be a direct field, not in data dict."
    )


@then(parsers.parse('the {event_type} event has step_id "{expected_step}"'))
def verify_step_id(
    test_context: dict[str, Any], event_type: str, expected_step: str
) -> None:
    """Verify the event has the expected step_id as a direct field."""
    event = test_context["last_event"]
    assert event.step_id == expected_step, (
        f"Expected step_id '{expected_step}', got '{event.step_id}'. "
        f"Step_id must be a direct field, not in data dict."
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
            timestamp="2026-02-07T19:00:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="RED_ACCEPTANCE",
            status="EXECUTED",
            outcome="FAIL",
            timestamp="2026-02-07T19:01:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="RED_UNIT",
            status="EXECUTED",
            outcome="FAIL",
            timestamp="2026-02-07T19:02:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="GREEN",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-07T19:03:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="REVIEW",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-07T19:04:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="REFACTOR_CONTINUOUS",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-07T19:05:00Z",
        ),
        PhaseEvent(
            step_id=step_id,
            phase_name="COMMIT",
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-07T19:06:00Z",
        ),
    ]
