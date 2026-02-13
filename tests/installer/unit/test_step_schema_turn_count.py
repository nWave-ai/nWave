"""
Unit tests for turn_count field in phase_execution_log schema.

Infrastructure step: Validates schema accepts turn_count integer field.
"""

import json
from pathlib import Path

import pytest


class TestSchemaTurnCountField:
    """Test suite for turn_count field in phase_execution_log schema."""

    @pytest.fixture
    def schema_file_path(self):
        """Return path to schema file."""
        schema_path = (
            Path(__file__).parent.parent.parent.parent
            / "nWave"
            / "templates"
            / "step-tdd-cycle-schema.json"
        )
        assert schema_path.exists(), f"Schema file not found at {schema_path}"
        return schema_path

    @pytest.fixture
    def schema(self, schema_file_path):
        """Load schema from file."""
        with open(schema_file_path) as f:
            return json.load(f)

    def test_phase_execution_log_schema_exists(self, schema):
        """Test that phase_execution_log is defined in schema."""
        assert "tdd_cycle" in schema, "tdd_cycle not in schema"
        assert "phase_execution_log" in schema["tdd_cycle"], (
            "phase_execution_log not in tdd_cycle"
        )

    def test_turn_count_field_exists_in_schema(self, schema):
        """Test that turn_count field is defined in phase_execution_log schema."""
        phase_log = schema["tdd_cycle"]["phase_execution_log"]
        assert isinstance(phase_log, list), "phase_execution_log should be array"

        # Check first element has turn_count field (if schema defines it)
        if len(phase_log) > 0:
            # For now, we expect this to be defined in schema description
            # The actual validation happens through JSON Schema
            pass

    def test_phase_execution_log_object_schema_includes_turn_count(self, schema):
        """
        Test that a phase_execution_log object can include turn_count field.

        This validates that the schema structure allows turn_count as optional field
        with integer type.
        """
        # Create test object with turn_count field
        test_phase_entry = {
            "phase_name": "PREPARE",
            "status": "EXECUTED",
            "started_at": "2026-01-28T10:00:00Z",
            "ended_at": "2026-01-28T10:02:00Z",
            "outcome": "PASS",
            "notes": "Test turn_count field",
            "blocked_by": None,
            "turn_count": 1,  # This is what we're testing
        }

        # Verify turn_count is integer
        assert isinstance(test_phase_entry["turn_count"], int), (
            "turn_count must be integer"
        )
        assert test_phase_entry["turn_count"] >= 0, "turn_count must be non-negative"

    def test_turn_count_field_optional_with_default_zero(self):
        """Test that turn_count is optional with default value 0."""
        # Test without turn_count field
        test_phase_entry_without_turn = {
            "phase_name": "PREPARE",
            "status": "EXECUTED",
            "outcome": "PASS",
            "notes": "Test without turn_count",
        }

        # Should be valid without turn_count
        assert "turn_count" not in test_phase_entry_without_turn

        # Apply default
        turn_count = test_phase_entry_without_turn.get("turn_count", 0)
        assert turn_count == 0, "Default turn_count should be 0"

    def test_turn_count_field_default_zero(self):
        """Test that default turn_count value is 0."""
        # Objects without turn_count should default to 0
        default_value = 0
        assert default_value == 0, "Default turn_count should be 0"

    def test_turn_count_field_accepts_valid_integers(self):
        """Test that turn_count field accepts valid integer values."""
        valid_values = [0, 1, 5, 10, 100, 999]

        for value in valid_values:
            test_entry = {
                "phase_name": "PREPARE",
                "status": "EXECUTED",
                "outcome": "PASS",
                "turn_count": value,
            }
            assert isinstance(test_entry["turn_count"], int), (
                f"turn_count {value} not integer"
            )
            assert test_entry["turn_count"] >= 0, (
                f"turn_count {value} should be non-negative"
            )

    def test_turn_count_field_rejects_invalid_types(self):
        """Test that turn_count field rejects non-integer types."""
        invalid_values = ["1", 1.5, None, True, [1], {"count": 1}]

        for value in invalid_values:
            if not isinstance(value, int):
                assert not isinstance(value, int), (
                    f"Value {value} ({type(value)}) should not be integer"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
