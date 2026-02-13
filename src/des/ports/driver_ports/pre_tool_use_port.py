"""PreToolUsePort - driver port for validating Task tool invocations.

Abstract interface defining how the Claude Code hook adapter communicates
with the application layer for pre-tool-use validation.

Called by: ClaudeCodeHookAdapter when PreToolUse hook fires for Task tool.
Implemented by: PreToolUseService (application layer).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PreToolUseInput:
    """Input data for pre-tool-use validation.

    Attributes:
        prompt: Full Task prompt text
        max_turns: max_turns parameter (may be absent/None)
        subagent_type: Type of subagent being created
    """

    prompt: str
    max_turns: int | None = None
    subagent_type: str = ""


@dataclass(frozen=True)
class HookDecision:
    """Decision result from a hook validation.

    Shared by both PreToolUsePort and SubagentStopPort.

    Attributes:
        action: "allow" or "block"
        reason: Block reason (None when allowed)
        exit_code: 0=allow, 2=block
        recovery_suggestions: Actionable steps to fix block (empty when allowed)
    """

    action: str  # "allow" | "block"
    reason: str | None = None
    exit_code: int = 0
    recovery_suggestions: list[str] = field(default_factory=list)

    @staticmethod
    def allow() -> HookDecision:
        """Create an allow decision."""
        return HookDecision(action="allow", exit_code=0)

    @staticmethod
    def block(
        reason: str, recovery_suggestions: list[str] | None = None
    ) -> HookDecision:
        """Create a block decision with reason."""
        return HookDecision(
            action="block",
            reason=reason,
            exit_code=2,
            recovery_suggestions=recovery_suggestions or [],
        )


class PreToolUsePort(ABC):
    """Driver port: validates Task tool invocations before execution.

    This is the application-layer interface that the hook adapter calls.
    The adapter translates Claude Code's JSON protocol into PreToolUseInput,
    calls this port, and translates HookDecision back to JSON + exit code.
    """

    @abstractmethod
    def validate(self, input_data: PreToolUseInput) -> HookDecision:
        """Validate a Task tool invocation.

        Args:
            input_data: Parsed input from the hook protocol

        Returns:
            HookDecision indicating allow or block
        """
        ...
