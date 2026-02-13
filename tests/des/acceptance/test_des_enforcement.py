"""
E2E Acceptance Test: US-011 DES Enforcement Hardening

PERSONA: Orchestrator (Parent Agent)
STORY: As an orchestrator, I want Task invocations referencing step IDs to be blocked
       unless they include DES markers, so that step execution is always monitored.

BUSINESS VALUE:
- Closes Scenario A: Task with step-id but without DES markers → BLOCKED
- Closes incomplete markers: DES-VALIDATION present but project/step IDs missing → BLOCKED
- Zero false positives on research/non-step tasks

SCOPE: Covers US-011 Acceptance Criteria (AC-011.1 through AC-011.9)
WAVE: DISTILL (Acceptance Test Creation)

TEST BOUNDARY: Port-to-port (driving port → application service → driven port stubs).
Tests invoke PreToolUseService and SessionGuardPolicy directly, matching the
business behavior without subprocess overhead.
"""

from datetime import datetime, timezone

from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter
from des.application.pre_tool_use_service import PreToolUseService
from des.domain.des_enforcement_policy import DesEnforcementPolicy
from des.domain.des_marker_parser import DesMarkerParser
from des.domain.marker_completeness_policy import MarkerCompletenessPolicy
from des.domain.max_turns_policy import MaxTurnsPolicy
from des.domain.session_guard_policy import SessionGuardPolicy
from des.ports.driver_ports.pre_tool_use_port import PreToolUseInput
from tests.des.acceptance.conftest import FakeTimeProvider


# =============================================================================
# SERVICE FACTORY: Build PreToolUseService with production domain, null I/O
# =============================================================================


def _build_pre_tool_use_service() -> PreToolUseService:
    """Build PreToolUseService with real domain logic and null I/O adapters."""
    return PreToolUseService(
        max_turns_policy=MaxTurnsPolicy(),
        marker_parser=DesMarkerParser(),
        prompt_validator=_make_template_validator(),
        audit_writer=NullAuditLogWriter(),
        time_provider=FakeTimeProvider(
            datetime(2026, 2, 12, 10, 0, 0, tzinfo=timezone.utc)
        ),
        enforcement_policy=DesEnforcementPolicy(),
        completeness_policy=MarkerCompletenessPolicy(),
    )


def _make_template_validator():
    """Create TemplateValidator (real validation, no I/O)."""
    from des.application.validator import TemplateValidator

    return TemplateValidator()


def _make_valid_des_prompt(
    project_id: str = "auth-upgrade", step_id: str = "01-01"
) -> str:
    """Build a fully valid DES prompt with all mandatory sections."""
    return f"""<!-- DES-VALIDATION : required -->
<!-- DES-PROJECT-ID : {project_id} -->
<!-- DES-STEP-ID : {step_id} -->

# DES_METADATA
Project: {project_id}
Step: {step_id}
Command: /nw:execute

# AGENT_IDENTITY
Agent: @software-crafter
Role: Implement features through Outside-In TDD

# TASK_CONTEXT
**Title**: Implement feature
**Type**: feature

Acceptance Criteria:
- Feature works as expected

# TDD_PHASES
Execute all 5 phases:
1. PREPARE
2. RED_ACCEPTANCE
3. RED_UNIT
4. GREEN
5. REVIEW
6. REFACTOR_CONTINUOUS
7. COMMIT

# QUALITY_GATES
- All tests must pass
- Code quality validated

# OUTCOME_RECORDING
Update execution-log.yaml after each phase.

# RECORDING_INTEGRITY
Valid Skip Prefixes: NOT_APPLICABLE, BLOCKED_BY_DEPENDENCY, APPROVED_SKIP, CHECKPOINT_PENDING
Anti-Fraud Rules: NEVER write EXECUTED for phases not performed. DES audits all entries.

# BOUNDARY_RULES
- Follow hexagonal architecture

Files to modify:
- src/feature.py

# TIMEOUT_INSTRUCTION
Turn budget: 50 turns
Exit on: completion or blocking issue
"""


# =============================================================================
# PHASE 1: Step-ID Enforcement Tests (AC-011.1 through AC-011.6)
# =============================================================================


