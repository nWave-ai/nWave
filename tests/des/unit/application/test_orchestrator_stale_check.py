"""Unit tests for DESOrchestrator.execute_step_with_stale_check() integration.

Tests the orchestrator's integration with StaleExecutionDetector to block
execution when stale IN_PROGRESS phases are detected.
"""

import json
from datetime import datetime, timedelta, timezone

from des.application.orchestrator import DESOrchestrator


class TestOrchestratorStaleCheckIntegration:
    """Test suite for stale execution detection integration in orchestrator."""

    def test_orchestrator_instantiates_stale_detector(self, tmp_path):
        """
        GIVEN DESOrchestrator instance
        WHEN execute_step_with_stale_check is called with no stale executions
        THEN execution should proceed normally (not blocked)
        """
        # Arrange: Create clean step file
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)
        step_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "TODO"},
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "NOT_EXECUTED", "turn_count": 0}
                ]
            },
        }
        step_file.write_text(json.dumps(step_data, indent=2))

        # Act: Call execute_step_with_stale_check
        orchestrator = DESOrchestrator.create_with_defaults()
        result = orchestrator.execute_step_with_stale_check(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="steps/01-01.json",
            project_root=tmp_path,
        )

        # Assert: Execution not blocked
        assert result.blocked is False
        assert result.blocking_reason is None
        assert result.stale_alert is None
        assert result.execute_result is not None

    def test_orchestrator_calls_scan_before_execution(self, tmp_path):
        """
        GIVEN stale step file with IN_PROGRESS phase
        WHEN execute_step_with_stale_check is called
        THEN execution should be blocked with stale alert
        """
        # Arrange: Create stale step file
        stale_step = tmp_path / "steps" / "01-01.json"
        stale_step.parent.mkdir(parents=True, exist_ok=True)
        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()
        stale_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "PREPARE",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    }
                ]
            },
        }
        stale_step.write_text(json.dumps(stale_data, indent=2))

        # Create target step
        target_step = tmp_path / "steps" / "02-01.json"
        target_data = {
            "task_id": "02-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "TODO"},
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "NOT_EXECUTED", "turn_count": 0}
                ]
            },
        }
        target_step.write_text(json.dumps(target_data, indent=2))

        # Act: Call execute_step_with_stale_check
        orchestrator = DESOrchestrator.create_with_defaults()
        result = orchestrator.execute_step_with_stale_check(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="steps/02-01.json",
            project_root=tmp_path,
        )

        # Assert: Execution blocked
        assert result.blocked is True
        assert result.blocking_reason == "STALE_EXECUTION_DETECTED"
        assert result.stale_alert is not None
        assert "01-01.json" in result.stale_alert.step_file

    def test_orchestrator_blocks_when_stale_detected(self, tmp_path):
        """
        GIVEN stale execution detected (is_blocked=true)
        WHEN execute_step_with_stale_check is called
        THEN execution should be blocked and execute_result should be None
        """
        # Arrange: Create stale step file
        stale_step = tmp_path / "steps" / "01-01.json"
        stale_step.parent.mkdir(parents=True, exist_ok=True)
        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()
        stale_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "RED_UNIT",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    }
                ]
            },
        }
        stale_step.write_text(json.dumps(stale_data, indent=2))

        # Create target step
        target_step = tmp_path / "steps" / "02-01.json"
        target_data = {
            "task_id": "02-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "TODO"},
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "NOT_EXECUTED", "turn_count": 0}
                ]
            },
        }
        target_step.write_text(json.dumps(target_data, indent=2))

        # Act: Call execute_step_with_stale_check
        orchestrator = DESOrchestrator.create_with_defaults()
        result = orchestrator.execute_step_with_stale_check(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="steps/02-01.json",
            project_root=tmp_path,
        )

        # Assert: Execution blocked, no execute_result
        assert result.blocked is True
        assert result.execute_result is None

    def test_orchestrator_displays_stale_alert(self, tmp_path):
        """
        GIVEN stale execution detected
        WHEN execution is blocked
        THEN stale_alert should include step_file, phase_name, age_minutes
        """
        # Arrange: Create stale step file
        stale_step = tmp_path / "steps" / "01-01.json"
        stale_step.parent.mkdir(parents=True, exist_ok=True)
        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=50)
        ).isoformat()
        stale_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "GREEN",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    }
                ]
            },
        }
        stale_step.write_text(json.dumps(stale_data, indent=2))

        # Create target step
        target_step = tmp_path / "steps" / "02-01.json"
        target_data = {
            "task_id": "02-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "TODO"},
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "NOT_EXECUTED", "turn_count": 0}
                ]
            },
        }
        target_step.write_text(json.dumps(target_data, indent=2))

        # Act: Call execute_step_with_stale_check
        orchestrator = DESOrchestrator.create_with_defaults()
        result = orchestrator.execute_step_with_stale_check(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="steps/02-01.json",
            project_root=tmp_path,
        )

        # Assert: Alert includes details
        assert result.stale_alert is not None
        assert "01-01.json" in result.stale_alert.step_file
        assert result.stale_alert.phase_name == "GREEN"
        assert result.stale_alert.age_minutes >= 50

    def test_orchestrator_sets_blocking_reason_correctly(self, tmp_path):
        """
        GIVEN stale execution detected
        WHEN execution is blocked
        THEN blocking_reason should be STALE_EXECUTION_DETECTED
        """
        # Arrange: Create stale step file
        stale_step = tmp_path / "steps" / "01-01.json"
        stale_step.parent.mkdir(parents=True, exist_ok=True)
        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()
        stale_data = {
            "task_id": "01-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "REFACTOR_CONTINUOUS",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    }
                ]
            },
        }
        stale_step.write_text(json.dumps(stale_data, indent=2))

        # Create target step
        target_step = tmp_path / "steps" / "02-01.json"
        target_data = {
            "task_id": "02-01",
            "project_id": "test-project",
            "workflow_type": "tdd_cycle",
            "state": {"status": "TODO"},
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "NOT_EXECUTED", "turn_count": 0}
                ]
            },
        }
        target_step.write_text(json.dumps(target_data, indent=2))

        # Act: Call execute_step_with_stale_check
        orchestrator = DESOrchestrator.create_with_defaults()
        result = orchestrator.execute_step_with_stale_check(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="steps/02-01.json",
            project_root=tmp_path,
        )

        # Assert: Blocking reason set correctly
        assert result.blocking_reason == "STALE_EXECUTION_DETECTED"
