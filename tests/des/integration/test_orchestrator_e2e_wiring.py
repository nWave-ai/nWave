"""
Unit tests for DESOrchestrator E2E wiring features.

Tests validate that execute_step() supports:
1. mocked_elapsed_times parameter for time progression simulation
2. timeout_warnings field in result
4. execution_path and features_validated fields in result

These unit tests drive implementation for Step 08-01 E2E wiring test.
"""

from pathlib import Path

import pytest

from des.application.orchestrator import ExecuteStepResult


class TestOrchestratorE2EWiring:
    """Unit tests for E2E wiring features in DESOrchestrator."""

    def test_execute_step_accepts_mocked_elapsed_times_parameter(
        self, des_orchestrator, in_memory_filesystem, minimal_step_file_dict
    ):
        """
        GIVEN orchestrator with step file configured
        WHEN execute_step() called with mocked_elapsed_times parameter
        THEN method accepts parameter without TypeError
        AND result includes timeout_warnings for crossed thresholds

        This enables E2E test to simulate time progression for timeout testing.
        """
        # GIVEN: Step file with timeout configuration
        step_file_path = Path("/tmp/step.json")
        step_data = minimal_step_file_dict.copy()
        step_data["tdd_cycle"]["duration_minutes"] = 30
        step_data["tdd_cycle"]["max_turns"] = 50

        in_memory_filesystem.write_json(step_file_path, step_data)

        # WHEN: execute_step() called with mocked_elapsed_times
        mocked_times = [900, 1350, 1620]  # 15min (50%), 22.5min (75%), 27min (90%)

        result = des_orchestrator.execute_step(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="step.json",
            project_root="/tmp",
            simulated_iterations=3,
            mocked_elapsed_times=mocked_times,  # NEW PARAMETER
            timeout_thresholds=[15, 22, 27],  # Required for mocked time logic
        )

        # THEN: Method accepts parameter (no TypeError)
        assert result is not None
        assert isinstance(result, ExecuteStepResult)

        # AND: Result has timeout_warnings field
        assert hasattr(result, "timeout_warnings"), (
            "ExecuteStepResult must have timeout_warnings field"
        )

        # AND: Warnings emitted for crossed thresholds
        assert len(result.timeout_warnings) >= 3, (
            f"Expected at least 3 warnings for 50%, 75%, 90% thresholds, "
            f"got {len(result.timeout_warnings)}"
        )

    def test_execute_step_result_has_timeout_warnings_field(
        self, des_orchestrator, in_memory_filesystem, minimal_step_file_dict
    ):
        """
        GIVEN orchestrator executing step with timeout thresholds
        WHEN execute_step() returns result
        THEN result.timeout_warnings field exists (not warnings_emitted)
        AND field contains list of warning strings

        This ensures API consistency for E2E test validation.
        """
        step_file_path = Path("/tmp/step.json")
        in_memory_filesystem.write_json(step_file_path, minimal_step_file_dict)

        result = des_orchestrator.execute_step(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="step.json",
            project_root="/tmp",
            simulated_iterations=1,
            timeout_thresholds=[15, 20, 27],  # minutes
        )

        # THEN: Result has timeout_warnings field
        assert hasattr(result, "timeout_warnings")
        assert isinstance(result.timeout_warnings, list)

    def test_execute_step_result_has_execution_path_field(
        self, des_orchestrator, in_memory_filesystem, minimal_step_file_dict
    ):
        """
        GIVEN orchestrator executing step
        WHEN execute_step() returns result
        THEN result.execution_path identifies orchestrator method path
        AND value is "DESOrchestrator.execute_step"

        This proves test validates features in actual execution path.
        """
        step_file_path = Path("/tmp/step.json")
        in_memory_filesystem.write_json(step_file_path, minimal_step_file_dict)

        result = des_orchestrator.execute_step(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="step.json",
            project_root="/tmp",
            simulated_iterations=1,
        )

        # THEN: Result has execution_path field
        assert hasattr(result, "execution_path")
        assert result.execution_path == "DESOrchestrator.execute_step"

    def test_execute_step_result_has_features_validated_field(
        self, des_orchestrator, in_memory_filesystem, minimal_step_file_dict
    ):
        """
        GIVEN orchestrator executing step with all features
        WHEN execute_step() returns result
        THEN result.features_validated lists all executed features
        AND list includes ["turn_counting", "timeout_monitoring", "extension_api"]

        This documents which features were validated during execution.
        """
        step_file_path = Path("/tmp/step.json")
        in_memory_filesystem.write_json(step_file_path, minimal_step_file_dict)

        result = des_orchestrator.execute_step(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="step.json",
            project_root="/tmp",
            simulated_iterations=1,
            mocked_elapsed_times=[900],  # 15 minutes, crosses 15-minute threshold
            timeout_thresholds=[15, 20, 27],
        )

        # THEN: Result has features_validated field
        assert hasattr(result, "features_validated")
        assert isinstance(result.features_validated, list)

        # AND: Core features listed (extension_api is OUT_OF_SCOPE in US-006)
        expected_features = ["turn_counting", "timeout_monitoring"]
        for feature in expected_features:
            assert feature in result.features_validated, (
                f"Feature '{feature}' should be in features_validated list"
            )


@pytest.fixture
def minimal_step_file_dict():
    """Create minimal step file structure for testing."""
    return {
        "task_id": "test-01",
        "project_id": "test",
        "state": {"status": "NOT_STARTED", "started_at": None, "completed_at": None},
        "tdd_cycle": {
            "max_turns": 50,
            "duration_minutes": 30,
            "total_extensions_minutes": 0,
            "phase_execution_log": [
                {
                    "phase_name": "PREPARE",
                    "phase_index": 0,
                    "status": "NOT_EXECUTED",
                    "started_at": None,
                    "ended_at": None,
                    "turn_count": 0,
                }
            ],
        },
    }
