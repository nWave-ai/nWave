"""Activation-resolution truth table — project-activation-gating (DISTILL scaffold).

The full 9-row truth table (ADR-AG-002) exercised exhaustively. The input
domain is finite + enumerable (marker ∈ {enabled, disabled, absent} x mode ∈
{opt-in, all, absent/corrupt}), so per the falsifier-gate this is
``@pytest.mark.parametrize`` — NOT property-based generation. Each row drives
the real pure ``resolve_activation`` policy fed by the real ``DESConfig`` reader
through the production composition root.

SKIPPED at module level so the suite stays green now; DELIVER unskips and
implements ``resolve_activation`` + the ``DESConfig`` extension until GREEN.

Note: the missing/corrupt-global-config rows (ABSENT, CORRUPT) collapse to the
fresh-install ``opt-in`` default — both are exercised explicitly (C6 robustness).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.des.acceptance.activation_gating.steps.composition import (
    ActivationGatingComposition,
)
from tests.des.acceptance.activation_gating.steps.domain_types import (
    TRUTH_TABLE,
    Activation,
    ResolutionCase,
)


def _build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> ActivationGatingComposition:
    project_root = tmp_path / "project"
    home_dir = tmp_path / "home"
    project_root.mkdir(parents=True, exist_ok=True)
    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))
    return ActivationGatingComposition(project_root=project_root, home_dir=home_dir)


@pytest.mark.parametrize(
    "case",
    TRUTH_TABLE,
    ids=[f"{c.marker.value}-x-{c.mode.value}->{c.expected.value}" for c in TRUTH_TABLE],
)
def test_activation_truth_table_row(
    case: ResolutionCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each of the 9 truth-table rows resolves to its documented verdict."""
    composition = _build(tmp_path, monkeypatch)
    composition.given_global_mode(case.mode)
    composition.given_marker(case.marker)

    composition.resolve_activation()

    assert composition.last_resolution is case.expected, case.note


def test_truth_table_is_complete() -> None:
    """The data table covers every markerxmode combination exactly once (C5a)."""
    seen = {(c.marker, c.mode) for c in TRUTH_TABLE}
    assert len(seen) == len(TRUTH_TABLE) == 9
    assert {c.expected for c in TRUTH_TABLE} == {Activation.ACTIVE, Activation.INACTIVE}
