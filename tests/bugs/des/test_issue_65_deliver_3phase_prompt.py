"""Regression guard: DELIVER prompts may use the ADR-025 3-phase TDD canon.

Background (nWave issue #65):
The live DES PreToolUse gate, ``TemplateValidator.validate_prompt``, validated a
prompt's embedded ``phase_execution_log`` with a HARDCODED ``schema_version="4.0"``
(``src/des/application/validator.py``). That forced the legacy 5-phase contract
(PREPARE / RED_ACCEPTANCE / RED_UNIT / GREEN / COMMIT), so a clean ADR-025
3-phase prompt (RED / GREEN / COMMIT) was rejected with
``Phase log has 3 phases, expected 5 phases from schema`` — even though
``ExecutionLogValidator`` already auto-detects the canon per-log and every other
live validator was migrated to per-log dispatch (the 2026-05-18 flip). This was
the single remaining live-path layer forcing v4.

The fix lets ``validate_prompt`` use the default/auto-detect path instead of
forcing ``"4.0"``. Auto-detect returns legacy phases ONLY when the COMPLETE
legacy-only set {PREPARE, RED_ACCEPTANCE, RED_UNIT} is present, so legacy
5-phase logs keep validating (audit-log replay, pre-2026-05-07) while clean
3-phase logs are accepted.

Refs: https://github.com/nWave-ai/nWave/issues/65 ; ADR-025 (2026-05-07).
"""

from __future__ import annotations

from des.application.validator import TemplateValidator


# The 9 mandatory sections a DES prompt must carry (mirrors the prompt the
# orchestrator emits). Kept inline so this regression guard is self-contained.
_BASE_SECTIONS = """<!-- DES-VALIDATION: required -->

## DES_METADATA
step_id: test-65-01
project_id: issue-65
step_file: steps/test-65-01.json

## AGENT_IDENTITY
You are @software-crafter executing this step.

## TASK_CONTEXT
Implement the feature with a complete TDD cycle.

## QUALITY_GATES
G1: All tests pass
G2: No code smells
G3: Coverage >= 80%

## OUTCOME_RECORDING
Record phase outcomes in the step file after each phase.

## RECORDING_INTEGRITY
Valid Skip Prefixes: NOT_APPLICABLE, BLOCKED_BY_DEPENDENCY, APPROVED_SKIP, CHECKPOINT_PENDING
Anti-Fraud Rules: NEVER write EXECUTED for phases not actually performed.

## BOUNDARY_RULES
ALLOWED:
- Modify implementation files in scope
FORBIDDEN:
- Skip mandatory phases without a valid reason

## TIMEOUT_INSTRUCTION
Turn budget: approximately 50 turns
Progress checkpoints: ~10, ~25, ~40, ~50
"""

CANONICAL_3_PHASE = ("RED", "GREEN", "COMMIT")
LEGACY_5_PHASE = ("PREPARE", "RED_ACCEPTANCE", "RED_UNIT", "GREEN", "COMMIT")


def _build_prompt(phases: tuple[str, ...]) -> str:
    """A complete DES prompt whose TDD_PHASES + embedded execution log use *phases*."""
    tdd_phases_section = (
        "## TDD_PHASES\n"
        f"Execute all {len(phases)} phases from schema:\n" + ", ".join(phases)
    )
    execution_log = "# EXECUTION_LOG_COMPLETE\n" + "\n".join(
        f"Phase {phase}: status=EXECUTED, outcome=PASS" for phase in phases
    )
    return f"{_BASE_SECTIONS}\n{tdd_phases_section}\n\n{execution_log}\n"


def test_three_phase_canon_prompt_is_accepted() -> None:
    """ADR-025 RED/GREEN/COMMIT prompt must pass the live validator (issue #65)."""
    result = TemplateValidator().validate_prompt(_build_prompt(CANONICAL_3_PHASE))
    assert result.task_invocation_allowed, (
        "3-phase canon prompt was rejected — the live gate is still forcing the "
        f"legacy 5-phase contract (issue #65). Errors: {result.errors}"
    )


def test_legacy_five_phase_prompt_still_accepted() -> None:
    """Legacy v4 logs must keep validating for pre-2026-05-07 audit-log replay."""
    result = TemplateValidator().validate_prompt(_build_prompt(LEGACY_5_PHASE))
    assert result.task_invocation_allowed, (
        f"Legacy 5-phase prompt regressed — must stay valid. Errors: {result.errors}"
    )


def test_partial_legacy_phase_log_is_rejected() -> None:
    """A partial-legacy log (incomplete legacy set) is an anomaly, not a canon.

    PREPARE+GREEN+COMMIT lacks the complete legacy-only set, so auto-detect keeps
    the canonical 3-phase contract and the prompt is rejected for the missing RED
    phase — pinning the complete-set guard so the fix cannot silently accept it.
    """
    result = TemplateValidator().validate_prompt(
        _build_prompt(("PREPARE", "GREEN", "COMMIT"))
    )
    assert not result.task_invocation_allowed, (
        f"Partial-legacy phase log should be rejected. Errors: {result.errors}"
    )
