"""
TaskInvocationPort interface for sub-agent task invocation in DES.

Defines the contract for invoking sub-agent tasks, abstracting away the
specific implementation (Claude Code Task tool, mock for testing, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any


class TaskInvocationPort(ABC):
    """
    Port interface for invoking sub-agent tasks.

    Implementations provide different task invocation strategies (actual Task
    tool invocation, mocked responses for testing, etc.) while maintaining
    a consistent interface.
    """

    @abstractmethod
    def invoke_task(self, prompt: str, agent: str) -> dict[str, Any]:
        """
        Invoke a sub-agent task.

        Args:
            prompt: The prompt to send to the sub-agent
            agent: The agent identifier to invoke

        Returns:
            Dict containing task result with keys:
            - success: bool indicating if task completed successfully
            - output: str output from the task (if successful)
            - error: str error message (if failed)
        """
        pass
