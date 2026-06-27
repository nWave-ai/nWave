"""E2E acceptance: the DES PreToolUse gate accepts the ADR-025 3-phase TDD canon.

PERSONA: a crafter dispatched into a DELIVER/execute step following the documented
ADR-025 canon (RED / GREEN / COMMIT).
STORY: As a developer following the current methodology, I want the DES PreToolUse
gate to accept a 3-phase DELIVER prompt, so the documented canon is actually usable
without hand-writing the legacy 5-phase contract.

Drives the live gate (`PreToolUseService`) through the production composition — real
`DesMarkerParser` + `TemplateValidator` + enforcement/completeness policies, null I/O
— so the embedded `phase_execution_log` canon check is exercised exactly as the hook
runs it (port-to-port mandate).

Regression for nWave issue #65: the gate forced `schema_version="4.0"`, rejecting a
3-phase prompt with "Phase log has 3 phases, expected 5 phases from schema".
Refs: https://github.com/nWave-ai/nWave/issues/65
"""

from __future__ import annotations

from datetime import datetime, timezone

from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter
from des.application.pre_tool_use_service import PreToolUseService
from des.application.validator import TemplateValidator
from des.domain.des_enforcement_policy import DesEnforcementPolicy
from des.domain.des_marker_parser import DesMarkerParser
from des.domain.marker_completeness_policy import MarkerCompletenessPolicy
from des.ports.driver_ports.pre_tool_use_port import PreToolUseInput
from tests.des.acceptance.conftest import FakeTimeProvider


CANONICAL_3_PHASE = ("RED", "GREEN", "COMMIT")
LEGACY_5_PHASE = ("PREPARE", "RED_ACCEPTANCE", "RED_UNIT", "GREEN", "COMMIT")


def _build_gate() -> PreToolUseService:
    """Production composition of the DES PreToolUse gate with null I/O adapters."""
    return PreToolUseService(
        marker_parser=DesMarkerParser(),
        prompt_validator=TemplateValidator(),
        audit_writer=NullAuditLogWriter(),
        time_provider=FakeTimeProvider(
            datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
        ),
        enforcement_policy=DesEnforcementPolicy(),
        completeness_policy=MarkerCompletenessPolicy(),
    )


def _deliver_prompt(
    phases: tuple[str, ...], project_id: str = "issue-65", step_id: str = "01-01"
) -> str:
    """A complete, marked DES DELIVER prompt whose TDD_PHASES *and* embedded
    execution log use *phases* — so the per-log canon dispatch is exercised."""
    tdd_lines = "\n".join(f"{i}. {p}" for i, p in enumerate(phases, 1))
    log_lines = "\n".join(f"Phase {p}: status=EXECUTED, outcome=PASS" for p in phases)
    return f"""<!-- DES-VALIDATION : required -->
<!-- DES-PROJECT-ID : {project_id} -->
<!-- DES-STEP-ID : {step_id} -->

# DES_METADATA
Project: {project_id}
Step: {step_id}
Command: /nw-execute

# AGENT_IDENTITY
Agent: @software-crafter

# TASK_CONTEXT
**Title**: Implement the feature via Outside-In TDD

# TDD_PHASES
Execute all {len(phases)} phases:
{tdd_lines}

# QUALITY_GATES
- All tests must pass

# OUTCOME_RECORDING
Update execution-log.json after each phase.

# RECORDING_INTEGRITY
Valid Skip Prefixes: NOT_APPLICABLE, BLOCKED_BY_DEPENDENCY, APPROVED_SKIP, CHECKPOINT_PENDING
Anti-Fraud Rules: NEVER write EXECUTED for phases not performed.

# BOUNDARY_RULES
- Follow hexagonal architecture

# TIMEOUT_INSTRUCTION
Turn budget: 50 turns

# EXECUTION_LOG_COMPLETE
{log_lines}
"""


class TestDeliver3PhaseCanonGate:
    """The DES PreToolUse gate accepts the ADR-025 3-phase canon (issue #65)."""

    def test_three_phase_deliver_prompt_is_allowed(self) -> None:
        """
        GIVEN a DELIVER prompt using the 3-phase canon (RED/GREEN/COMMIT) with a
              matching embedded phase_execution_log
        WHEN the DES PreToolUse gate validates it
        THEN the task invocation is allowed (exit 0).

        Pre-#65 the gate blocked this with "Phase log has 3 phases, expected 5".
        """
        decision = _build_gate().validate(
            PreToolUseInput(
                prompt=_deliver_prompt(CANONICAL_3_PHASE),
                subagent_type="nw-software-crafter",
            )
        )
        assert decision.exit_code == 0, (
            "3-phase DELIVER prompt was blocked by the live gate (issue #65). "
            f"reason={decision.reason}"
        )

    def test_legacy_five_phase_deliver_prompt_still_allowed(self) -> None:
        """
        GIVEN a DELIVER prompt using the legacy 5-phase contract with a matching
              embedded phase_execution_log
        WHEN the DES PreToolUse gate validates it
        THEN the task invocation is still allowed (exit 0) — audit-log replay
             backward-compat preserved.
        """
        decision = _build_gate().validate(
            PreToolUseInput(
                prompt=_deliver_prompt(LEGACY_5_PHASE),
                subagent_type="nw-software-crafter",
            )
        )
        assert decision.exit_code == 0, (
            f"Legacy 5-phase DELIVER prompt regressed. reason={decision.reason}"
        )
