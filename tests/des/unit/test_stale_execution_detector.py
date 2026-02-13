"""
Unit Tests: StaleExecutionDetector Application Service

LAYER: Application Layer (Hexagonal Architecture)
DEPENDENCIES:
- Domain: StaleExecution (value object)
- Domain: StaleDetectionResult (entity)

BUSINESS RULES UNDER TEST:
- Scan steps directory for IN_PROGRESS phases
- Compare phase age against configurable threshold (default 30 min)
- Return StaleDetectionResult with list of stale executions
- Pure file scanning (no DB, HTTP, or external services)
- Environment variable DES_STALE_THRESHOLD_MINUTES overrides default

TEST STRATEGY: Classical TDD (real domain objects, no mocking inside hexagon)
"""

import json
from datetime import datetime, timedelta, timezone

from des.application.stale_execution_detector import StaleExecutionDetector


class TestStaleExecutionDetectorInitialization:
    """Test service initialization and configuration."""

    def test_detector_initializes_with_project_root(self, tmp_path):
        """
        GIVEN a valid project root path
        WHEN StaleExecutionDetector is initialized
        THEN detector stores project root correctly
        """
        detector = StaleExecutionDetector(project_root=tmp_path)
        assert detector is not None

    def test_detector_uses_default_threshold_30_minutes(self, tmp_path):
        """
        GIVEN no environment variable set
        WHEN StaleExecutionDetector is initialized
        THEN threshold defaults to 30 minutes
        """
        detector = StaleExecutionDetector(project_root=tmp_path)
        assert detector.threshold_minutes == 30

    def test_detector_respects_environment_variable_threshold(
        self, tmp_path, monkeypatch
    ):
        """
        GIVEN DES_STALE_THRESHOLD_MINUTES=10 environment variable
        WHEN StaleExecutionDetector is initialized
        THEN threshold is set to 10 minutes
        """
        monkeypatch.setenv("DES_STALE_THRESHOLD_MINUTES", "10")
        detector = StaleExecutionDetector(project_root=tmp_path)
        assert detector.threshold_minutes == 10

    def test_detector_falls_back_to_default_when_env_var_invalid_non_integer(
        self, tmp_path, monkeypatch
    ):
        """
        GIVEN DES_STALE_THRESHOLD_MINUTES="invalid" (non-integer string)
        WHEN StaleExecutionDetector is initialized
        THEN threshold falls back to 30 minutes default
        """
        monkeypatch.setenv("DES_STALE_THRESHOLD_MINUTES", "invalid")
        detector = StaleExecutionDetector(project_root=tmp_path)
        assert detector.threshold_minutes == 30

    def test_detector_falls_back_to_default_when_env_var_empty_string(
        self, tmp_path, monkeypatch
    ):
        """
        GIVEN DES_STALE_THRESHOLD_MINUTES="" (empty string)
        WHEN StaleExecutionDetector is initialized
        THEN threshold falls back to 30 minutes default
        """
        monkeypatch.setenv("DES_STALE_THRESHOLD_MINUTES", "")
        detector = StaleExecutionDetector(project_root=tmp_path)
        assert detector.threshold_minutes == 30

    def test_detector_falls_back_to_default_when_env_var_negative(
        self, tmp_path, monkeypatch
    ):
        """
        GIVEN DES_STALE_THRESHOLD_MINUTES="-5" (negative integer)
        WHEN StaleExecutionDetector is initialized
        THEN threshold falls back to 30 minutes default
        """
        monkeypatch.setenv("DES_STALE_THRESHOLD_MINUTES", "-5")
        detector = StaleExecutionDetector(project_root=tmp_path)
        assert detector.threshold_minutes == 30

    def test_detector_uses_external_services_is_false(self, tmp_path):
        """
        GIVEN StaleExecutionDetector is initialized
        WHEN checking uses_external_services property
        THEN it returns False (pure file scanning, no DB/HTTP/external services)
        """
        detector = StaleExecutionDetector(project_root=tmp_path)
        assert detector.uses_external_services is False

    def test_detector_is_session_scoped_is_true(self, tmp_path):
        """
        GIVEN StaleExecutionDetector is initialized
        WHEN checking is_session_scoped property
        THEN it returns True (no daemon, terminates with session)
        """
        detector = StaleExecutionDetector(project_root=tmp_path)
        assert detector.is_session_scoped is True


