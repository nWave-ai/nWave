"""Unit tests for E4 v1.0 and v1.1 SubstantiveImpact rules.

Test Budget:
  v1.0: 3 distinct behaviors x 2 = 6 max. Using 3 tests.
  v1.1: 3 distinct behaviors x 2 = 6 max. Using 3 tests.

Port-to-port: check_v1_0() and check_v1_1() pure domain functions ARE the driving ports.
"""

from __future__ import annotations

import pytest
from nwave_ai.feature_delta.domain.model import (
    CommitmentRow,
    FeatureDeltaModel,
    WaveSection,
)
from nwave_ai.feature_delta.domain.rules.e4_substantive_impact import (
    check_v1_0,
    check_v1_1,
)


def _model_with_impact(impact: str) -> FeatureDeltaModel:
    row = CommitmentRow(
        origin="DISCUSS#row1",
        commitment="some commitment",
        ddr="n/a",
        impact=impact,
    )
    section = WaveSection(name="DESIGN", rows=(row,), ddr_entries=())
    return FeatureDeltaModel(feature_id="test", sections=(section,))


_CONSEQUENCE_VERBS: tuple[str, ...] = (
    "ratifies",
    "preserves",
    "removes",
    "restricts",
    "deprecates",
    "mandates",
    "blocks",
    "enforces",
    "requires",
    "gates",
)


# Behavior 1: consequence verb in impact passes E4 (AC-1)
def test_consequence_verb_passes_e4() -> None:
    model = _model_with_impact("DDD-1 ratifies framework-agnostic relaxation")
    violations = check_v1_0(model, _CONSEQUENCE_VERBS)
    assert violations == ()


# Behavior 2: short/vague impact without verb fails E4 (AC-2)
@pytest.mark.parametrize(
    "impact",
    ["ok", "done", "fine", "yes"],
)
def test_short_vague_impact_fails_e4(impact: str) -> None:
    model = _model_with_impact(impact)
    violations = check_v1_0(model, _CONSEQUENCE_VERBS)
    assert len(violations) == 1
    assert violations[0].rule == "E4"


# Behavior 3: word-count >=10 passes E4 regardless of verb (v1.0 conceded gap, AC-3)
def test_word_padding_bypass_passes_e4_v1_0() -> None:
    impact = "the the the the the the the the the the"  # 10 vacuous words, no verb
    model = _model_with_impact(impact)
    violations = check_v1_0(model, _CONSEQUENCE_VERBS)
    assert violations == (), (
        "v1.0 conceded gap: word-padding bypasses the heuristic — closed by US-12 v1.1"
    )


# ---------------------------------------------------------------------------
# E4 v1.1 unit tests (US-12 R2 — structural citation required)
# ---------------------------------------------------------------------------


# v1.1 Behavior 1: DDD citation in impact passes E4 v1.1 (AC-1)
def test_ddd_citation_passes_e4_v1_1() -> None:
    model = _model_with_impact("DDD-1 ratifies framework-agnostic relaxation")
    violations = check_v1_1(model, _CONSEQUENCE_VERBS)
    assert violations == ()


# v1.1 Behavior 2: word-padding without DDD or row citation fails E4 v1.1 (AC-2)
def test_word_padding_without_citation_fails_e4_v1_1() -> None:
    impact = "the the the the the the the the the the"  # 10 words, no citation
    model = _model_with_impact(impact)
    violations = check_v1_1(model, _CONSEQUENCE_VERBS)
    assert len(violations) == 1
    assert violations[0].rule == "E4"


# v1.1 Behavior 3: row# citation in impact passes E4 v1.1 (AC-3)
def test_row_citation_passes_e4_v1_1() -> None:
    model = _model_with_impact("preserves DISCUSS#row3 verbatim")
    violations = check_v1_1(model, _CONSEQUENCE_VERBS)
    assert violations == ()
