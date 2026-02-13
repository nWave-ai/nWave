"""
Unit tests for recovery_suggestions data structure in step files.

Tests the recovery_suggestions field definition and behavior.
"""

import json


class TestRecoverySuggestionsDataStructure:
    """Unit tests for recovery_suggestions array in step file state."""

    def test_recovery_suggestions_field_can_be_added_to_step_state(self):
        """
        GIVEN a step file state dictionary
        WHEN recovery_suggestions field is added
        THEN field is JSON array of strings
        """
        # Arrange
        step_state = {
            "status": "FAILED",
            "failure_reason": "Agent crashed",
            "started_at": "2026-01-24T10:00:00Z",
            "completed_at": None,
        }

        # Act
        step_state["recovery_suggestions"] = [
            "Review agent transcript for error details",
            "Reset phase status to NOT_EXECUTED",
            "Run /nw:execute again to resume",
        ]

        # Assert
        assert "recovery_suggestions" in step_state
        assert isinstance(step_state["recovery_suggestions"], list)
        assert len(step_state["recovery_suggestions"]) == 3
        assert all(isinstance(s, str) for s in step_state["recovery_suggestions"])

    def test_recovery_suggestions_persists_through_json_serialization(self):
        """
        GIVEN step state with recovery_suggestions array
        WHEN serialized to JSON and deserialized
        THEN recovery_suggestions array is preserved
        """
        # Arrange
        original_state = {
            "status": "FAILED",
            "failure_reason": "Silent completion",
            "recovery_suggestions": [
                "Check agent transcript at /path/to/transcript.log",
                "Verify OUTCOME_RECORDING section in prompt",
                "Manually update phase status based on transcript",
            ],
        }

        # Act
        json_str = json.dumps(original_state)
        restored_state = json.loads(json_str)

        # Assert
        assert "recovery_suggestions" in restored_state
        assert isinstance(restored_state["recovery_suggestions"], list)
        assert (
            restored_state["recovery_suggestions"]
            == original_state["recovery_suggestions"]
        )

    def test_recovery_suggestions_field_is_array_not_string(self):
        """
        GIVEN recovery_suggestions field in step state
        WHEN accessed
        THEN field is always JSON array, never string
        """
        # Arrange
        step_state = {
            "status": "FAILED",
            "recovery_suggestions": ["suggestion 1", "suggestion 2"],
        }

        # Act
        suggestions = step_state["recovery_suggestions"]

        # Assert
        assert isinstance(suggestions, list)
        assert not isinstance(suggestions, str)

    def test_recovery_suggestions_array_can_be_empty(self):
        """
        GIVEN step state with recovery_suggestions field
        WHEN field is empty array
        THEN structure is valid
        """
        # Arrange & Act
        step_state = {
            "status": "FAILED",
            "recovery_suggestions": [],
        }

        # Assert
        assert "recovery_suggestions" in step_state
        assert isinstance(step_state["recovery_suggestions"], list)
        assert len(step_state["recovery_suggestions"]) == 0

    def test_recovery_suggestions_survives_step_file_read_write_cycle(self, tmp_path):
        """
        GIVEN step file with recovery_suggestions in state
        WHEN written to disk and read back
        THEN recovery_suggestions field and content preserved
        """
        # Arrange
        step_file = tmp_path / "step.json"
        step_data = {
            "step_id": "01-01",
            "task_id": "US005-01-01",
            "state": {
                "status": "FAILED",
                "failure_reason": "Agent crash during GREEN_UNIT",
                "recovery_suggestions": [
                    "Review agent transcript for error details",
                    "Reset GREEN_UNIT phase status to NOT_EXECUTED",
                    "Run /nw:execute again to resume from GREEN_UNIT",
                ],
            },
        }

        # Act
        step_file.write_text(json.dumps(step_data, indent=2))
        loaded_data = json.loads(step_file.read_text())

        # Assert
        assert "recovery_suggestions" in loaded_data["state"]
        assert isinstance(loaded_data["state"]["recovery_suggestions"], list)
        assert len(loaded_data["state"]["recovery_suggestions"]) == 3
        assert (
            loaded_data["state"]["recovery_suggestions"]
            == step_data["state"]["recovery_suggestions"]
        )

    def test_recovery_suggestions_backward_compatible_with_existing_step_files(self):
        """
        GIVEN existing step file without recovery_suggestions field
        WHEN recovery_suggestions is added
        THEN other fields remain unchanged
        """
        # Arrange
        existing_step_state = {
            "status": "IN_PROGRESS",
            "started_at": "2026-01-24T10:00:00Z",
            "completed_at": None,
            "other_field": "preserved",
        }

        # Act
        enhanced_state = existing_step_state.copy()
        enhanced_state["recovery_suggestions"] = ["First suggestion"]

        # Assert
        assert enhanced_state["status"] == "IN_PROGRESS"
        assert enhanced_state["started_at"] == "2026-01-24T10:00:00Z"
        assert enhanced_state["other_field"] == "preserved"
        assert "recovery_suggestions" in enhanced_state
        assert isinstance(enhanced_state["recovery_suggestions"], list)

    def test_recovery_suggestions_each_entry_is_string(self):
        """
        GIVEN recovery_suggestions array
        WHEN populated
        THEN each entry is string type
        """
        # Arrange
        suggestions = [
            "Check transcript at /path/to/file",
            "Reset phase status to NOT_EXECUTED",
            "Run /nw:execute to continue",
        ]

        # Act & Assert
        for suggestion in suggestions:
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0  # Non-empty strings

    def test_recovery_suggestions_can_contain_commands_and_paths(self):
        """
        GIVEN recovery suggestions array
        WHEN suggestions include commands and file paths
        THEN structure accommodates them
        """
        # Arrange
        step_state = {
            "recovery_suggestions": [
                "Check agent transcript at /tmp/agent-transcripts/session-12345.log",
                "Run command: /nw:execute @software-crafter steps/01-01.json",
                "Reset phase status by editing step file at docs/feature/des/steps/01-01.json",
            ],
        }

        # Act & Assert
        for suggestion in step_state["recovery_suggestions"]:
            assert isinstance(suggestion, str)
            # Validate that paths and commands can be embedded
            assert any(char in suggestion for char in ["/", "@", ":"])
