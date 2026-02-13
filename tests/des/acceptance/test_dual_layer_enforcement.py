"""
E2E Acceptance Test: US-009 Dual-Layer DES Enforcement (SubagentStop + PostToolUse)

PERSONA: Orchestrator (Parent Agent)
STORY: As an orchestrator, I want deterministic notification when a sub-agent fails
       to complete TDD phases, so I can take corrective action.

BUSINESS VALUE:
- Layer 1 (SubagentStop): Blocks sub-agent on first attempt, allows on second to prevent loops
- Layer 2 (PostToolUse): Fires AFTER Task returns to parent, injects additionalContext if FAILED
- Together: Parent ALWAYS knows when a sub-agent failed, even if SubagentStop couldn't fix it

SCOPE: Covers US-009 Acceptance Criteria (AC-009.1 through AC-009.7)
WAVE: DISTILL (Acceptance Test Creation)

TEST BOUNDARY: Port-to-port (driving port → application service → driven port stubs).
Tests invoke SubagentStopService and PostToolUseService directly with in-memory
adapters, matching the business behavior without subprocess overhead.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter
from des.application.post_tool_use_service import PostToolUseService
from des.application.subagent_stop_service import SubagentStopService
from des.domain.phase_event import PhaseEvent
from des.domain.step_completion_validator import StepCompletionValidator
from des.domain.tdd_schema import get_tdd_schema
from des.ports.driven_ports.audit_log_reader import AuditLogReader
from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter
from des.ports.driven_ports.execution_log_reader import ExecutionLogReader
from des.ports.driven_ports.scope_checker import ScopeChecker, ScopeCheckResult
from des.ports.driven_ports.time_provider_port import TimeProvider
from des.ports.driver_ports.subagent_stop_port import SubagentStopContext


if TYPE_CHECKING:
    from pathlib import Path


# =============================================================================
# TEST DOUBLES
# =============================================================================


class StubTimeProvider(TimeProvider):
    def now_utc(self) -> datetime:
        return datetime(2026, 2, 6, 12, 0, 0, tzinfo=timezone.utc)


class StubScopeChecker(ScopeChecker):
    def check_scope(
        self, project_root: Path, allowed_patterns: list[str]
    ) -> ScopeCheckResult:
        return ScopeCheckResult(has_violations=False, out_of_scope_files=[])


class SpyAuditWriter(AuditLogWriter):
    """Captures audit events for verification."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def log_event(self, event: AuditEvent) -> None:
        self.events.append(event)


class InMemoryLogReader(ExecutionLogReader):
    """In-memory execution log reader for testing."""

    def __init__(self, project_id: str, events: list[PhaseEvent]) -> None:
        self._project_id = project_id
        self._events = events

    def read_project_id(self, log_path: str) -> str:
        return self._project_id

    def read_step_events(self, log_path: str, step_id: str) -> list[PhaseEvent]:
        return [e for e in self._events if e.step_id == step_id]

    def read_all_events(self, log_path: str) -> list[PhaseEvent]:
        return self._events


class InMemoryAuditLogReader(AuditLogReader):
    """In-memory audit log reader for PostToolUse testing."""

    def __init__(self, entries: list[dict[str, Any]] | None = None) -> None:
        self._entries = entries or []

    def read_last_entry(
        self,
        event_type: str | None = None,
        feature_name: str | None = None,
        step_id: str | None = None,
    ) -> dict[str, Any] | None:
        for entry in reversed(self._entries):
            if event_type and entry.get("event") != event_type:
                continue
            if feature_name and entry.get("feature_name") != feature_name:
                continue
            if step_id and entry.get("step_id") != step_id:
                continue
            return entry
        return None


# =============================================================================
# SERVICE FACTORIES
# =============================================================================


def _build_stop_service(
    events: list[PhaseEvent],
    audit_writer: AuditLogWriter | None = None,
) -> SubagentStopService:
    """Build SubagentStopService with in-memory adapters."""
    schema = get_tdd_schema()
    return SubagentStopService(
        log_reader=InMemoryLogReader(project_id="test-project", events=events),
        completion_validator=StepCompletionValidator(schema=schema),
        scope_checker=StubScopeChecker(),
        audit_writer=audit_writer or NullAuditLogWriter(),
        time_provider=StubTimeProvider(),
    )


def _build_post_tool_use_service(
    entries: list[dict[str, Any]] | None = None,
) -> PostToolUseService:
    """Build PostToolUseService with in-memory audit log reader."""
    return PostToolUseService(audit_reader=InMemoryAuditLogReader(entries))


# =============================================================================
# EVENT BUILDERS
# =============================================================================


