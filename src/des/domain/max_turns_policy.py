"""Max turns policy domain logic.

Pure business rule for validating the max_turns parameter
on Task tool invocations. No I/O dependencies.

Replaces inline validation in claude_code_hook_adapter.handle_pre_tool_use()
(lines 100-119).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyResult:
    """Result of a max_turns policy validation.

    Attributes:
        is_valid: Whether the max_turns value passes validation
        reason: Block reason if invalid, None if valid
    """

    is_valid: bool
    reason: str | None = None


class MaxTurnsPolicy:
    """Validates max_turns parameter for Task tool invocations.

    Business rules:
    1. max_turns must not be None (MISSING_MAX_TURNS)
    2. max_turns must be an integer (INVALID_MAX_TURNS)
    3. max_turns must be between 10 and 100 inclusive (INVALID_MAX_TURNS)
    """

    MIN_TURNS = 10
    MAX_TURNS = 100

    MISSING_REASON = (
        "MISSING_MAX_TURNS: The max_turns parameter is required for all Task invocations. "
        "Add max_turns parameter (e.g., max_turns=30) to prevent unbounded execution."
    )

    INVALID_REASON_TEMPLATE = (
        "INVALID_MAX_TURNS: max_turns must be an integer between {min} and {max} (got: {value}). "
        "Recommended values: quick edit=15, background task=25, standard=30, research=35, complex=50."
    )

    def validate(self, max_turns: int | None) -> PolicyResult:
        """Validate a max_turns value against the policy.

        Args:
            max_turns: The max_turns parameter value (may be None)

        Returns:
            PolicyResult indicating whether the value is valid
        """
        if max_turns is None:
            return PolicyResult(is_valid=False, reason=self.MISSING_REASON)

        if (
            not isinstance(max_turns, int)
            or max_turns < self.MIN_TURNS
            or max_turns > self.MAX_TURNS
        ):
            reason = self.INVALID_REASON_TEMPLATE.format(
                min=self.MIN_TURNS,
                max=self.MAX_TURNS,
                value=max_turns,
            )
            return PolicyResult(is_valid=False, reason=reason)

        return PolicyResult(is_valid=True)
