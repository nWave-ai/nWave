"""E4: SubstantiveImpact rule v1.0 and v1.1.

v1.0 logic: for each DESIGN CommitmentRow, examine the Impact column.
PASS if word_count(impact) >= 10 OR impact contains >= 1 word from verbs.
FAIL otherwise — impact too vague.

v1.1 logic (additive over v1.0): Impact MUST additionally contain a
structural citation: DDR-\\d+ OR row#\\d+ (case-insensitive for row#).
Pure prose without citation fails even if v1.0 word-count/verb passes.
Closes stressor S1: word-padding bypass empirical from spdd-bench.

The decision-record citation is canonically DDR-N; the legacy DDD-N form is
still accepted for backward compatibility (issue #50).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from nwave_ai.feature_delta.domain.violations import ValidationViolation


if TYPE_CHECKING:
    from nwave_ai.feature_delta.domain.model import FeatureDeltaModel

# DDR-N canonical; legacy DDD-N accepted (issue #50).
_CITATION_PATTERN = re.compile(r"DD[DR]-\d+|row#\d+|#row\d+", re.IGNORECASE)


def check_v1_0(
    model: FeatureDeltaModel, verbs: tuple[str, ...]
) -> tuple[ValidationViolation, ...]:
    """
    E4 v1.0: PASS if impact word-count >= 10 OR contains a consequence verb.

    v1.0 conceded gap: word-padding bypasses word-count threshold.
    Closed by US-12 v1.1 (R2).
    """
    design_section = next((s for s in model.sections if s.name == "DESIGN"), None)
    if design_section is None:
        return ()

    violations: list[ValidationViolation] = []
    for row_index, row in enumerate(design_section.rows, start=1):
        impact = row.impact.strip()
        if _passes_v1_0(impact, verbs):
            continue
        violations.append(
            ValidationViolation(
                rule="E4",
                severity="error",
                file=model.feature_id,
                line=row_index,
                offender=impact[:80] if impact else "(empty)",
                remediation=(
                    "Provide an Impact value with >= 10 words OR a consequence verb "
                    "(e.g. ratifies, preserves, removes, restricts, deprecates). "
                    "v1.1 will additionally require a DDR-N or row citation."
                ),
            )
        )

    return tuple(violations)


def check_v1_1(
    model: FeatureDeltaModel, verbs: tuple[str, ...]
) -> tuple[ValidationViolation, ...]:
    """
    E4 v1.1: PASS if v1.0 baseline passes AND impact contains DDR-N or row#N citation.

    Closes stressor S1: word-padding bypass blocked by requiring a structural reference.
    US-12 AC-1: DDR-\\d+ citation passes (legacy DDD-\\d+ also accepted).
    US-12 AC-2: word-padding without citation fails.
    US-12 AC-3: row#\\d+ citation passes.
    """
    design_section = next((s for s in model.sections if s.name == "DESIGN"), None)
    if design_section is None:
        return ()

    violations: list[ValidationViolation] = []
    for row_index, row in enumerate(design_section.rows, start=1):
        impact = row.impact.strip()
        v1_0_passes = _passes_v1_0(impact, verbs)
        has_citation = bool(_CITATION_PATTERN.search(impact))
        if v1_0_passes and has_citation:
            continue
        violations.append(
            ValidationViolation(
                rule="E4",
                severity="error",
                file=model.feature_id,
                line=row_index,
                offender=impact[:80] if impact else "(empty)",
                remediation=(
                    "E4 v1.1 requires a structural citation: DDR-N or row#N. "
                    "Add a DDR entry reference (e.g. DDR-1) or a row citation "
                    "(e.g. DISCUSS#row3 or row#3) in the Impact column."
                ),
            )
        )

    return tuple(violations)


def _passes_v1_0(impact: str, verbs: tuple[str, ...]) -> bool:
    words = impact.split()
    if len(words) >= 10:
        return True
    impact_lower = impact.lower()
    return any(verb.lower() in impact_lower for verb in verbs)
