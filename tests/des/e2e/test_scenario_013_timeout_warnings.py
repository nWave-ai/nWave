"""
Acceptance test for scenario 013: Timeout warnings emit at thresholds.

This test validates that TimeoutMonitor is properly wired into DESOrchestrator
to emit warnings during active agent execution when time thresholds are crossed.
"""

import json
import tempfile
from datetime import timedelta
from pathlib import Path


class TestScenario013TimeoutWarningsEmitAtThresholds:
    """
    Test that TimeoutMonitor integration emits warnings during execution.

    Acceptance Criteria:
    - TimeoutMonitor initialized at phase start with configured thresholds
    - Orchestrator checks thresholds during execution loop (e.g., every 5 turns)
    - Warning messages emitted to agent context when thresholds crossed
    - Warnings include remaining time and current progress
    - Timeout warnings ACTIVATE when /nw:execute or /nw:develop invoked
    """

    def test_timeout_warnings_emit_at_thresholds(
        self, scenario_des_orchestrator, mocked_time_provider
    ):
        """TimeoutMonitor emits warnings when time thresholds are crossed during execution."""
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

            # Configure thresholds at 5, 10, 15 minutes
            thresholds = [5, 10, 15]

            # When: Executing a step with /nw:execute command
            result = orchestrator.execute_step(
                command="/nw:execute",
                agent="@software-crafter",
                step_file="test_step.json",
                project_root=tmpdir,
                simulated_iterations=3,
                timeout_thresholds=thresholds,
            )

            # Then: Warning should be emitted for the 5-minute threshold
            assert result.warnings_emitted is not None
            assert len(result.warnings_emitted) > 0

            # And: Warning should mention the crossed threshold (5 minutes)
            first_warning = result.warnings_emitted[0]
            assert "5" in first_warning or "threshold" in first_warning.lower()

            # And: Warning should include remaining time information
            assert (
                "remaining" in first_warning.lower()
                or "elapsed" in first_warning.lower()
            )

    def _create_step_file_with_started_at(self, started_at: str) -> dict:
        """Create minimal step file structure with started_at timestamp."""
        return {
            "task_specification": {
                "task_id": "04-01",
                "project_id": "des-us006",
                "name": "Test timeout monitoring",
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
