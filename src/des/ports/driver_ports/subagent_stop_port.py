"""SubagentStopPort - driver port for validating step completion.

Abstract interface defining how the Claude Code hook adapter communicates
with the application layer for subagent-stop validation.

Called by: ClaudeCodeHookAdapter when SubagentStop hook fires.
Implemented by: SubagentStopService (application layer).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from des.ports.driver_ports.pre_tool_use_port import HookDecision


@dataclass(frozen=True)
class SubagentStopContext:
    """Input context for subagent-stop validation.

    Attributes:
        execution_log_path: Absolute path to execution-log.yaml
        project_id: Project identifier
        step_id: Step identifier
        stop_hook_active: True if SubagentStop already fired once (second attempt).
            When True and validation fails, service allows to prevent infinite loops.
        cwd: Working directory for git commit verification. Empty string skips
            git verification (backward compatibility).
    """

    execution_log_path: str
    project_id: str
    step_id: str
    stop_hook_active: bool = False
    cwd: str = ""
    task_start_time: str = ""
    turns_used: int | None = None
    tokens_used: int | None = None


class SubagentStopPort(ABC):
    """Driver port: validates step completion when a subagent finishes.

    This is the application-layer interface that the hook adapter calls.
    The adapter translates Claude Code's JSON protocol into SubagentStopContext,
    calls this port, and translates HookDecision back to JSON + exit code.
    """

    @abstractmethod
    def validate(self, context: SubagentStopContext) -> HookDecision:
        """Validate step completion for a subagent.

        Args:
            context: Parsed context from the hook protocol

        Returns:
            HookDecision indicating allow or block
        """
        ...
