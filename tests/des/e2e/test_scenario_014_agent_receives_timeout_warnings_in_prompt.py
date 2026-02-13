"""
Acceptance test for scenario 014: Agent receives timeout warnings in prompt context.

This test validates that timeout warnings are injected into the agent's prompt
context on the next turn after a threshold is crossed during execution.
"""

import json
import tempfile
from datetime import timedelta
from pathlib import Path


class TestScenario014AgentReceivesTimeoutWarningsInPrompt:
    """
    Test that timeout warnings are included in agent prompt context.

    Acceptance Criteria:
    - Agent receives warning message in next turn after threshold crossed
    - Warning format: 'TIMEOUT WARNING: 75% elapsed (30/40 minutes). Remaining: 10 minutes.'
    - Warning includes phase name and suggested actions
    - Warnings do not block execution, only inform agent
    """

    def test_agent_receives_timeout_warnings_in_prompt(
        self, scenario_des_orchestrator, mocked_time_provider
    ):
        """Timeout warnings are injected into agent's prompt context after threshold crossed."""
        # Given: A step file with a phase that started 7 minutes ago
        # and configured thresholds at [5, 10, 15] minutes
        orchestrator = scenario_des_orchestrator

        with tempfile.TemporaryDirectory() as tmpdir:
            step_file_path = Path(tmpdir) / "test_step.json"

            # Create step file with phase started 7 minutes ago (relative to mocked time)
            base_time = mocked_time_provider.now_utc()
            started_at = (base_time - timedelta(minutes=7)).isoformat()
            step_data = self._create_step_file_with_started_at(started_at)

            with open(step_file_path, "w") as f:
                json.dump(step_data, f, indent=2)

            # Configure thresholds at 5, 10, 15 minutes with 40 minute budget
            thresholds = [5, 10, 15]
            timeout_budget_minutes = 40

            # When: Rendering prompt after threshold crossed
            prompt = orchestrator.render_prompt(
                command="/nw:execute",
                agent="@software-crafter",
                step_file="test_step.json",
                project_root=tmpdir,
                timeout_thresholds=thresholds,
                timeout_budget_minutes=timeout_budget_minutes,
            )

            # Then: Prompt should contain timeout warning
            assert "TIMEOUT WARNING" in prompt

            # And: Warning should include percentage elapsed
            assert "%" in prompt and "elapsed" in prompt.lower()

            # And: Warning should include remaining time
            assert "Remaining:" in prompt or "remaining" in prompt.lower()

            # And: Warning should include phase name
            assert "PREPARE" in prompt or "phase" in prompt.lower()

    def _create_step_file_with_started_at(self, started_at: str) -> dict:
        """Create minimal step file structure with started_at timestamp."""
        return {
            "task_specification": {
                "task_id": "04-02",
                "project_id": "des-us006",
                "name": "Test timeout warnings in prompt",
            },
            "state": {
                "status": "IN_PROGRESS",
                "started_at": started_at,
                "ended_at": None,
            },
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "PREPARE",
                        "phase_index": 0,
                        "status": "IN_PROGRESS",
                        "started_at": started_at,
                        "ended_at": None,
                        "turn_count": 0,
                    }
                ]
            },
        }