def _create_incomplete_events(tdd_phases) -> list[PhaseEvent]:
    """Create events with only first 2 phases completed (rest missing)."""
    return [
        PhaseEvent(
            step_id="01-01",
            phase_name=phase,
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-06T10:00:00+00:00",
        )
        for phase in tdd_phases[:2]
    ]


# =============================================================================
# ACCEPTANCE TESTS
# =============================================================================


class TestDualLayerEnforcement:
    """E2E acceptance tests for US-009: Dual-layer DES enforcement.

    All tests invoke application services directly through driving ports.
    """

    # =========================================================================
    # AC-009.1: SubagentStop blocks on first attempt (stop_hook_active=false)
    # Scenario 001
    # =========================================================================

    def test_subagent_stop_blocks_on_first_attempt(self, tdd_phases):
        """
        GIVEN a sub-agent completes with missing TDD phases
        AND stop_hook_active is false (first attempt)
        WHEN SubagentStop hook fires
        THEN decision is "block" with exit code 0
        AND reason contains actionable instructions

        Business Value: Sub-agent gets one chance to fix missing phases
                       before being allowed through.
        """
        events = _create_incomplete_events(tdd_phases)
        service = _build_stop_service(events)
        decision = service.validate(
            SubagentStopContext(
                execution_log_path="/fake/execution-log.yaml",
                project_id="test-project",
                step_id="01-01",
                stop_hook_active=False,
            )
        )

        assert decision.action == "block", (
            f"Expected block, got {decision.action}: {decision.reason}"
        )
        assert "Missing phases" in (decision.reason or "")

    # =========================================================================
    # AC-009.2: SubagentStop allows on second attempt (stop_hook_active=true)
    # Scenario 002
    # =========================================================================

    def test_subagent_stop_allows_on_second_attempt(self, tdd_phases):
        """
        GIVEN a sub-agent completes with missing TDD phases
        AND stop_hook_active is true (second attempt, loop prevention)
        WHEN SubagentStop hook fires
        THEN decision is "allow" (prevent infinite loop)
        AND audit log records HOOK_SUBAGENT_STOP_FAILED with allowed_despite_failure

        Business Value: Prevents infinite SubagentStop loops while still
                       recording the failure for PostToolUse to pick up.
        """
        events = _create_incomplete_events(tdd_phases)
        spy = SpyAuditWriter()
        service = _build_stop_service(events, audit_writer=spy)
        decision = service.validate(
            SubagentStopContext(
                execution_log_path="/fake/execution-log.yaml",
                project_id="test-project",
                step_id="01-01",
                stop_hook_active=True,
            )
        )

        # Assert: Allow decision (prevent loop)
        assert decision.action == "allow", (
            f"Expected allow, got {decision.action}: {decision.reason}"
        )

        # Assert: Audit log records FAILED with allowed_despite_failure
        failed_events = [
            e for e in spy.events if e.event_type == "HOOK_SUBAGENT_STOP_FAILED"
        ]
        assert len(failed_events) >= 1, (
            f"Expected HOOK_SUBAGENT_STOP_FAILED audit event, got: "
            f"{[e.event_type for e in spy.events]}"
        )
        assert failed_events[-1].data.get("allowed_despite_failure") is True

    # =========================================================================
    # AC-009.3: Block reason has actionable instructions
    # Scenario 003
    # =========================================================================

    def test_block_reason_has_actionable_instructions(self, tdd_phases):
        """
        GIVEN a sub-agent completes with missing TDD phases
        AND stop_hook_active is false (first attempt)
        WHEN SubagentStop hook fires and blocks
        THEN reason mentions specific missing phases AND step_id
        AND reason contains recovery instructions

        Business Value: Sub-agent receives clear, actionable instructions
                       to complete the missing work.
        """
        events = _create_incomplete_events(tdd_phases)
        service = _build_stop_service(events)
        decision = service.validate(
            SubagentStopContext(
                execution_log_path="/fake/execution-log.yaml",
                project_id="test-project",
                step_id="01-01",
                stop_hook_active=False,
            )
        )

        assert decision.action == "block"
        reason = decision.reason or ""
        # The service includes step_id context via the completion validator
        assert "Missing phases" in reason, "Reason should mention missing phases"
        # Should mention at least one specific missing phase
        missing_phases = tdd_phases[2:]  # First 2 included, rest missing
        assert any(phase in reason for phase in missing_phases), (
            f"Reason should mention specific missing phases, got: {reason}"
        )

    # =========================================================================
    # AC-009.4: PostToolUse detects FAILED in audit log
    # Scenario 004
    # =========================================================================

    def test_post_tool_use_detects_failed_audit(self):
        """
        GIVEN the audit log contains a HOOK_SUBAGENT_STOP_FAILED entry
        WHEN PostToolUse hook fires after Task returns to parent
        THEN response includes additionalContext with failure notification

        Business Value: Parent orchestrator is ALWAYS notified of sub-agent
                       failure, even when SubagentStop couldn't prevent it.
        """
        service = _build_post_tool_use_service(
            entries=[
                {
                    "event": "HOOK_SUBAGENT_STOP_FAILED",
                    "timestamp": "2026-02-06T10:00:00+00:00",
                    "feature_name": "test-project",
                    "step_id": "01-01",
                    "validation_errors": ["Missing phases: GREEN, REVIEW, COMMIT"],
                    "allowed_despite_failure": True,
                },
            ]
        )
        additional_context = service.check_completion_status(is_des_task=True)

        assert additional_context is not None, "Expected additionalContext"
        assert "FAILED" in additional_context or "failed" in additional_context.lower()

    # =========================================================================
    # AC-009.5: PostToolUse passes through on PASSED
    # Scenario 005
    # =========================================================================

    def test_post_tool_use_passes_through_on_passed(self):
        """
        GIVEN the audit log contains only HOOK_SUBAGENT_STOP_PASSED entries
        WHEN PostToolUse hook fires after Task returns to parent
        THEN no additionalContext is injected (clean passthrough) for non-DES tasks

        Business Value: Successful sub-agents don't trigger unnecessary
                       notifications to the parent.
        """
        service = _build_post_tool_use_service(
            entries=[
                {
                    "event": "HOOK_SUBAGENT_STOP_PASSED",
                    "timestamp": "2026-02-06T10:00:00+00:00",
                    "feature_name": "test-project",
                    "step_id": "01-01",
                },
            ]
        )
        # Non-DES task: should return None (no context injection)
        additional_context = service.check_completion_status(is_des_task=False)
        assert additional_context is None

    # =========================================================================
    # AC-009.5: PostToolUse passes through for non-DES tasks
    # Scenario 005b
    # =========================================================================

    def test_post_tool_use_passes_through_for_non_des(self):
        """
        GIVEN no audit log entries exist (non-DES task)
        WHEN PostToolUse hook fires after Task returns to parent
        THEN no additionalContext is injected

        Business Value: Non-DES tasks are not affected by DES enforcement.
        """
        service = _build_post_tool_use_service(entries=[])
        additional_context = service.check_completion_status(is_des_task=False)
        assert additional_context is None

    # =========================================================================
    # AC-009.6: additionalContext has recovery details
    # Scenario 006
    # =========================================================================

    def test_post_tool_use_additional_context_has_recovery_details(self):
        """
        GIVEN the audit log contains HOOK_SUBAGENT_STOP_FAILED with details
        WHEN PostToolUse hook fires
        THEN additionalContext includes feature_name, step_id, and errors

        Business Value: Parent receives enough context to decide whether
                       to retry, resume, or escalate.
        """
        service = _build_post_tool_use_service(
            entries=[
                {
                    "event": "HOOK_SUBAGENT_STOP_FAILED",
                    "timestamp": "2026-02-06T10:00:00+00:00",
                    "feature_name": "auth-upgrade",
                    "step_id": "02-03",
                    "validation_errors": ["Missing phases: GREEN, COMMIT"],
                    "allowed_despite_failure": True,
                },
            ]
        )
        ctx = service.check_completion_status(is_des_task=True)
        assert ctx is not None
        assert "auth-upgrade" in ctx, f"Should include feature_name, got: {ctx}"
        assert "02-03" in ctx, f"Should include step_id, got: {ctx}"
        assert "Missing phases" in ctx or "GREEN" in ctx, (
            f"Should include errors, got: {ctx}"
        )

    # =========================================================================
    # AC-009.7: Missing audit log = graceful passthrough
    # Scenario 007
    # =========================================================================

    def test_missing_audit_log_graceful_passthrough(self):
        """
        GIVEN the audit log has no entries (empty)
        WHEN PostToolUse hook fires
        THEN no crash, no additionalContext

        Business Value: System remains stable even when audit infrastructure
                       is missing.
        """
        service = _build_post_tool_use_service(entries=[])
        additional_context = service.check_completion_status(is_des_task=False)
        assert additional_context is None

    # =========================================================================
    # AC-009.8: PostToolUse injects continuation context for DES task PASSED
    # Scenario 008
    # =========================================================================

    def test_post_tool_use_injects_continuation_on_des_passed(self):
        """
        GIVEN the audit log contains HOOK_SUBAGENT_STOP_PASSED
        AND the just-completed Task prompt contains DES markers (is_des_task=True)
        WHEN PostToolUse hook fires
        THEN additionalContext includes continuation instructions with DES markers

        Business Value: Orchestrator is always reminded to continue the develop
                       workflow and include DES markers in the next dispatch,
                       ensuring every step is validated until feature completion.
        """
        service = _build_post_tool_use_service(
            entries=[
                {
                    "event": "HOOK_SUBAGENT_STOP_PASSED",
                    "timestamp": "2026-02-09T10:00:00+00:00",
                    "feature_name": "auth-upgrade",
                    "step_id": "01-01",
                },
            ]
        )
        ctx = service.check_completion_status(is_des_task=True)

        assert ctx is not None, "Expected continuation context"
        assert "COMPLETED" in ctx, f"Should indicate step completed, got: {ctx}"
        assert "auth-upgrade" in ctx, f"Should include project_id, got: {ctx}"
        assert "01-01" in ctx, f"Should include step_id, got: {ctx}"
        assert "DES-VALIDATION" in ctx, (
            f"Should include DES marker template, got: {ctx}"
        )
        assert "DES-PROJECT-ID" in ctx, (
            f"Should include DES-PROJECT-ID marker, got: {ctx}"
        )
        assert "DES-STEP-ID" in ctx, f"Should include DES-STEP-ID marker, got: {ctx}"
        assert "execute.md" in ctx, f"Should reference execute.md template, got: {ctx}"

    # =========================================================================
    # AC-009.9: PostToolUse failure includes DES reminder for DES tasks
    # Scenario 009
    # =========================================================================

    def test_post_tool_use_failure_includes_des_reminder_for_des_task(self):
        """
        GIVEN the audit log contains HOOK_SUBAGENT_STOP_FAILED
        AND the just-completed Task prompt contains DES markers (is_des_task=True)
        WHEN PostToolUse hook fires
        THEN additionalContext includes failure details AND DES marker reminder

        Business Value: On failure, orchestrator gets both the error details
                       and a reminder to include DES markers when re-dispatching.
        """
        service = _build_post_tool_use_service(
            entries=[
                {
                    "event": "HOOK_SUBAGENT_STOP_FAILED",
                    "timestamp": "2026-02-09T10:00:00+00:00",
                    "feature_name": "auth-upgrade",
                    "step_id": "02-01",
                    "validation_errors": ["Missing phases: GREEN, COMMIT"],
                    "allowed_despite_failure": True,
                },
            ]
        )
        ctx = service.check_completion_status(is_des_task=True)

        assert ctx is not None
        assert "FAILED" in ctx, f"Should indicate failure, got: {ctx}"
        assert "auth-upgrade" in ctx, f"Should include project_id, got: {ctx}"
        assert "02-01" in ctx, f"Should include step_id, got: {ctx}"
        assert "DES-VALIDATION" in ctx, (
            f"Should include DES marker reminder, got: {ctx}"
        )
        assert "execute.md" in ctx, f"Should reference execute.md, got: {ctx}"

    # =========================================================================
    # AC-009.10: Non-DES task still passes through even with PASSED audit
    # Scenario 010
    # =========================================================================

    def test_post_tool_use_non_des_task_no_continuation_despite_passed_audit(self):
        """
        GIVEN the audit log contains HOOK_SUBAGENT_STOP_PASSED from an earlier DES task
        AND the just-completed Task prompt does NOT contain DES markers
        WHEN PostToolUse hook fires
        THEN no additionalContext is injected (non-DES tasks unaffected)

        Business Value: Non-DES tasks are never polluted with DES continuation
                       context, even when DES events exist in the audit log.
        """
        service = _build_post_tool_use_service(
            entries=[
                {
                    "event": "HOOK_SUBAGENT_STOP_PASSED",
                    "timestamp": "2026-02-09T10:00:00+00:00",
                    "feature_name": "auth-upgrade",
                    "step_id": "01-01",
                },
            ]
        )
        # Non-DES task
        ctx = service.check_completion_status(is_des_task=False)
        assert ctx is None

    # =========================================================================
    # AC-009.7: SubagentStop empty context = allow passthrough (resilience 9a)
    # Scenario 007b
    # =========================================================================

    def test_subagent_stop_empty_context_allows_passthrough(self):
        """
        GIVEN no events exist for the step (empty context)
        AND stop_hook_active is true (second attempt)
        WHEN SubagentStop hook fires
        THEN allow decision (resilience fix 9a)

        Business Value: Empty context on SubagentStop should not block a
        completed subagent. The subagent already finished; blocking serves
        no purpose when context is missing.
        """
        service = _build_stop_service(events=[])
        decision = service.validate(
            SubagentStopContext(
                execution_log_path="/fake/execution-log.yaml",
                project_id="test-project",
                step_id="01-01",
                stop_hook_active=True,
            )
        )
        assert decision.action == "allow"
