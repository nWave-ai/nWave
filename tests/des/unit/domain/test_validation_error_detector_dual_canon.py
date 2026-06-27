"""Issue #65 (Fix C): ValidationErrorDetector phase-sequence detection must be
dual-canon aware.

``detect_phase_sequence_errors`` bound the valid sequence to the canonical
3-phase list unconditionally (``VALID_PHASE_SEQUENCE = schema.tdd_phases``), so a
legacy 5-phase step file had its PREPARE / RED_ACCEPTANCE / RED_UNIT phases
silently skipped by the ordering check — out-of-order legacy phases went
undetected. The detector now auto-detects the canon from the recorded phases
(legacy only when the complete legacy-only set {PREPARE, RED_ACCEPTANCE,
RED_UNIT} is present, otherwise canonical), mirroring the per-log dispatch in
ExecutionLogValidator._resolve_active_phases. Legacy step files stay valid for
audit replay.

Refs: https://github.com/nWave-ai/nWave/issues/65
"""

from __future__ import annotations

from des.domain.tdd_schema import CANONICAL_PHASES, LEGACY_PHASES
from des.domain.validation_error_detector import ValidationErrorDetector


def _cycle(*phase_names: str) -> dict:
    return {"phase_execution_log": [{"phase_name": name} for name in phase_names]}


def test_out_of_order_legacy_phases_are_detected() -> None:
    """Legacy step with RED_UNIT before RED_ACCEPTANCE must be flagged (#65 Fix C).

    The complete legacy-only set is present, so the detector validates against the
    legacy 5-phase sequence. Before the fix these phases were skipped and the
    mis-ordering went unreported.
    """
    detector = ValidationErrorDetector()
    cycle = _cycle("PREPARE", "RED_UNIT", "RED_ACCEPTANCE", "GREEN", "COMMIT")
    errors = detector.detect_phase_sequence_errors(cycle)
    assert errors, "out-of-order legacy phases should be flagged (issue #65 Fix C)"


def test_in_order_legacy_phases_are_clean() -> None:
    """A correctly-ordered legacy 5-phase step must not false-positive."""
    detector = ValidationErrorDetector()
    errors = detector.detect_phase_sequence_errors(_cycle(*LEGACY_PHASES))
    assert errors == [], f"in-order legacy step must be clean: {errors}"


def test_in_order_canonical_phases_are_clean() -> None:
    """A correctly-ordered 3-phase step must not false-positive."""
    detector = ValidationErrorDetector()
    errors = detector.detect_phase_sequence_errors(_cycle(*CANONICAL_PHASES))
    assert errors == [], f"in-order 3-phase step must be clean: {errors}"


def test_out_of_order_canonical_phases_are_detected() -> None:
    """Guard: out-of-order canonical phases are still flagged."""
    detector = ValidationErrorDetector()
    errors = detector.detect_phase_sequence_errors(_cycle("GREEN", "RED", "COMMIT"))
    assert errors, "out-of-order canonical phases should be flagged"
