"""Root-only FS detection table -- plugin-skill-deliverable-type (DISTILL scaffold).

The full root-marker table (ADR-PST-002, DDD-4) exercised exhaustively through
the REAL detector (``deliverable_type_detector.detect_deliverable_type``) over a
real project tree on ``tmp_path``. Finite + enumerable -> ``@pytest.mark.parametrize``
(falsifier-gate), not property-based generation.

The named collision guard is its own assertion: a NESTED ``nWave/skills/``
directory (this very repo's shape) MUST resolve to ``application`` -- detection
inspects ROOT markers only and never recurses (Principle 12 bounded universe).

SKIPPED at module level so the suite stays green now; DELIVER unskips and
implements ``detect_deliverable_type`` until GREEN.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.des.acceptance.plugin_skill_deliverable_type.steps.composition import (
    build_production_composition,
)
from tests.des.acceptance.plugin_skill_deliverable_type.steps.domain_types import (
    DETECTION_TABLE,
    DetectionCase,
    ResolvedType,
    RootMarker,
)


@pytest.mark.parametrize(
    "case",
    DETECTION_TABLE,
    ids=[f"{c.root_marker.value}->{c.expected.value}" for c in DETECTION_TABLE],
)
def test_detection_table_row(
    case: DetectionCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each root-marker row resolves to its documented detected type.

    CONTRACT_SHAPE: unbounded-preservation
    """
    composition = build_production_composition(tmp_path, monkeypatch)
    composition.given_root_marker(case.root_marker)

    composition.detect_root_type()

    assert composition.last_detected_type is case.expected, case.note


def test_nested_skills_dir_never_triggers_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The collision guard: nested nWave/skills/ is application, never skill.

    This is the nwave-dev self-classification bug the SPIKE flagged (edge case 1):
    a repo that ships skills under a NESTED folder must not silently disable
    enforcement on itself.

    CONTRACT_SHAPE: unbounded-preservation
    """
    composition = build_production_composition(tmp_path, monkeypatch)
    composition.given_root_marker(RootMarker.NESTED_NWAVE_SKILLS)

    composition.detect_root_type()

    assert composition.last_detected_type is ResolvedType.APPLICATION


def test_detection_table_is_complete() -> None:
    """The data table covers every root-marker exactly once (C5a).

    CONTRACT_SHAPE: pure-function
    """
    seen = {c.root_marker for c in DETECTION_TABLE}
    assert len(seen) == len(DETECTION_TABLE) == len(RootMarker)
