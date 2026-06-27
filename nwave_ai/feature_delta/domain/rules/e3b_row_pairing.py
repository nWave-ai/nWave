"""E3b-row: Row-level bijection check (v1.1 R1).

Each downstream commitment row carries an Origin column value like
'DISCUSS#row1' that points to an upstream row by 1-based index.

Bijection rule:
- Every upstream row must have at least one downstream successor (paired
  via Origin) OR be authorized via a DDR entry in the downstream section.
- Multi-pair (1 upstream → N downstream) is valid (refinement).
- Orphan downstream rows (Origin pointing to non-existent upstream index)
  are also reported as violations.
"""

from __future__ import annotations

import itertools
import re
from typing import TYPE_CHECKING

from nwave_ai.feature_delta.domain.violations import ValidationViolation


if TYPE_CHECKING:
    from nwave_ai.feature_delta.domain.model import FeatureDeltaModel

# Wave order for upstream/downstream relationships.
_WAVE_ORDER = ("DISCOVER", "DISCUSS", "DESIGN", "DEVOPS", "DISTILL", "DELIVER")

# Pattern: WAVE#rowN  (e.g. DISCUSS#row1, DESIGN#row3)
_ORIGIN_PATTERN = re.compile(r"^([A-Z]+)#row(\d+)$")


def _wave_index(name: str) -> int:
    try:
        return _WAVE_ORDER.index(name.upper())
    except ValueError:
        return -1


def check_row_pairing(model: FeatureDeltaModel) -> tuple[ValidationViolation, ...]:
    """Check E3b-row: bijection between upstream and downstream rows.

    For each consecutive wave pair, every upstream row must be cited by
    at least one downstream row via its Origin column, or authorized by
    a DDR entry in the downstream section.

    Returns a tuple of ValidationViolation objects (empty = clean).
    """
    violations: list[ValidationViolation] = []

    sorted_sections = sorted(
        model.sections,
        key=lambda s: _wave_index(s.name),
    )

    for upstream, downstream in itertools.pairwise(sorted_sections):
        upstream_idx = _wave_index(upstream.name)
        downstream_idx = _wave_index(downstream.name)
        if upstream_idx < 0 or downstream_idx < 0:
            continue
        if downstream_idx <= upstream_idx:
            continue

        upstream_wave = upstream.name.upper()
        upstream_row_count = len(upstream.rows)

        if upstream_row_count == 0:
            continue

        # Build set of upstream row IDs that are cited by downstream rows.
        cited_upstream_ids: set[str] = set()
        for row in downstream.rows:
            origin = row.origin.strip() if row.origin else ""
            match = _ORIGIN_PATTERN.match(origin)
            if match:
                wave_name = match.group(1).upper()
                row_num = int(match.group(2))
                if wave_name == upstream_wave:
                    cited_upstream_ids.add(f"{upstream_wave}#row{row_num}")

        # If downstream has DDR entries, removals are considered authorized.
        ddr_authorized = bool(downstream.ddr_entries)

        # Check each upstream row.
        for row_index, _row in enumerate(upstream.rows, start=1):
            row_id = f"{upstream_wave}#row{row_index}"
            if row_id not in cited_upstream_ids and not ddr_authorized:
                violations.append(
                    ValidationViolation(
                        rule="E3b-row",
                        severity="error",
                        file=model.feature_id,
                        line=row_index,
                        offender=row_id,
                        remediation=(
                            f"Add 'Origin: {row_id}' to a downstream row in "
                            f"{downstream.name}, or add a DDR entry authorizing removal."
                        ),
                    )
                )

    return tuple(violations)
