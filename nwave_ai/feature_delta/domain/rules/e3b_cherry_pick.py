"""E3b: CherryPickCheck rule — downstream row count >= upstream OR DDR-authorized."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from nwave_ai.feature_delta.domain.violations import ValidationViolation


if TYPE_CHECKING:
    from nwave_ai.feature_delta.domain.model import FeatureDeltaModel

# Wave order for upstream/downstream relationships.
_WAVE_ORDER = ("DISCOVER", "DISCUSS", "DESIGN", "DEVOPS", "DISTILL", "DELIVER")


def _wave_index(name: str) -> int:
    try:
        return _WAVE_ORDER.index(name.upper())
    except ValueError:
        return -1


def check(model: FeatureDeltaModel) -> tuple[ValidationViolation, ...]:
    """Check E3b: for each consecutive wave pair (DISCUSS→DESIGN only for v1.0),
    downstream must not drop rows without DDR ratification.

    A "cherry-pick" occurs when:
      - upstream wave has N commitment rows
      - downstream wave has M < N commitment rows
      - the downstream wave has no DDR entries authorizing removals

    When downstream has DDR entries (any), the removals are considered authorized.

    Returns a tuple of ValidationViolation objects (empty = clean).
    """
    violations: list[ValidationViolation] = []

    # Sort sections by canonical wave order.
    sorted_sections = sorted(
        model.sections,
        key=lambda s: _wave_index(s.name),
    )

    # Check each consecutive pair.
    for upstream, downstream in itertools.pairwise(sorted_sections):
        upstream_idx = _wave_index(upstream.name)
        downstream_idx = _wave_index(downstream.name)
        if upstream_idx < 0 or downstream_idx < 0:
            continue
        if downstream_idx <= upstream_idx:
            continue

        upstream_count = len(upstream.rows)
        downstream_count = len(downstream.rows)

        if downstream_count >= upstream_count:
            # All rows present or more — no cherry-pick.
            continue

        # Downstream has fewer rows.
        # If there are DDR entries in the downstream section, removals are authorized.
        if downstream.ddr_entries:
            continue

        # No DDR entries — each missing row is a violation.
        # Identify which upstream commitments are absent from downstream.
        downstream_commitments = {r.commitment.strip() for r in downstream.rows}
        for row in upstream.rows:
            commitment = row.commitment.strip()
            if not commitment:
                continue
            if commitment not in downstream_commitments:
                violations.append(
                    ValidationViolation(
                        rule="E3b",
                        severity="error",
                        file=model.feature_id,
                        line=1,
                        offender=commitment,
                        remediation="Add DDR entry OR restore row",
                    )
                )

    return tuple(violations)
