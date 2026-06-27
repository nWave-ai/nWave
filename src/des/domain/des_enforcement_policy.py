"""DES Enforcement Policy - step-id based enforcement rule.

Pure domain policy following PolicyResult pattern.
Every Agent prompt containing a step-id pattern (\\d{2}-\\d{2}) without DES
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

    # Keyword-anchored pattern: requires "step" keyword or DES-STEP-ID marker
    # to avoid false positives on dates (03-29), line ranges (50-80), ports (80-82)
    STEP_ID_PATTERN = re.compile(
        r"(?i)(?:"
        r"\bstep\s*[:\-]?\s*\d{2}-\d{2}\b"
        r"|DES-STEP-ID\s*:\s*\d{2}-\d{2}"
        r")"
    )
    DES_MARKER = "DES-VALIDATION : required"
    EXEMPT_MARKER = "DES-ENFORCEMENT : exempt"

    # __SCAFFOLD__ (DISTILL, feature plugin-skill-deliverable-type, ADR-PST-001).
    # Closed allow-list of deliverable types that carry the step-enforcement
    # exemption. The fail-safe is the CLOSEDNESS of this set: any value not
    # exactly in here (None, "application", typos, case mismatch) stays enforced.
    # DELIVER implements the short-circuit below and REMOVES the scaffold raise.
    EXEMPT_DELIVERABLE_TYPES = frozenset({"plugin", "skill"})

    ENFORCED_REASON = (
        "DES_MARKERS_MISSING: Task prompt contains step-id pattern ({step_id}) "
        "but lacks DES markers. Step execution tasks require DES monitoring."
    )

    def check(
        self, prompt: str, deliverable_type: str | None = None
    ) -> EnforcementResult:
        """Check if a Task prompt requires DES markers but lacks them.

        ``deliverable_type`` (ADR-PST-001): a sibling short-circuit to the
        existing ``EXEMPT_MARKER`` branch. When the resolved project deliverable
        type is in the closed exempt set ``{plugin, skill}``, step enforcement is
        disabled by default (no per-dispatch marker needed). ``None`` / unknown /
        typo / ``application`` fall through to the existing step-id rule
        (fail-safe by construction).

        The app-code path (``deliverable_type is None``) is BYTE-IDENTICAL to
        the pre-feature behaviour, so every existing enforcement test stays
        GREEN.
        """
        if deliverable_type in self.EXEMPT_DELIVERABLE_TYPES:
            return EnforcementResult(is_enforced=False)

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
                "Read ~/.claude/skills/nw-execute/SKILL.md for the full template.",
                "If this is NOT step execution, add: <!-- DES-ENFORCEMENT : exempt -->",
            ],
        )
