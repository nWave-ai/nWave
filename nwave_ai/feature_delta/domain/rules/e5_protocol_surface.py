"""E5: ProtocolSurface rule — detects silent erosion of protocol-surface verbs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwave_ai.feature_delta.domain.violations import ValidationViolation


if TYPE_CHECKING:
    from nwave_ai.feature_delta.domain.model import FeatureDeltaModel


def check(
    model: FeatureDeltaModel, patterns: tuple[str, ...]
) -> tuple[ValidationViolation, ...]:
    """
    Check that protocol-surface verbs present in DISCUSS commitments
    are still present in DESIGN commitments (or ratified by a DDR entry).

    For each pattern in `patterns`, if any DISCUSS commitment contains it
    but no DESIGN commitment contains it AND no DESIGN row has a non-empty
    DDR ratification, it is a violation.

    Returns a tuple of ValidationViolation objects (empty = clean).
    """
    if not patterns:
        return ()

    discuss_section = next((s for s in model.sections if s.name == "DISCUSS"), None)
    design_section = next((s for s in model.sections if s.name == "DESIGN"), None)

    if discuss_section is None or design_section is None:
        return ()

    discuss_text = " ".join(r.commitment for r in discuss_section.rows)
    design_text = " ".join(r.commitment for r in design_section.rows)

    # Collect DDR ratifications: any DESIGN row with a non-empty, non-placeholder DDR cell.
    ratified_ddrs = {
        r.ddr.strip()
        for r in design_section.rows
        if r.ddr.strip() and r.ddr.strip().lower() not in ("n/a", "(none)", "none", "")
    }

    violations: list[ValidationViolation] = []
    for pattern in patterns:
        if pattern.upper() not in discuss_text.upper():
            continue
        if pattern.upper() in design_text.upper():
            continue
        # Pattern present in DISCUSS but missing from DESIGN.
        # Check if any DDR entry ratifies the downgrade.
        if ratified_ddrs:
            continue
        line_hint = 1  # Line numbers not tracked in v1; use 1 as sentinel.
        offender_file = model.feature_id
        violations.append(
            ValidationViolation(
                rule="E5",
                severity="error",
                file=offender_file,
                line=line_hint,
                offender=pattern,
                remediation=(
                    f"Add a DDR entry ratifying the removal of '{pattern}' "
                    f"or restore the commitment in DESIGN."
                ),
            )
        )

    return tuple(violations)
