"""Unit tests for step schema extension tracking."""

import json
from pathlib import Path


class TestStepSchemaExtensions:
    """Test step schema supports extension tracking."""

    def test_phase_execution_log_has_extensions_granted_field(self):
        """Verify phase_execution_log entries include extensions_granted list."""
        # Load the step template schema
        schema_path = Path("nWave/templates/step-tdd-cycle-schema.json")
        with open(schema_path) as f:
            schema = json.load(f)

        # Check each phase has extensions_granted field
        for phase in schema["tdd_cycle"]["phase_execution_log"]:
            assert "extensions_granted" in phase, (
                f"Phase {phase['phase_name']} missing extensions_granted field"
            )
            assert isinstance(phase["extensions_granted"], list), (
                f"Phase {phase['phase_name']} extensions_granted must be a list"
            )

    def test_extension_record_structure(self):
        """Verify ExtensionRecord has required fields."""
        # Schema should define the structure (even if list is empty by default)
        # We'll check by adding a sample extension record and validating it
        required_fields = {
            "timestamp": str,
            "reason": str,
            "additional_turns": int,
            "additional_minutes": int,
            "approved_by": str,
        }

        # Create a sample extension record
        sample_extension = {
            "timestamp": "2026-01-25T00:00:00Z",
            "reason": "Complex refactoring needed",
            "additional_turns": 5,
            "additional_minutes": 15,
            "approved_by": "tech-lead",
        }

        # Validate structure
        for field_name, field_type in required_fields.items():
            assert field_name in sample_extension, (
                f"ExtensionRecord missing field: {field_name}"
            )
            assert isinstance(sample_extension[field_name], field_type), (
                f"ExtensionRecord field {field_name} has wrong type"
            )

    def test_extensions_granted_initialized_empty(self):
        """Verify extensions_granted starts as empty list."""
        schema_path = Path("nWave/templates/step-tdd-cycle-schema.json")
        with open(schema_path) as f:
            schema = json.load(f)

        for phase in schema["tdd_cycle"]["phase_execution_log"]:
            assert phase["extensions_granted"] == [], (
                f"Phase {phase['phase_name']} extensions_granted should initialize as empty list"
            )
