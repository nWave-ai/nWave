"""Deliverable-type enforcement matrix -- plugin-skill-deliverable-type (DISTILL scaffold).

The full Cartesian over (step-id present x explicit marker x deliverable type)
exercised exhaustively through the REAL enforcement driving port
(``PreToolUseService.validate``). The input domain is finite + enumerable
(StepIdPresence x Marker x DeliverableType), so per the falsifier-gate this is
``@pytest.mark.parametrize`` -- NOT property-based generation (a typo'd type is a
known list member; shrinking buys nothing).

Seeds from the SPIKE 8/8 behaviour matrix and adds the two fail-safe obligation
rows (ADR-PST-001 obligation 1): a mis-spelled type and a mis-cased type both
stay ENFORCED -- the closed exempt set makes "a typo silently exempts"
non-representable. Each row drives the production policy through the real service.

SKIPPED at module level so the suite stays green now; DELIVER unskips and
implements the ``DesEnforcementPolicy`` exempt-type short-circuit until GREEN.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.des.acceptance.plugin_skill_deliverable_type.steps.composition import (
    build_production_composition,
)
from tests.des.acceptance.plugin_skill_deliverable_type.steps.domain_types import (
    ENFORCEMENT_MATRIX,
    EXEMPT_DELIVERABLE_TYPES,
    DeliverableType,
    DispatchEnvelope,
    EnforcementCase,
    GateOutcome,
    Marker,
    StepIdPresence,
)


@pytest.mark.parametrize(
    "case",
    ENFORCEMENT_MATRIX,
    ids=[
        f"{c.step_id.value}-x-{c.marker.value}-x-{c.deliverable.value}->{c.expected.value}"
        for c in ENFORCEMENT_MATRIX
    ],
)
def test_enforcement_matrix_row(
    case: EnforcementCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each matrix row resolves to its documented gate outcome through the port.

    CONTRACT_SHAPE: bounded-change
    """
    composition = build_production_composition(tmp_path, monkeypatch)

    composition.dispatch(
        DispatchEnvelope(
            step_id=case.step_id,
            marker=case.marker,
            deliverable=case.deliverable,
        )
    )

    assert composition.last_gate_outcome is case.expected, case.note


def test_type_carried_exemption_leaves_no_dispatch_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plugin dispatch is exempt WITHOUT carrying a per-dispatch exempt marker.

    This is the issue's core promise: the practitioner stops hand-stamping
    ``DES-ENFORCEMENT : exempt`` on every plugin/skill dispatch. The exemption
    must be observably TYPE-carried, not marker-carried.

    CONTRACT_SHAPE: bounded-change
    """
    composition = build_production_composition(tmp_path, monkeypatch)

    composition.dispatch(
        DispatchEnvelope(
            step_id=StepIdPresence.HAS_STEP_ID,
            marker=Marker.NONE,
            deliverable=DeliverableType.PLUGIN,
        )
    )

    universe = composition.capture_universe()
    assert universe["gate.outcome"] is GateOutcome.EXEMPT
    assert universe["gate.dispatch_carries_exempt_marker"] is False


def test_exempt_set_is_closed_and_excludes_application() -> None:
    """The exempt set is exactly {plugin, skill} -- application is NOT in it (C6c).

    Belt assertion on the closed allow-list: any non-exempt deliverable (incl.
    APPLICATION, UNSET, TYPO, MIXEDCASE) must stay outside the exempt set so the
    fail-safe (ADR-PST-001) is structural, not incidental.

    CONTRACT_SHAPE: pure-function
    """
    assert (
        frozenset({DeliverableType.PLUGIN, DeliverableType.SKILL})
        == EXEMPT_DELIVERABLE_TYPES
    )
    non_exempt = {
        DeliverableType.APPLICATION,
        DeliverableType.UNSET,
        DeliverableType.TYPO,
        DeliverableType.MIXEDCASE,
    }
    assert non_exempt.isdisjoint(EXEMPT_DELIVERABLE_TYPES)
