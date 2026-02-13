"""Test implementation of post-execution hook adapter."""

from des.application.orchestrator import HookPort, HookResult


class MockedSubagentStopHook(HookPort):
    """Test implementation of post-execution hook.

    Returns predefined results without file I/O for fast, deterministic testing.
    Tracks call history for verification in tests.
    """

    def __init__(self, predefined_result: HookResult = None):
        """Initialize with optional predefined result.

        Args:
            predefined_result: HookResult to return from on_agent_complete.
                             Defaults to PASSED status if not provided.
        """
        self._result = predefined_result or HookResult(validation_status="PASSED")
        self.call_count = 0
        self.last_step_file_path = None
        self.persist_turn_count_calls = []

    def persist_turn_count(
        self, step_file_path: str, phase_name: str, turn_count: int
    ) -> None:
        """Track persist_turn_count calls without file I/O.

        Args:
            step_file_path: Path to step file (recorded but not written)
            phase_name: Name of the phase to update
            turn_count: Turn count value to persist

        Raises:
            ValueError: If turn_count is negative
        """
        if turn_count < 0:
            raise ValueError(f"turn_count must be non-negative, got {turn_count}")

        self.persist_turn_count_calls.append(
            {
                "step_file_path": step_file_path,
                "phase_name": phase_name,
                "turn_count": turn_count,
            }
        )

    def on_agent_complete(self, step_file_path: str) -> HookResult:
        """Return predefined result without file I/O.

        Args:
            step_file_path: Path to step file (recorded but not read)

        Returns:
            Predefined HookResult configured at initialization
        """
        self.call_count += 1
        self.last_step_file_path = step_file_path
        return self._result