class TestStepIdEnforcement:
    """E2E tests for step-id enforcement policy."""

    # AC-011.1: Step-id + no markers → BLOCKED
    def test_step_id_without_markers_blocked(self):
        """
        GIVEN a Task prompt containing step-id pattern 01-01
        AND no DES markers present
        WHEN PreToolUse hook fires
        THEN exit code is 2 (block)
        AND response contains block decision
        """
        service = _build_pre_tool_use_service()
        decision = service.validate(
            PreToolUseInput(
                prompt="Execute step 01-01 for the authentication feature",
                max_turns=30,
                subagent_type="nw-software-crafter",
            )
        )
        assert decision.exit_code == 2, (
            f"Expected exit_code 2 (block), got {decision.exit_code}: {decision.reason}"
        )
        assert decision.action == "block"
        assert "DES_MARKERS_MISSING" in (decision.reason or "")

    # AC-011.2: Step-id + markers present → ALLOWED
    def test_step_id_with_markers_allowed(self):
        """
        GIVEN a Task prompt containing step-id pattern 01-01
        AND DES-VALIDATION marker present with full valid prompt
        WHEN PreToolUse hook fires
        THEN exit code is 0 (allow)
        """
        service = _build_pre_tool_use_service()
        decision = service.validate(
            PreToolUseInput(
                prompt=_make_valid_des_prompt(),
                max_turns=30,
                subagent_type="nw-software-crafter",
            )
        )
        assert decision.exit_code == 0, (
            f"Expected exit_code 0 (allow), got {decision.exit_code}: {decision.reason}"
        )

    # AC-011.3: No step-id → ALLOWED
    def test_no_step_id_allowed(self):
        """
        GIVEN a Task prompt without step-id patterns
        WHEN PreToolUse hook fires
        THEN exit code is 0 (allow)
        """
        service = _build_pre_tool_use_service()
        decision = service.validate(
            PreToolUseInput(
                prompt="Research authentication best practices for the project",
                max_turns=30,
                subagent_type="nw-researcher",
            )
        )
        assert decision.exit_code == 0, (
            f"Expected exit_code 0 (allow), got {decision.exit_code}: {decision.reason}"
        )

    # AC-011.4: Step-id + exempt marker → ALLOWED
    def test_exempt_marker_allowed(self):
        """
        GIVEN a Task prompt containing step-id pattern
        AND DES-ENFORCEMENT exempt marker present
        WHEN PreToolUse hook fires
        THEN exit code is 0 (allow)
        """
        service = _build_pre_tool_use_service()
        decision = service.validate(
            PreToolUseInput(
                prompt=(
                    "<!-- DES-ENFORCEMENT : exempt -->\n"
                    "Review roadmap step 01-01 for completeness"
                ),
                max_turns=30,
                subagent_type="nw-solution-architect",
            )
        )
        assert decision.exit_code == 0, (
            f"Expected exit_code 0 (allow), got {decision.exit_code}: {decision.reason}"
        )

    # AC-011.5: Block reason contains DES marker template
    def test_block_reason_contains_recovery_suggestions(self):
        """
        GIVEN a Task prompt blocked by step-id enforcement
        WHEN PreToolUse hook fires
        THEN block reason contains DES_MARKERS_MISSING
        AND response includes marker template guidance
        """
        service = _build_pre_tool_use_service()
        decision = service.validate(
            PreToolUseInput(
                prompt="Implement step 02-03 changes to the system",
                max_turns=30,
                subagent_type="nw-software-crafter",
            )
        )
        assert decision.exit_code == 2
        reason = decision.reason or ""
        assert "DES_MARKERS_MISSING" in reason
        assert "02-03" in reason

    # AC-011.6: Audit log records blocked event
    def test_audit_log_records_blocked_event(self):
        """
        GIVEN a Task prompt blocked by step-id enforcement
        WHEN PreToolUse hook fires
        THEN audit writer receives HOOK_PRE_TOOL_USE_BLOCKED with DES_MARKERS_MISSING
        """
        from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter

        class SpyAuditWriter(AuditLogWriter):
            def __init__(self):
                self.events: list[AuditEvent] = []

            def log_event(self, event: AuditEvent) -> None:
                self.events.append(event)

        spy = SpyAuditWriter()
        service = PreToolUseService(
            max_turns_policy=MaxTurnsPolicy(),
            marker_parser=DesMarkerParser(),
            prompt_validator=_make_template_validator(),
            audit_writer=spy,
            time_provider=FakeTimeProvider(
                datetime(2026, 2, 12, 10, 0, 0, tzinfo=timezone.utc)
            ),
            enforcement_policy=DesEnforcementPolicy(),
            completeness_policy=MarkerCompletenessPolicy(),
        )

        service.validate(
            PreToolUseInput(
                prompt="Execute step 01-01",
                max_turns=30,
                subagent_type="nw-software-crafter",
            )
        )

        blocked_events = [
            e for e in spy.events if e.event_type == "HOOK_PRE_TOOL_USE_BLOCKED"
        ]
        assert len(blocked_events) >= 1, (
            f"Expected HOOK_PRE_TOOL_USE_BLOCKED event, got: "
            f"{[e.event_type for e in spy.events]}"
        )
        assert "DES_MARKERS_MISSING" in (blocked_events[-1].data.get("reason", ""))


# =============================================================================
# PHASE 2: Session Guard Tests (AC-011.10 through AC-011.13)
# =============================================================================


