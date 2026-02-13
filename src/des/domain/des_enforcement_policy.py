"""DES Enforcement Policy - step-id based enforcement rule.

Pure domain policy following MaxTurnsPolicy pattern.
Every Task prompt containing a step-id pattern (\\d{2}-\\d{2}) without DES
markers gets blocked. This closes the bypass where the orchestrator delegates
via Task but forgets DES markers.

The step-id pattern is the single structural invariant: if you mention a step ID,
you are doing step execution work that requires DES monitoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EnforcementResult:
    """Result of a DES enforcement policy check.

    Attributes:
        is_enforced: True if the prompt should be blocked
        reason: Block reason if enforced, None otherwise
        recovery_suggestions: Actionable steps to fix the block
    """

    is_enforced: bool
    reason: str | None = None
    recovery_suggestions: list[str] = field(default_factory=list)


class DesEnforcementPolicy:
    """Enforces DES markers on Task prompts that reference step IDs.

    Business rule: If a prompt contains a step-id pattern (\\d{2}-\\d{2})
    but lacks DES markers, it must be blocked. Step execution requires
    DES monitoring.
    """

    # Negative lookbehind prevents matching date substrings like "2026-02-09"
    STEP_ID_PATTERN = re.compile(r"(?<!\d{4}-)\b\d{2}-\d{2}\b")
    DES_MARKER = "DES-VALIDATION : required"
    EXEMPT_MARKER = "DES-ENFORCEMENT : exempt"

    ENFORCED_REASON = (
        "DES_MARKERS_MISSING: Task prompt contains step-id pattern ({step_id}) "
        "but lacks DES markers. Step execution tasks require DES monitoring."
    )

    def check(self, prompt: str) -> EnforcementResult:
        """Check if a Task prompt requires DES markers but lacks them."""
        if self.DES_MARKER in prompt or self.EXEMPT_MARKER in prompt:
            return EnforcementResult(is_enforced=False)

        match = self.STEP_ID_PATTERN.search(prompt)
        if not match:
            return EnforcementResult(is_enforced=False)

        return EnforcementResult(
            is_enforced=True,
            reason=self.ENFORCED_REASON.format(step_id=match.group()),
            recovery_suggestions=[
                "Add DES markers to the Task prompt:",
                "<!-- DES-VALIDATION : required -->",
                "<!-- DES-PROJECT-ID : {project-id} -->",
                "<!-- DES-STEP-ID : {step-id} -->",
                "Read ~/.claude/commands/nw/execute.md for the full template.",
                "If this is NOT step execution, add: <!-- DES-ENFORCEMENT : exempt -->",
            ],
        )
