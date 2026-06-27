"""Unit tests for E1 (SectionPresent) and E2 (ColumnsPresent) rules.

Test Budget: 3 distinct behaviors x 2 = 6 unit tests max.

Behaviors:
  B1 — E1 returns empty tuple on well-formed wave headings
  B2 — E1 returns violation with did_you_mean on malformed heading
  B3 — E2 returns violation when commitments table missing a required column
"""

from __future__ import annotations

import pytest
from nwave_ai.feature_delta.domain.rules import e1_section_present, e2_columns_present


# ---------------------------------------------------------------------------
# B1 — E1 clean on well-formed document
# ---------------------------------------------------------------------------

WELLFORMED_TEXT = (
    "# my feature\n\n"
    "## Wave: DISCUSS / [REF] Some Section\n\n"
    "### [REF] Inherited commitments\n\n"
    "| Origin | Commitment | DDD | Impact |\n"
    "|--------|------------|-----|--------|\n"
    "| n/a | POST /api/login | n/a | baseline |\n\n"
    "## Wave: DESIGN / [REF] Some Section\n\n"
    "### [REF] Inherited commitments\n\n"
    "| Origin | Commitment | DDD | Impact |\n"
    "|--------|------------|-----|--------|\n"
    "| DISCUSS#row1 | POST /api/login backed by Flask | n/a | preserves |\n"
)


def test_e1_returns_empty_on_well_formed_document():
    violations = e1_section_present.check(
        WELLFORMED_TEXT, "docs/feature/test/feature-delta.md"
    )
    assert violations == ()


# ---------------------------------------------------------------------------
# B2 — E1 reports typo with did_you_mean
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "typo_heading, expected_suggestion",
    [
        ("## Wave : DISCUSS", "## Wave: DISCUSS"),
        ("## Wave: DISCSS", "## Wave: DISCUSS"),
    ],
)
def test_e1_returns_violation_with_did_you_mean_on_typo(
    typo_heading, expected_suggestion
):
    text = f"# feature\n\n{typo_heading}\n\nsome content\n"
    violations = e1_section_present.check(text, "docs/feature/test/feature-delta.md")
    assert len(violations) >= 1
    v = violations[0]
    assert v.rule == "E1"
    assert v.did_you_mean is not None
    assert "DISCUSS" in v.did_you_mean


# ---------------------------------------------------------------------------
# B3 — E2 reports missing column in commitments table
# ---------------------------------------------------------------------------


MISSING_DDD_COL_TEXT = (
    "# feature\n\n"
    "## Wave: DESIGN / [REF] Inherited commitments\n\n"
    "### [REF] Inherited commitments\n\n"
    "| Origin | Commitment | Impact |\n"
    "|--------|------------|--------|\n"
    "| n/a | some commitment | some impact |\n"
)


def test_e2_returns_violation_on_missing_ddd_column():
    violations = e2_columns_present.check(
        MISSING_DDD_COL_TEXT, "docs/feature/test/feature-delta.md"
    )
    assert len(violations) >= 1
    v = violations[0]
    assert v.rule == "E2"
    assert "DDR" in v.offender or "DDR" in v.remediation
