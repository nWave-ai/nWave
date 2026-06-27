"""Regression lock: E4 v1.0 word-padding bypass is a CONCEDED gap.

US-09 AC-3 / US-09 AC-4: documents and regression-locks the known v1.0
limitation that word-padding (10+ words with no consequence verb) bypasses
the E4 heuristic.

This test MUST remain GREEN as long as v1.0 is active.
When US-12 v1.1 ships, this test may be retired or updated to assert
the new behavior under check_v1_1().
"""

from __future__ import annotations

from nwave_ai.feature_delta.domain.model import (
    CommitmentRow,
    FeatureDeltaModel,
    WaveSection,
)
from nwave_ai.feature_delta.domain.rules.e4_substantive_impact import check_v1_0


# v1.0 conceded gap: closed by US-12 v1.1 (R2 row-citation requirement)
_V1_0_BYPASS_DOCUMENTED = "US-12 v1.1 closes this gap via R2 row-citation requirement"

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


def _model_with_impact(impact: str) -> FeatureDeltaModel:
    row = CommitmentRow(
        origin="DISCUSS#row1",
        commitment="some commitment",
        ddr="n/a",
        impact=impact,
    )
    section = WaveSection(name="DESIGN", rows=(row,), ddr_entries=())
    return FeatureDeltaModel(feature_id="test", sections=(section,))


def test_word_padding_bypass_is_conceded_v1_0_gap() -> None:
    """
    REGRESSION LOCK: word-padding bypasses E4 v1.0.

    v1.0 conceded gap documented in:
    - e4_substantive_impact.py module docstring
    - US-09 AC-3 acceptance scenario
    - This regression lock

    Closure: US-12 v1.1 (R2 row-citation requirement).
    """
    padded_impacts = [
        "the the the the the the the the the the",  # 10 identical filler words
        "a b c d e f g h i j",  # 10 single-char words, no verb
        "one two three four five six seven eight nine ten",  # 10 ordinals, no verb
    ]
    for impact in padded_impacts:
        model = _model_with_impact(impact)
        violations = check_v1_0(model, _CONSEQUENCE_VERBS)
        assert violations == (), (
            f"v1.0 conceded gap broken: '{impact}' should pass by word-count. "
            f"If this fails, check whether v1.1 was prematurely activated. "
            f"Documented closure: {_V1_0_BYPASS_DOCUMENTED}"
        )
