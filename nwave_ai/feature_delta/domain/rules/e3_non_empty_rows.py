"""E3: NonEmptyRows rule — every CommitmentRow must have non-empty cells."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwave_ai.feature_delta.domain.violations import ValidationViolation


if TYPE_CHECKING:
    from nwave_ai.feature_delta.domain.model import FeatureDeltaModel

_REQUIRED_FIELDS = ("origin", "commitment", "ddr", "impact")
_FIELD_LABELS = {
    "origin": "Origin",
    "commitment": "Commitment",
    "ddr": "DDR",
    "impact": "Impact",
}


def check(model: FeatureDeltaModel) -> tuple[ValidationViolation, ...]:
    """Check E3 rule: every CommitmentRow must have non-empty cells in all 4 columns.

    Returns a tuple of ValidationViolation objects (empty = clean).
    """
    violations: list[ValidationViolation] = []

    for section in model.sections:
        for row_index, row in enumerate(section.rows, start=1):
            for field in _REQUIRED_FIELDS:
                value = getattr(row, field)
                if not value or not value.strip():
                    label = _FIELD_LABELS[field]
                    violations.append(
                        ValidationViolation(
                            rule="E3",
                            severity="error",
                            file=model.feature_id,
                            line=row_index,
                            offender=f"[{section.name}] row {row_index}: empty '{label}' cell",
                            remediation=(
                                f"Fill the '{label}' column in "
                                f"{section.name} row {row_index}."
                            ),
                        )
                    )
    return tuple(violations)
