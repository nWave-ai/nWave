"""Unit tests for E3b-row pairing bijection rule.

Test Budget: 3 behaviors * 2 = 6 max unit tests.
Driving port: check_row_pairing() pure domain function.
"""

from __future__ import annotations

from nwave_ai.feature_delta.domain.model import (
    CommitmentRow,
    FeatureDeltaModel,
    WaveSection,
)
from nwave_ai.feature_delta.domain.rules.e3b_row_pairing import check_row_pairing


def _make_model(
    discuss_rows: list[tuple[str, str]],
    design_rows: list[tuple[str, str]],
    design_ddr_entries: tuple = (),
) -> FeatureDeltaModel:
    """Build a minimal FeatureDeltaModel for testing."""
    discuss = WaveSection(
        name="DISCUSS",
        rows=tuple(
            CommitmentRow(origin=origin, commitment=commit, ddr="n/a", impact="impact")
            for origin, commit in discuss_rows
        ),
        ddr_entries=(),
    )
    design = WaveSection(
        name="DESIGN",
        rows=tuple(
            CommitmentRow(origin=origin, commitment=commit, ddr="n/a", impact="impact")
            for origin, commit in design_rows
        ),
        ddr_entries=design_ddr_entries,
    )
    return FeatureDeltaModel(
        feature_id="test",
        sections=(discuss, design),
    )


def test_complete_bijection_produces_no_violations() -> None:
    """Behavior 1: all upstream rows have downstream successors — clean."""
    model = _make_model(
        discuss_rows=[
            ("n/a", "commitment-1"),
            ("n/a", "commitment-2"),
            ("n/a", "commitment-3"),
        ],
        design_rows=[
            ("DISCUSS#row1", "impl-1"),
            ("DISCUSS#row2", "impl-2"),
            ("DISCUSS#row3", "impl-3"),
        ],
    )
    violations = check_row_pairing(model)
    assert violations == ()


def test_unpaired_upstream_rows_reported_as_orphans() -> None:
    """Behavior 2: upstream rows with no downstream citation → orphan violation per row."""
    model = _make_model(
        discuss_rows=[
            ("n/a", "commitment-1"),
            ("n/a", "commitment-2"),
            ("n/a", "commitment-3"),
        ],
        design_rows=[
            ("DISCUSS#row1", "impl-1"),
            # rows 2 and 3 have no downstream pairing
        ],
    )
    violations = check_row_pairing(model)
    orphan_offenders = {v.offender for v in violations}
    assert "DISCUSS#row2" in orphan_offenders
    assert "DISCUSS#row3" in orphan_offenders
    assert all(v.rule == "E3b-row" for v in violations)


def test_multi_pair_one_upstream_many_downstream_passes() -> None:
    """Behavior 3: one upstream row cited by multiple downstream rows is valid."""
    model = _make_model(
        discuss_rows=[
            ("n/a", "commitment-1"),
        ],
        design_rows=[
            ("DISCUSS#row1", "impl-1a"),
            ("DISCUSS#row1", "impl-1b"),
        ],
    )
    violations = check_row_pairing(model)
    assert violations == ()
