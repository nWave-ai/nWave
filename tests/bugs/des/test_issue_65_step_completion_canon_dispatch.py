"""Regression guard (issue #65, downstream): StepCompletionValidator dispatches
per-log between the v5 3-phase canon and the v4 legacy 5-phase contract.

The PreToolUse *prompt* gate is already guarded by
``tests/bugs/des/test_issue_65_deliver_3phase_prompt.py``. This guard covers the
DOWNSTREAM step-completion stage: ``StepCompletionValidator.validate`` must accept
a v5 RED/GREEN/COMMIT step (and must NOT demand the legacy-only phases), while a
v4 PREPARE/RED_ACCEPTANCE/RED_UNIT/GREEN/COMMIT step still validates for
audit-log replay. Pins ``_active_phases_for_events`` per-log dispatch
(``src/des/domain/step_completion_validator.py``) so a future change cannot
silently re-break the "passes prompt, fails step-completion" scenario #65 feared.

Refs: https://github.com/nWave-ai/nWave/issues/65 ; ADR-025 (2026-05-07).
"""

from __future__ import annotations

from des.domain.phase_event import PhaseEvent
from des.domain.step_completion_validator import StepCompletionValidator
from des.domain.tdd_schema import TDDSchemaLoader


CANONICAL_3_PHASE = ("RED", "GREEN", "COMMIT")
LEGACY_5_PHASE = ("PREPARE", "RED_ACCEPTANCE", "RED_UNIT", "GREEN", "COMMIT")
LEGACY_ONLY = ("PREPARE", "RED_ACCEPTANCE", "RED_UNIT")


def _events(phases: tuple[str, ...], step_id: str = "01-01") -> list[PhaseEvent]:
    """A complete EXECUTED/PASS event stream for *phases* (single step)."""
    return [
        PhaseEvent(
            step_id=step_id,
            phase_name=phase,
            status="EXECUTED",
            outcome="PASS",
            timestamp=f"2026-06-17T10:00:{idx:02d}Z",
        )
        for idx, phase in enumerate(phases)
    ]


def _validator() -> StepCompletionValidator:
    """Validator wired with the production-loaded TDD schema (real composition)."""
    return StepCompletionValidator(TDDSchemaLoader().load())


def test_v5_three_phase_step_is_valid() -> None:
    """A v5 RED/GREEN/COMMIT step passes step-completion validation."""
    result = _validator().validate(_events(CANONICAL_3_PHASE))
    assert result.is_valid, (
        "A v5 3-phase (RED/GREEN/COMMIT) step was rejected by step-completion "
        f"validation (issue #65 downstream). errors={result.error_messages}"
    )


def test_v5_three_phase_step_not_rejected_for_missing_legacy_phases() -> None:
    """Dispatch proof: the 3-phase log routes to the canonical set, so the
    legacy-only phases (PREPARE/RED_ACCEPTANCE/RED_UNIT) are NOT demanded.

    Guards against a regression to a hardcoded 5-phase required set, which would
    charge a clean v5 step with "missing PREPARE/RED_ACCEPTANCE/RED_UNIT".
    """
    result = _validator().validate(_events(CANONICAL_3_PHASE))
    assert all(phase not in result.missing_phases for phase in LEGACY_ONLY), (
        "v5 step was charged with missing legacy phases — "
        "_active_phases_for_events is not dispatching per-log. "
        f"missing={result.missing_phases}"
    )


def test_v4_legacy_five_phase_step_still_valid() -> None:
    """Backward-compat: a complete legacy 5-phase step validates (audit replay)."""
    result = _validator().validate(_events(LEGACY_5_PHASE))
    assert result.is_valid, (
        "Legacy v4 5-phase step regressed in step-completion validation. "
        f"errors={result.error_messages}"
    )
