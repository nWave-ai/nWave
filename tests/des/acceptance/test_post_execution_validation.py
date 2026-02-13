"""
E2E Acceptance Test: US-003 Post-Execution State Validation (Schema v2.0)

PERSONA: Marcus (Senior Developer)
STORY: As a senior developer, I want DES to automatically detect when phases are
       left abandoned (IN_PROGRESS) after sub-agent completion, so that I'm
       immediately alerted to incomplete work instead of discovering it hours later.

BUSINESS VALUE:
- Detects crashed agents before developers waste debugging time
- Catches silent completions where agent returned without updating state
- Validates execution integrity with specific, actionable error messages
- Enables immediate intervention instead of hours-later discovery

SCOPE: Covers US-003 Acceptance Criteria (AC-003.1 through AC-003.6)
WAVE: DISTILL (Acceptance Test Creation)
STATUS: Migrated to Schema v2.0 (execution-log.yaml format)

TEST BOUNDARY: Port-to-port (driving port → SubagentStopService → driven port stubs).
Tests invoke SubagentStopService.validate() directly with in-memory adapters,
matching the business behavior without subprocess overhead.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter
from des.application.subagent_stop_service import SubagentStopService
from des.domain.phase_event import PhaseEvent
from des.domain.step_completion_validator import StepCompletionValidator
from des.domain.tdd_schema import get_tdd_schema
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
        return datetime(2026, 2, 2, 12, 0, 0, tzinfo=timezone.utc)


class StubScopeChecker(ScopeChecker):
    def check_scope(
        self, project_root: Path, allowed_patterns: list[str]
    ) -> ScopeCheckResult:
        return ScopeCheckResult(has_violations=False, out_of_scope_files=[])


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


# =============================================================================
# SERVICE FACTORY
# =============================================================================


def _build_service(events: list[PhaseEvent]) -> SubagentStopService:
    """Build SubagentStopService with in-memory adapters."""
    schema = get_tdd_schema()
    return SubagentStopService(
        log_reader=InMemoryLogReader(project_id="test-project", events=events),
        completion_validator=StepCompletionValidator(schema=schema),
        scope_checker=StubScopeChecker(),
        audit_writer=NullAuditLogWriter(),
        time_provider=StubTimeProvider(),
    )


def _make_context(
    step_id: str = "01-01",
    project_id: str = "test-project",
    stop_hook_active: bool = False,
) -> SubagentStopContext:
    """Build a SubagentStopContext for testing."""
    return SubagentStopContext(
        execution_log_path="/fake/execution-log.yaml",
        project_id=project_id,
        step_id=step_id,
        stop_hook_active=stop_hook_active,
    )


# =============================================================================
# EVENT BUILDERS
# =============================================================================


def _make_all_phases_executed(tdd_phases, step_id="01-01") -> list[PhaseEvent]:
    """Create events with all phases EXECUTED with PASS."""
    return [
        PhaseEvent(
            step_id=step_id,
            phase_name=phase,
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-02T10:00:00+00:00",
        )
        for phase in tdd_phases
    ]


def _make_abandoned_phase_events(
    tdd_phases, abandoned_phase, last_completed_phase, step_id="01-01"
) -> list[PhaseEvent]:
    """Create events where a phase is missing (simulates abandoned)."""
    last_idx = tdd_phases.index(last_completed_phase)
    return [
        PhaseEvent(
            step_id=step_id,
            phase_name=phase,
            status="EXECUTED",
            outcome="PASS",
            timestamp="2026-02-02T10:00:00+00:00",
        )
        for i, phase in enumerate(tdd_phases)
        if i <= last_idx
    ]


def _make_silent_completion_events() -> list[PhaseEvent]:
    """Create empty event list (simulates silent completion)."""
    return []


def _make_missing_outcome_events(
    tdd_phases, phase_name, step_id="01-01"
) -> list[PhaseEvent]:
    """Create events where one EXECUTED phase has invalid outcome."""
    events = []
    for phase in tdd_phases:
        if phase == phase_name:
            events.append(
                PhaseEvent(
                    step_id=step_id,
                    phase_name=phase,
                    status="EXECUTED",
                    outcome="",
                    timestamp="2026-02-02T10:00:00+00:00",
                )
            )
        else:
            events.append(
                PhaseEvent(
                    step_id=step_id,
                    phase_name=phase,
                    status="EXECUTED",
                    outcome="PASS",
                    timestamp="2026-02-02T10:00:00+00:00",
                )
            )
    return events


def _make_invalid_skip_events(
    tdd_phases, skipped_phase, step_id="01-01"
) -> list[PhaseEvent]:
    """Create events where one SKIPPED phase has invalid reason."""
    events = []
    for phase in tdd_phases:
        if phase == skipped_phase:
            events.append(
                PhaseEvent(
                    step_id=step_id,
                    phase_name=phase,
                    status="SKIPPED",
                    outcome="No reason given",
                    timestamp="2026-02-02T10:00:00+00:00",
                )
            )
        else:
            events.append(
                PhaseEvent(
                    step_id=step_id,
                    phase_name=phase,
                    status="EXECUTED",
                    outcome="PASS",
                    timestamp="2026-02-02T10:00:00+00:00",
                )
            )
    return events


def _make_multiple_issues_events(tdd_phases, step_id="01-01") -> list[PhaseEvent]:
    """Create events with multiple validation issues."""
    events = []
    # First 3 phases OK
    for phase in tdd_phases[:3]:
        events.append(
            PhaseEvent(
                step_id=step_id,
                phase_name=phase,
                status="EXECUTED",
                outcome="PASS",
                timestamp="2026-02-02T10:00:00+00:00",
            )
        )
    # Phase 4 missing (abandoned)
    # Phase 5 has invalid outcome
    if len(tdd_phases) > 4:
        events.append(
            PhaseEvent(
                step_id=step_id,
                phase_name=tdd_phases[4],
                status="EXECUTED",
                outcome="",
                timestamp="2026-02-02T10:00:00+00:00",
            )
        )
    # Phase 6 has invalid skip
    if len(tdd_phases) > 5:
        events.append(
            PhaseEvent(
                step_id=step_id,
                phase_name=tdd_phases[5],
                status="SKIPPED",
                outcome="Bad reason",
                timestamp="2026-02-02T10:00:00+00:00",
            )
        )
    # Remaining phases missing
    return events


def _make_valid_skip_events(tdd_phases, step_id="01-01") -> list[PhaseEvent]:
    """Create events with legitimately skipped phase."""
    events = []
    for phase in tdd_phases:
        if phase == "GREEN":
            events.append(
                PhaseEvent(
                    step_id=step_id,
                    phase_name=phase,
                    status="SKIPPED",
                    outcome="APPROVED_SKIP:Code already meets quality standards",
                    timestamp="2026-02-02T10:00:00+00:00",
                )
            )
        else:
            events.append(
                PhaseEvent(
                    step_id=step_id,
                    phase_name=phase,
                    status="EXECUTED",
                    outcome="PASS",
                    timestamp="2026-02-02T10:00:00+00:00",
                )
            )
    return events


# =============================================================================
# ACCEPTANCE TESTS
# =============================================================================


class TestPostExecutionStateValidation:
    """E2E acceptance tests for US-003: Post-execution state validation (Schema v2.0).

    All tests invoke SubagentStopService.validate() directly through the driving port.
    This matches the business behavior and survives internal refactoring.
    """

    # =========================================================================
    # AC-003.1: SubagentStop hook fires for every sub-agent completion
    # Scenario 1: SubagentStop hook invoked on agent completion
    # =========================================================================

    def test_subagent_stop_hook_fires_on_agent_completion(self, tdd_phases):
        """
        GIVEN software-crafter agent completes step 01-01 execution
        WHEN the sub-agent returns control to orchestrator
        THEN SubagentStop hook fires and validates execution-log state

        Business Value: Marcus receives immediate feedback on execution state
                       the moment an agent completes, preventing silent failures
                       from going unnoticed until the next day.

        Domain Example: Software-crafter finishes step 01-01, hook validates
                       that all started phases were properly completed.
        """
        events = _make_all_phases_executed(tdd_phases)
        service = _build_service(events)
        decision = service.validate(_make_context())

        assert decision.action == "allow", (
            f"Expected allow, got {decision.action}: {decision.reason}"
        )

    # =========================================================================
    # AC-003.2: Phases with status "IN_PROGRESS" after completion are flagged
    # Scenario 2: Abandoned phase detected after agent crash
    # =========================================================================

    def test_abandoned_in_progress_phase_detected(self, tdd_phases):
        """
        GIVEN software-crafter agent crashed during GREEN phase
        AND execution-log.yaml shows GREEN phase never logged (missing from events)
        WHEN SubagentStop hook fires after agent process terminates
        THEN hook detects abandoned phase and flags it with specific error

        Business Value: Marcus is immediately alerted when an agent crashes
                       mid-execution, avoiding 2+ hours of debugging time
                       discovering the issue the next day.

        Domain Example: Agent was implementing GREEN, crashed due to
                       network error. GREEN phase never appears in event log,
                       indicating work was started but never completed.

        Error Format: "Missing phases: GREEN" (in v2.0, abandoned = missing from log)
        """
        events = _make_abandoned_phase_events(
            tdd_phases, abandoned_phase="GREEN", last_completed_phase="RED_UNIT"
        )
        service = _build_service(events)
        decision = service.validate(_make_context())

        assert decision.action == "block", (
            f"Expected block, got {decision.action}: {decision.reason}"
        )
        assert "GREEN" in (decision.reason or "")
        assert "Missing phases" in (decision.reason or "")

    # =========================================================================
    # AC-003.3: Tasks marked "DONE" with "NOT_EXECUTED" phases are flagged
    # Scenario 3: Silent completion detected (agent returned without executing)
    # =========================================================================

    def test_done_task_with_not_executed_phases_flagged(self, tdd_phases):
        """
        GIVEN software-crafter agent returned without updating execution-log
        AND events list is empty (no phases logged)
        WHEN SubagentStop hook fires
        THEN hook detects mismatch and flags as silent completion error

        Business Value: Marcus catches agents that claimed to work but
                       actually did nothing, preventing false confidence
                       in task completion.

        Domain Example: Agent received step 01-01 but encountered an error
                       early and returned without logging any phases.
                       Events list is empty.

        Error Format: All phases listed as missing in the error reason
        """
        events = _make_silent_completion_events()
        service = _build_service(events)
        decision = service.validate(_make_context())

        assert decision.action == "block", (
            f"Expected block, got {decision.action}: {decision.reason}"
        )
        assert "Missing phases" in (decision.reason or "")
        # All TDD phases should appear in the missing phases list
        for phase in tdd_phases:
            assert phase in (decision.reason or ""), (
                f"Phase {phase} should be listed as missing in: {decision.reason}"
            )
        # Recovery guidance provided in recovery_suggestions
        assert len(decision.recovery_suggestions) > 0, (
            "Expected recovery suggestions to be provided"
        )

    # =========================================================================
    # AC-003.4: "EXECUTED" phases without outcome field are flagged
    # Scenario 4: Incomplete phase execution detected (no outcome recorded)
    # =========================================================================

    def test_executed_phase_without_outcome_flagged(self, tdd_phases):
        """
        GIVEN execution-log.yaml shows GREEN phase with status "EXECUTED"
        AND the phase has invalid outcome (empty string instead of PASS/FAIL)
        WHEN SubagentStop hook validates the execution log
        THEN hook flags the phase as incomplete execution

        Business Value: Marcus ensures all executed phases have documented
                       outcomes, maintaining audit trail for Priya's PR reviews
                       and preventing "I finished but didn't record what I did"
                       situations.

        Domain Example: Agent marked GREEN as EXECUTED but forgot to
                       record outcome. Without valid outcome, there's no evidence
                       of work completion.

        Error Format: "Invalid outcome ''"  (in v2.0, outcome is in data field)
        """
        events = _make_missing_outcome_events(tdd_phases, "GREEN")
        service = _build_service(events)
        decision = service.validate(_make_context())

        assert decision.action == "block", (
            f"Expected block, got {decision.action}: {decision.reason}"
        )
        assert "GREEN" in (decision.reason or "")
        assert "Invalid outcome" in (decision.reason or "")

    # =========================================================================
    # AC-003.5: "SKIPPED" phases must have valid `blocked_by` reason
    # Scenario 5: Skipped phase with missing blocked_by reason flagged
    # =========================================================================

    def test_skipped_phase_without_blocked_by_reason_flagged(self, tdd_phases):
        """
        GIVEN execution-log.yaml shows GREEN phase with status "SKIPPED"
        AND the phase has invalid skip reason (no valid prefix)
        WHEN SubagentStop hook validates the execution log
        THEN hook flags the skip as invalid (must have valid prefix)

        Business Value: Marcus ensures all skipped phases have documented
                       reasons, preventing arbitrary phase skipping without
                       justification. Priya can verify during PR review that
                       skips were legitimate.

        Domain Example: Agent skipped GREEN but didn't provide valid reason.
                       Without valid prefix (BLOCKED_BY_DEPENDENCY,
                       NOT_APPLICABLE, APPROVED_SKIP, etc.), we can't verify
                       if skip was legitimate.

        Error Format: "Invalid skip reason" (in v2.0, must start with valid prefix)
        """
        events = _make_invalid_skip_events(tdd_phases, "GREEN")
        service = _build_service(events)
        decision = service.validate(_make_context())

        assert decision.action == "block", (
            f"Expected block, got {decision.action}: {decision.reason}"
        )
        assert "GREEN" in (decision.reason or "")
        assert "skip reason" in (decision.reason or "").lower()

    # =========================================================================
    # AC-003.6: Validation errors trigger FAILED state with recovery suggestions
    # Scenario 6: Multiple validation errors trigger FAILED state
    # =========================================================================

    def test_validation_errors_trigger_failed_state_with_recovery(self, tdd_phases):
        """
        GIVEN execution-log.yaml has multiple issues:
          - Missing phases (abandoned)
          - Invalid outcome (incomplete)
          - Invalid skip reason
        WHEN SubagentStop hook validates the execution log
        THEN validation status is FAILED with all errors listed
        AND recovery suggestions are provided for each error type

        Business Value: Marcus receives comprehensive failure report with
                       clear recovery path, enabling immediate resolution
                       without guesswork.

        Domain Example: Agent only logged first 3 phases, then crashed.
                       One phase has invalid outcome, another has invalid skip.
                       All issues reported together with recovery steps.

        Recovery Suggestions Expected:
        - "Resume execution to complete missing phases"
        - "Fix invalid phase entries in execution-log.yaml"
        - "Ensure EXECUTED phases have PASS/FAIL outcome"
        """
        events = _make_multiple_issues_events(tdd_phases)
        service = _build_service(events)
        decision = service.validate(_make_context())

        assert decision.action == "block", (
            f"Expected block, got {decision.action}: {decision.reason}"
        )

        # Assert: Multiple issue types captured in reason
        reason = decision.reason or ""
        assert "Missing phases" in reason, "Should report abandoned/missing phases"
        assert "Invalid" in reason, "Should report invalid phases (outcome or skip)"

        # Assert: Recovery suggestions provided
        assert len(decision.recovery_suggestions) > 0, (
            "Expected recovery suggestions to be provided"
        )

        # Recovery suggestions should be actionable
        suggestions_text = " ".join(decision.recovery_suggestions).lower()
        assert any(
            keyword in suggestions_text
            for keyword in ["fix", "ensure", "resume", "format"]
        ), "Should provide actionable recovery guidance"

    # =========================================================================
    # Happy Path: Clean completion passes validation silently
    # Scenario 7: All phases executed correctly - validation passes
    # =========================================================================

    def test_clean_completion_passes_validation(self, tdd_phases):
        """
        GIVEN software-crafter agent completes all 5 phases successfully
        AND each phase shows "EXECUTED" with valid outcome (PASS)
        WHEN SubagentStop hook validates the execution log
        THEN validation passes successfully

        Business Value: Marcus confirms that properly completed steps are
                       validated silently without unnecessary alerts, allowing
                       smooth workflow continuation.

        Domain Example: Agent executed all 5 phases (PREPARE through COMMIT),
                       each with PASS outcome. Validation confirms integrity
                       and logs success.
        """
        events = _make_all_phases_executed(tdd_phases)
        service = _build_service(events)
        decision = service.validate(_make_context())

        assert decision.action == "allow", (
            f"Expected allow, got {decision.action}: {decision.reason}"
        )

    # =========================================================================
    # Edge Case: Valid skip with proper blocked_by reason passes
    # Scenario 8: Legitimately skipped phases pass validation
    # =========================================================================

    def test_valid_skip_with_blocked_by_passes_validation(self, tdd_phases):
        """
        GIVEN execution-log.yaml shows GREEN phase with status "SKIPPED"
        AND the phase has valid skip reason with APPROVED_SKIP prefix
        WHEN SubagentStop hook validates the execution log
        THEN validation passes (skip is legitimate)

        Business Value: Marcus confirms that legitimate skips with proper
                       justification are accepted, not flagged as errors.
                       Allows appropriate phase skipping when conditions warrant.

        Domain Example: Agent determined GREEN tests already pass. Properly
                       documented with APPROVED_SKIP prefix:
                       "APPROVED_SKIP:Code already meets quality standards"
        """
        events = _make_valid_skip_events(tdd_phases)
        service = _build_service(events)
        decision = service.validate(_make_context())

        assert decision.action == "allow", (
            f"Expected allow, got {decision.action}: {decision.reason}"
        )


# =============================================================================
# WIRING TESTS: Validation through DESOrchestrator Entry Point (CM-A/CM-D)
# =============================================================================


class TestOrchestratorHookIntegration:
    """
    Integration tests that verify SubagentStopHook is wired into DESOrchestrator.

    These tests exercise the ENTRY POINT (DESOrchestrator) rather than the
    internal component (SubagentStopHook) directly. This is the 10% E2E test
    that proves the wiring works (per CM-D 90/10 rule).
    """

    def test_orchestrator_invokes_subagent_stop_hook_on_completion(
        self, tmp_project_root, minimal_step_file, tdd_phases
    ):
        """
        GIVEN DESOrchestrator configured with a HookPort
        WHEN on_subagent_complete() is called with a step file path
        THEN the hook's on_agent_complete() is invoked exactly once
        AND the step file path is forwarded to the hook
        """
        from des.adapters.driven.filesystem.in_memory_filesystem import (
            InMemoryFileSystem,
        )
        from des.adapters.driven.time.mocked_time import MockedTimeProvider
        from des.adapters.drivers.hooks.mocked_hook import MockedSubagentStopHook
        from des.adapters.drivers.validators.mocked_validator import (
            MockedTemplateValidator,
        )
        from des.application.orchestrator import DESOrchestrator, HookResult

        hook = MockedSubagentStopHook(HookResult(validation_status="PASSED"))
        orchestrator = DESOrchestrator(
            hook=hook,
            validator=MockedTemplateValidator(),
            filesystem=InMemoryFileSystem(),
            time_provider=MockedTimeProvider(
                datetime(2026, 2, 2, 12, 0, 0, tzinfo=timezone.utc)
            ),
        )

        step_path = str(minimal_step_file)
        result = orchestrator.on_subagent_complete(step_path)

        assert hook.call_count == 1, (
            f"Hook should fire exactly once, fired {hook.call_count}"
        )
        assert hook.last_step_file_path == step_path
        assert result.validation_status == "PASSED"

    def test_orchestrator_detects_abandoned_phase_via_entry_point(
        self, tmp_project_root, minimal_step_file, tdd_phases
    ):
        """
        GIVEN DESOrchestrator configured with a hook that returns FAILED
        WHEN on_subagent_complete() is called
        THEN the orchestrator propagates the FAILED result with abandoned phase info
        """
        from des.adapters.driven.filesystem.in_memory_filesystem import (
            InMemoryFileSystem,
        )
        from des.adapters.driven.time.mocked_time import MockedTimeProvider
        from des.adapters.drivers.hooks.mocked_hook import MockedSubagentStopHook
        from des.adapters.drivers.validators.mocked_validator import (
            MockedTemplateValidator,
        )
        from des.application.orchestrator import DESOrchestrator, HookResult

        hook = MockedSubagentStopHook(
            HookResult(
                validation_status="FAILED",
                abandoned_phases=["GREEN"],
                error_count=1,
                error_message="Missing phases: GREEN",
                recovery_suggestions=["Resume GREEN phase execution"],
            )
        )
        orchestrator = DESOrchestrator(
            hook=hook,
            validator=MockedTemplateValidator(),
            filesystem=InMemoryFileSystem(),
            time_provider=MockedTimeProvider(
                datetime(2026, 2, 2, 12, 0, 0, tzinfo=timezone.utc)
            ),
        )

        result = orchestrator.on_subagent_complete(str(minimal_step_file))

        assert result.validation_status == "FAILED"
        assert "GREEN" in result.abandoned_phases
        assert result.error_count == 1
        assert "Missing phases" in (result.error_message or "")