class TestStaleExecutionDetectorScanningLogic:
    """Test core scanning and detection logic."""

    def test_scan_returns_empty_result_when_no_step_files(self, tmp_path):
        """
        GIVEN steps directory is empty
        WHEN scan_for_stale_executions is called
        THEN result has is_blocked=False and empty stale_executions list
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        assert result.is_blocked is False
        assert len(result.stale_executions) == 0

    def test_scan_ignores_completed_steps(self, tmp_path):
        """
        GIVEN step file with status="DONE"
        WHEN scan_for_stale_executions is called
        THEN step is not flagged as stale
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        completed_step = {
            "task_id": "01-01",
            "state": {
                "status": "DONE",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        (steps_dir / "01-01.json").write_text(json.dumps(completed_step))

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        assert result.is_blocked is False
        assert len(result.stale_executions) == 0

    def test_scan_detects_stale_in_progress_phase_exceeding_threshold(self, tmp_path):
        """
        GIVEN step with IN_PROGRESS phase started 45 minutes ago
        AND threshold is 30 minutes
        WHEN scan_for_stale_executions is called
        THEN step is flagged as stale (45 > 30)
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()
        stale_step = {
            "task_id": "01-01",
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
        (steps_dir / "01-01.json").write_text(json.dumps(stale_step))

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        assert result.is_blocked is True
        assert len(result.stale_executions) == 1
        assert result.stale_executions[0].step_file == "steps/01-01.json"
        assert result.stale_executions[0].phase_name == "RED_UNIT"
        assert result.stale_executions[0].age_minutes >= 45

    def test_scan_ignores_recent_in_progress_within_threshold(self, tmp_path):
        """
        GIVEN step with IN_PROGRESS phase started 15 minutes ago
        AND threshold is 30 minutes
        WHEN scan_for_stale_executions is called
        THEN step is NOT flagged as stale (15 < 30)
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        recent_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=15)
        ).isoformat()
        recent_step = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS", "started_at": recent_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "GREEN_UNIT",
                        "status": "IN_PROGRESS",
                        "started_at": recent_timestamp,
                    }
                ]
            },
        }
        (steps_dir / "01-01.json").write_text(json.dumps(recent_step))

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        assert result.is_blocked is False
        assert len(result.stale_executions) == 0

    def test_scan_detects_multiple_stale_executions(self, tmp_path):
        """
        GIVEN two step files with stale IN_PROGRESS phases
        WHEN scan_for_stale_executions is called
        THEN both steps are flagged as stale
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()

        # First stale step
        stale_step_1 = {
            "task_id": "01-01",
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
        (steps_dir / "01-01.json").write_text(json.dumps(stale_step_1))

        # Second stale step
        stale_step_2 = {
            "task_id": "02-01",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "GREEN_UNIT",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    }
                ]
            },
        }
        (steps_dir / "02-01.json").write_text(json.dumps(stale_step_2))

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        assert result.is_blocked is True
        assert len(result.stale_executions) == 2

    def test_scan_uses_custom_threshold_from_environment(self, tmp_path, monkeypatch):
        """
        GIVEN DES_STALE_THRESHOLD_MINUTES=10
        AND step with IN_PROGRESS phase started 15 minutes ago
        WHEN scan_for_stale_executions is called
        THEN step is flagged as stale (15 > 10)
        """
        monkeypatch.setenv("DES_STALE_THRESHOLD_MINUTES", "10")
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=15)
        ).isoformat()
        stale_step = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "RED_ACCEPTANCE",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    }
                ]
            },
        }
        (steps_dir / "01-01.json").write_text(json.dumps(stale_step))

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        assert result.is_blocked is True
        assert len(result.stale_executions) == 1


class TestStaleExecutionDetectorStaleDetectionResult:
    """Test that scan returns proper StaleDetectionResult with domain entities."""

    def test_scan_returns_stale_detection_result_instance(self, tmp_path):
        """
        GIVEN any project state
        WHEN scan_for_stale_executions is called
        THEN returns StaleDetectionResult instance
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        from des.domain.stale_detection_result import StaleDetectionResult

        assert isinstance(result, StaleDetectionResult)

    def test_scan_result_contains_stale_execution_instances(self, tmp_path):
        """
        GIVEN stale step file
        WHEN scan_for_stale_executions is called
        THEN result contains StaleExecution instances
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()
        stale_step = {
            "task_id": "01-01",
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
        (steps_dir / "01-01.json").write_text(json.dumps(stale_step))

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        from des.domain.stale_execution import StaleExecution

        assert len(result.stale_executions) == 1
        assert isinstance(result.stale_executions[0], StaleExecution)


class TestStaleExecutionDetectorThresholdBoundaries:
    """Test threshold boundary conditions (age > threshold, not >=)."""

    def test_phase_exactly_at_threshold_not_flagged_as_stale(self, tmp_path):
        """
        GIVEN step with IN_PROGRESS phase started exactly 30 minutes ago
        AND threshold is 30 minutes
        WHEN scan_for_stale_executions is called
        THEN step is NOT flagged as stale (30 == 30, need > not >=)
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        # Create phase that is exactly 30 minutes old
        exactly_at_threshold = (
            datetime.now(timezone.utc) - timedelta(minutes=30)
        ).isoformat()
        step_at_boundary = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS", "started_at": exactly_at_threshold},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "GREEN_UNIT",
                        "status": "IN_PROGRESS",
                        "started_at": exactly_at_threshold,
                    }
                ]
            },
        }
        (steps_dir / "01-01.json").write_text(json.dumps(step_at_boundary))

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        # Should NOT be stale (boundary is exclusive, not inclusive)
        assert result.is_blocked is False
        assert len(result.stale_executions) == 0

    def test_phase_one_minute_over_threshold_flagged_as_stale(self, tmp_path):
        """
        GIVEN step with IN_PROGRESS phase started 31 minutes ago
        AND threshold is 30 minutes
        WHEN scan_for_stale_executions is called
        THEN step IS flagged as stale (31 > 30)
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        # Create phase that is 31 minutes old (1 minute over threshold)
        one_over_threshold = (
            datetime.now(timezone.utc) - timedelta(minutes=31)
        ).isoformat()
        step_over_boundary = {
            "task_id": "02-01",
            "state": {"status": "IN_PROGRESS", "started_at": one_over_threshold},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "REFACTOR_L1",
                        "status": "IN_PROGRESS",
                        "started_at": one_over_threshold,
                    }
                ]
            },
        }
        (steps_dir / "02-01.json").write_text(json.dumps(step_over_boundary))

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        # Should be stale (31 > 30)
        assert result.is_blocked is True
        assert len(result.stale_executions) == 1
        assert result.stale_executions[0].age_minutes >= 31


class TestStaleExecutionDetectorEdgeCases:
    """Test edge cases and error handling."""

    def test_scan_handles_missing_steps_directory(self, tmp_path):
        """
        GIVEN steps directory does not exist
        WHEN scan_for_stale_executions is called
        THEN returns empty result (no crash)
        """
        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        assert result.is_blocked is False
        assert len(result.stale_executions) == 0

    def test_scan_handles_step_file_without_tdd_cycle(self, tmp_path):
        """
        GIVEN step file without tdd_cycle field
        WHEN scan_for_stale_executions is called
        THEN step is safely ignored (no crash)
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        step_without_cycle = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS"},
        }
        (steps_dir / "01-01.json").write_text(json.dumps(step_without_cycle))

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        assert result.is_blocked is False
        assert len(result.stale_executions) == 0

    def test_scan_handles_phase_without_started_at(self, tmp_path):
        """
        GIVEN IN_PROGRESS phase missing started_at timestamp
        WHEN scan_for_stale_executions is called
        THEN phase is safely ignored (no crash)
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        step_missing_timestamp = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS"},
            "tdd_cycle": {
                "phase_execution_log": [
                    {
                        "phase_name": "RED_UNIT",
                        "status": "IN_PROGRESS",
                        # started_at missing
                    }
                ]
            },
        }
        (steps_dir / "01-01.json").write_text(json.dumps(step_missing_timestamp))

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        assert result.is_blocked is False
        assert len(result.stale_executions) == 0

    def test_scan_handles_corrupted_json_step_file(self, tmp_path):
        """
        GIVEN step file with invalid JSON
        WHEN scan_for_stale_executions is called
        THEN corrupted file is skipped (no crash)
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        # Create corrupted JSON file
        (steps_dir / "01-01.json").write_text("{ invalid json content")

        # Create valid stale file
        stale_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=45)
        ).isoformat()
        valid_step = {
            "task_id": "02-01",
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
        (steps_dir / "02-01.json").write_text(json.dumps(valid_step))

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        # Should detect valid stale file, ignore corrupted file
        assert result.is_blocked is True
        assert len(result.stale_executions) == 1

    def test_scan_collects_warning_for_corrupted_json_file(self, tmp_path):
        """
        GIVEN one step file has corrupted JSON
        WHEN scan_for_stale_executions runs
        THEN result includes warning with file_path and error message
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        # Create corrupted JSON file
        (steps_dir / "01-01.json").write_text("{ invalid json content")

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        # Should collect warning for corrupted file
        assert hasattr(result, "warnings")
        assert len(result.warnings) == 1
        assert result.warnings[0]["file_path"] == "steps/01-01.json"
        # Error message should indicate JSON parsing issue
        error_msg = result.warnings[0]["error"].lower()
        assert any(
            keyword in error_msg for keyword in ["json", "parse", "expecting", "decode"]
        )

    def test_scan_collects_multiple_warnings_for_multiple_corrupted_files(
        self, tmp_path
    ):
        """
        GIVEN multiple step files have corrupted JSON
        WHEN scan_for_stale_executions runs
        THEN result includes all warnings with file paths
        """
        steps_dir = tmp_path / "steps"
        steps_dir.mkdir()

        # Create 3 corrupted JSON files
        (steps_dir / "01-01.json").write_text("{ invalid json")
        (steps_dir / "02-02.json").write_text("not json at all")
        (steps_dir / "03-03.json").write_text('{"incomplete": ')

        detector = StaleExecutionDetector(project_root=tmp_path)
        result = detector.scan_for_stale_executions()

        # Should collect warnings for all corrupted files
        assert hasattr(result, "warnings")
        assert len(result.warnings) == 3
        file_paths = [w["file_path"] for w in result.warnings]
        assert "steps/01-01.json" in file_paths
        assert "steps/02-02.json" in file_paths
        assert "steps/03-03.json" in file_paths