class TestSessionGuard:
    """E2E tests for Write/Edit session guard (Scenario B prevention)."""

    # AC-011.10: Source write blocked during deliver without DES task
    def test_source_write_blocked_during_deliver(self):
        """
        GIVEN deliver session is active
        AND no DES task signal (des_task_active is False)
        WHEN Write tool targets a source file
        THEN guard result is blocked
        """
        policy = SessionGuardPolicy()
        result = policy.check(
            file_path="src/auth/user_auth.py",
            session_active=True,
            des_task_active=False,
        )
        assert result.blocked, f"Expected blocked, got allowed: {result.reason}"

    # AC-011.11: Source write allowed with DES task active
    def test_source_write_allowed_with_des_task(self):
        """
        GIVEN deliver session is active
        AND DES task signal exists (des_task_active is True)
        WHEN Write tool targets a source file
        THEN guard result is not blocked
        """
        policy = SessionGuardPolicy()
        result = policy.check(
            file_path="src/auth/user_auth.py",
            session_active=True,
            des_task_active=True,
        )
        assert not result.blocked, f"Expected allowed, got blocked: {result.reason}"

    # AC-011.12: Orchestration file allowed during deliver
    def test_orchestration_file_allowed_during_deliver(self):
        """
        GIVEN deliver session is active
        AND no DES task signal
        WHEN Write tool targets docs/feature/ file
        THEN guard result is not blocked
        """
        policy = SessionGuardPolicy()
        result = policy.check(
            file_path="docs/feature/test/roadmap.yaml",
            session_active=True,
            des_task_active=False,
        )
        assert not result.blocked, f"Expected allowed, got blocked: {result.reason}"

    # AC-011.13: No deliver session = all writes allowed
    def test_no_deliver_session_allows_all(self):
        """
        GIVEN no deliver session marker exists
        WHEN Write tool targets a source file
        THEN guard result is not blocked
        """
        policy = SessionGuardPolicy()
        result = policy.check(
            file_path="src/auth/user_auth.py",
            session_active=False,
            des_task_active=False,
        )
        assert not result.blocked, f"Expected allowed, got blocked: {result.reason}"


# =============================================================================
# PHASE 3: Marker Completeness Tests (AC-011.7 through AC-011.9)
# =============================================================================


class TestMarkerCompleteness:
    """E2E tests for DES marker completeness validation."""

    # AC-011.7: DES-VALIDATION present, DES-PROJECT-ID missing → BLOCKED
    def test_missing_project_id_blocked(self):
        """
        GIVEN DES-VALIDATION marker present
        AND DES-PROJECT-ID missing
        WHEN PreToolUse hook fires
        THEN exit code is 2 (block)
        AND reason contains DES_MARKERS_INCOMPLETE
        """
        service = _build_pre_tool_use_service()
        decision = service.validate(
            PreToolUseInput(
                prompt=(
                    "<!-- DES-VALIDATION : required -->\n"
                    "<!-- DES-STEP-ID : 01-01 -->\n"
                    "Execute step 01-01"
                ),
                max_turns=30,
                subagent_type="nw-software-crafter",
            )
        )
        assert decision.exit_code == 2, (
            f"Expected exit_code 2 (block), got {decision.exit_code}: {decision.reason}"
        )
        assert "DES_MARKERS_INCOMPLETE" in (decision.reason or "")
        assert "DES-PROJECT-ID" in (decision.reason or "")

    # AC-011.8: DES-VALIDATION present, DES-STEP-ID missing → BLOCKED
    def test_missing_step_id_blocked(self):
        """
        GIVEN DES-VALIDATION marker present
        AND DES-STEP-ID missing (non-orchestrator mode)
        WHEN PreToolUse hook fires
        THEN exit code is 2 (block)
        AND reason contains DES_MARKERS_INCOMPLETE
        """
        service = _build_pre_tool_use_service()
        decision = service.validate(
            PreToolUseInput(
                prompt=(
                    "<!-- DES-VALIDATION : required -->\n"
                    "<!-- DES-PROJECT-ID : auth-upgrade -->\n"
                    "Execute step 01-01"
                ),
                max_turns=30,
                subagent_type="nw-software-crafter",
            )
        )
        assert decision.exit_code == 2, (
            f"Expected exit_code 2 (block), got {decision.exit_code}: {decision.reason}"
        )
        assert "DES_MARKERS_INCOMPLETE" in (decision.reason or "")
        assert "DES-STEP-ID" in (decision.reason or "")

    # AC-011.9: DES-VALIDATION + both IDs → ALLOWED
    def test_complete_markers_allowed(self):
        """
        GIVEN DES-VALIDATION marker present
        AND both DES-PROJECT-ID and DES-STEP-ID present
        WHEN PreToolUse hook fires
        THEN exit code is 0 (allow)
        """
        service = _build_pre_tool_use_service()
        decision = service.validate(
            PreToolUseInput(
                prompt=_make_valid_des_prompt(),
                max_turns=30,
                subagent_type="nw-software-crafter",
            )
        )
        assert decision.exit_code == 0, (
            f"Expected exit_code 0 (allow), got {decision.exit_code}: {decision.reason}"
        )
