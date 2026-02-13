"""
MockedTaskAdapter - test task invocation implementation.

Provides a mocked task invocation adapter for testing environments,
returning predefined results instead of invoking actual tasks.
"""

from typing import Any

from des.ports.driven_ports.task_invocation_port import TaskInvocationPort


class MockedTaskAdapter(TaskInvocationPort):
    """
    Test task invocation adapter that returns predefined results.

    Supports both single predefined results and queues of results for
    testing scenarios with multiple task invocations.
    """

    def __init__(
        self,
        predefined_result: dict[str, Any] | None = None,
        results_queue: list[dict[str, Any]] | None = None,
    ):
        """
        Initialize the mocked task adapter.

        Args:
            predefined_result: Single result to return for all invocations
            results_queue: Queue of results to return in sequence
        """
        self.predefined_result = predefined_result
        self.results_queue = results_queue or []
        self.invocation_count = 0

    def invoke_task(self, prompt: str, agent: str) -> dict[str, Any]:
        """
        Return a predefined task result without actual invocation.

        Args:
            prompt: Ignored (for testing)
            agent: Ignored (for testing)

        Returns:
            Predefined task result dictionary
        """
        self.invocation_count += 1

        # If we have a results queue, pop from it
        if self.results_queue:
            if len(self.results_queue) > 0:
                return self.results_queue.pop(0)

        # Otherwise return the predefined result
        if self.predefined_result:
            return self.predefined_result

        # Default response if nothing configured
        return {"success": True, "output": "Mocked task result", "error": None}
