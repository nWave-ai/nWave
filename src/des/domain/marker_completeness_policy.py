"""Marker Completeness Policy - validates DES marker completeness.

Pure domain policy that ensures when DES-VALIDATION is present,
the required identifiers (DES-PROJECT-ID, DES-STEP-ID) are also present.
Prevents tasks from proceeding with null identifiers that break
downstream services (SubagentStop cannot locate execution log).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from des.domain.des_marker_parser import DesMarkers


@dataclass(frozen=True)
class CompletenessResult:
    """Result of a marker completeness validation.

    Attributes:
        is_valid: True if markers are complete
        reason: Block reason if invalid, None otherwise
        recovery_suggestions: Actionable steps to fix the block
    """

    is_valid: bool
    reason: str | None = None
    recovery_suggestions: list[str] = field(default_factory=list)


class MarkerCompletenessPolicy:
    """Validates that DES markers are complete when present.

    Business rules:
    1. Non-DES tasks always valid (no markers to check)
    2. DES tasks require DES-PROJECT-ID
    3. DES tasks require DES-STEP-ID (unless orchestrator mode)
    """

    def validate(self, markers: DesMarkers) -> CompletenessResult:
        """Validate marker completeness."""
        if not markers.is_des_task:
            return CompletenessResult(is_valid=True)

        missing = []
        if not markers.project_id:
            missing.append("DES-PROJECT-ID")
        if not markers.step_id and not markers.is_orchestrator_mode:
            missing.append("DES-STEP-ID")

        if not missing:
            return CompletenessResult(is_valid=True)

        return CompletenessResult(
            is_valid=False,
            reason=f"DES_MARKERS_INCOMPLETE: {', '.join(missing)} missing",
            recovery_suggestions=[
                "Add the missing DES markers to the Task prompt:",
                "<!-- DES-PROJECT-ID : {project-id} -->",
                "<!-- DES-STEP-ID : {step-id} -->",
                "Read ~/.claude/commands/nw/execute.md for the full template.",
            ],
        )
