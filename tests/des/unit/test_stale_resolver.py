"""
Unit Tests for StaleResolver Application Service

Tests the stale step resolution mechanism that marks steps as ABANDONED
and provides recovery suggestions.

Coverage:
- StaleResolver initialization
- mark_abandoned() method behavior
- State updates (status, phase, failure_reason, recovery_suggestions, abandoned_at)
- YAML file reading and writing
- Error handling for invalid paths
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from des.application.stale_resolver import StaleResolver


class TestStaleResolverInitialization:
    """Test StaleResolver constructor and configuration."""

    def test_init_accepts_project_root(self, tmp_path):
        """StaleResolver should accept project_root parameter."""
        resolver = StaleResolver(project_root=tmp_path)
        assert resolver.project_root == tmp_path

    def test_init_converts_string_to_path(self, tmp_path):
        """StaleResolver should convert string project_root to Path."""
        resolver = StaleResolver(project_root=str(tmp_path))
        assert isinstance(resolver.project_root, Path)
        assert resolver.project_root == tmp_path


class TestMarkAbandonedMethod:
    """Test mark_abandoned() method for state updates."""

    def test_mark_abandoned_updates_state_status(self, tmp_path):
        """mark_abandoned() should set state.status to ABANDONED."""
        # Arrange
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)

        step_data = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS"},
            "tdd_cycle": {"phase_execution_log": []},
        }
        step_file.write_text(json.dumps(step_data, indent=2))

        resolver = StaleResolver(project_root=tmp_path)

        # Act
        resolver.mark_abandoned(step_file="steps/01-01.json", reason="Test failure")

        # Assert
        updated = json.loads(step_file.read_text())
        assert updated["state"]["status"] == "ABANDONED"

    def test_mark_abandoned_adds_failure_reason(self, tmp_path):
        """mark_abandoned() should add failure_reason to state."""
        # Arrange
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)

        step_data = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS"},
            "tdd_cycle": {"phase_execution_log": []},
        }
        step_file.write_text(json.dumps(step_data, indent=2))

        resolver = StaleResolver(project_root=tmp_path)

        # Act
        resolver.mark_abandoned(
            step_file="steps/01-01.json",
            reason="Agent crashed during RED_ACCEPTANCE phase",
        )

        # Assert
        updated = json.loads(step_file.read_text())
        assert "failure_reason" in updated["state"]
        assert "Agent crashed" in updated["state"]["failure_reason"]

    def test_mark_abandoned_adds_recovery_suggestions(self, tmp_path):
        """mark_abandoned() should add recovery_suggestions list to state."""
        # Arrange
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)

        step_data = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS"},
            "tdd_cycle": {"phase_execution_log": []},
        }
        step_file.write_text(json.dumps(step_data, indent=2))

        resolver = StaleResolver(project_root=tmp_path)

        # Act
        resolver.mark_abandoned(step_file="steps/01-01.json", reason="Test failure")

        # Assert
        updated = json.loads(step_file.read_text())
        assert "recovery_suggestions" in updated["state"]
        assert isinstance(updated["state"]["recovery_suggestions"], list)
        assert len(updated["state"]["recovery_suggestions"]) >= 1

    def test_mark_abandoned_includes_review_transcript_suggestion(self, tmp_path):
        """recovery_suggestions should include 'Review transcript' guidance."""
        # Arrange
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)

        step_data = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS"},
            "tdd_cycle": {"phase_execution_log": []},
        }
        step_file.write_text(json.dumps(step_data, indent=2))

        resolver = StaleResolver(project_root=tmp_path)

        # Act
        resolver.mark_abandoned(step_file="steps/01-01.json", reason="Test failure")

        # Assert
        updated = json.loads(step_file.read_text())
        suggestions = updated["state"]["recovery_suggestions"]
        assert any("transcript" in s.lower() for s in suggestions)

    def test_mark_abandoned_includes_reset_phase_suggestion(self, tmp_path):
        """recovery_suggestions should include 'Reset phase and retry' guidance."""
        # Arrange
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)

        step_data = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS"},
            "tdd_cycle": {"phase_execution_log": []},
        }
        step_file.write_text(json.dumps(step_data, indent=2))

        resolver = StaleResolver(project_root=tmp_path)

        # Act
        resolver.mark_abandoned(step_file="steps/01-01.json", reason="Test failure")

        # Assert
        updated = json.loads(step_file.read_text())
        suggestions = updated["state"]["recovery_suggestions"]
        assert any("reset" in s.lower() and "retry" in s.lower() for s in suggestions)

    def test_mark_abandoned_adds_abandoned_at_timestamp(self, tmp_path):
        """mark_abandoned() should add abandoned_at timestamp to state."""
        # Arrange
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)

        step_data = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS"},
            "tdd_cycle": {"phase_execution_log": []},
        }
        step_file.write_text(json.dumps(step_data, indent=2))

        resolver = StaleResolver(project_root=tmp_path)

        # Act
        resolver.mark_abandoned(step_file="steps/01-01.json", reason="Test failure")

        # Assert
        updated = json.loads(step_file.read_text())
        assert "abandoned_at" in updated["state"]
        # Verify timestamp is valid ISO format
        abandoned_at_str = updated["state"]["abandoned_at"]
        abandoned_at = datetime.fromisoformat(abandoned_at_str.replace("Z", "+00:00"))
        # Verify timestamp is recent (within last minute)
        from datetime import timezone

        now = datetime.now(timezone.utc)
        time_diff = (now - abandoned_at).total_seconds()
        assert 0 <= time_diff <= 60

    def test_mark_abandoned_updates_phase_status(self, tmp_path):
        """mark_abandoned() should update IN_PROGRESS phase status to ABANDONED."""
        # Arrange
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)

        stale_timestamp = (datetime.now() - timedelta(minutes=45)).isoformat()
        step_data = {
            "task_id": "01-01",
            "state": {"status": "IN_PROGRESS", "started_at": stale_timestamp},
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "EXECUTED"},
                    {
                        "phase_name": "RED_ACCEPTANCE",
                        "status": "IN_PROGRESS",
                        "started_at": stale_timestamp,
                    },
                ]
            },
        }
        step_file.write_text(json.dumps(step_data, indent=2))

        resolver = StaleResolver(project_root=tmp_path)

        # Act
        resolver.mark_abandoned(
            step_file="steps/01-01.json",
            reason="Agent crashed during RED_ACCEPTANCE phase",
        )

        # Assert
        updated = json.loads(step_file.read_text())
        red_acceptance_phase = updated["tdd_cycle"]["phase_execution_log"][1]
        assert red_acceptance_phase["status"] == "ABANDONED"

    def test_mark_abandoned_raises_error_for_missing_file(self, tmp_path):
        """mark_abandoned() should raise FileNotFoundError for missing step file."""
        resolver = StaleResolver(project_root=tmp_path)

        with pytest.raises(FileNotFoundError):
            resolver.mark_abandoned(
                step_file="steps/nonexistent.json", reason="Test failure"
            )

    def test_mark_abandoned_raises_error_for_invalid_json(self, tmp_path):
        """mark_abandoned() should raise JSONDecodeError for corrupted step file."""
        # Arrange
        step_file = tmp_path / "steps" / "01-01.json"
        step_file.parent.mkdir(parents=True, exist_ok=True)
        step_file.write_text("{ invalid json }")

        resolver = StaleResolver(project_root=tmp_path)

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            resolver.mark_abandoned(step_file="steps/01-01.json", reason="Test failure")
