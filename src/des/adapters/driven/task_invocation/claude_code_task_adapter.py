"""
ClaudeCodeTaskAdapter - production task invocation implementation.

Provides integration with the actual Claude Code Task tool for invoking
sub-agents in production environments.
"""

from typing import Any

from des.ports.driven_ports.task_invocation_port import TaskInvocationPort


class ClaudeCodeTaskAdapter(TaskInvocationPort):
    """
    Production task invocation adapter that uses the actual Task tool.

    This adapter integrates with Claude Code's Task tool to invoke
    sub-agents and return their results.
    """

    def invoke_task(self, prompt: str, agent: str) -> dict[str, Any]:
        """
        Invoke a sub-agent task using the Claude Code Task tool.

        Args:
            prompt: The prompt to send to the sub-agent
            agent: The agent identifier to invoke

        Returns:
            Task result dictionary with keys:
            - success: bool
            - output: str (if successful)
            - error: str (if failed)

        Raises:
            NotImplementedError: Production Task tool integration pending.
                                Use MockedTaskAdapter for testing.

        Note:
            This adapter is a placeholder for future Claude Code Task tool integration.
            Current implementation intentionally raises NotImplementedError to prevent
            accidental use in production before integration is complete.
        """
        raise NotImplementedError(
            "ClaudeCodeTaskAdapter requires integration with actual Task tool. "
            "Use MockedTaskAdapter for testing."
        )
