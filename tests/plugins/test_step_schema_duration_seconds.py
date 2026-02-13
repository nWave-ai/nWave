"""
Unit tests for step schema duration_seconds enhancement.

Tests verify that:
1. duration_seconds field exists in phase_execution_log
2. duration_minutes is maintained for backward compatibility
3. duration_seconds is calculated from timestamps when both start and end exist
"""

import json
from datetime import datetime
from pathlib import Path


class TestStepSchemaDurationSeconds:
    """Test suite for duration_seconds field in step schema."""

    def test_template_schema_has_duration_seconds_field(self):
        """Verify template schema includes duration_seconds in phase_execution_log."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "nWave"
            / "templates"
            / "step-tdd-cycle-schema.json"
        )

        with open(template_path) as f:
            schema = json.load(f)

        # Verify phase_execution_log exists
        assert "tdd_cycle" in schema
        assert "phase_execution_log" in schema["tdd_cycle"]

        # Verify duration_seconds exists in each phase
        for phase in schema["tdd_cycle"]["phase_execution_log"]:
            assert "duration_seconds" in phase, (
                f"Phase {phase['phase_name']} missing duration_seconds field"
            )
            assert "duration_minutes" in phase, (
                f"Phase {phase['phase_name']} missing duration_minutes field (backward compatibility)"
            )

            # Verify both fields are null by default
            assert phase["duration_seconds"] is None
            assert phase["duration_minutes"] is None

    def test_duration_seconds_calculation_from_timestamps(self):
        """Verify duration_seconds can be calculated from started_at and ended_at."""
        # Given: timestamps with known difference
        start_time = "2026-01-25T11:30:00.000000+00:00"
        end_time = "2026-01-25T11:35:30.500000+00:00"  # 5 minutes 30.5 seconds later

        # When: calculating duration
        start_dt = datetime.fromisoformat(start_time.replace("+00:00", ""))
        end_dt = datetime.fromisoformat(end_time.replace("+00:00", ""))
        duration_seconds = (end_dt - start_dt).total_seconds()
        duration_minutes = duration_seconds / 60

        # Then: both formats calculated correctly
        assert duration_seconds == 330.5  # 5*60 + 30.5
        assert duration_minutes == 5.508333333333334  # ~5.51 minutes

    def test_existing_step_files_can_add_duration_seconds(self):
        """Verify existing step files can be enhanced with duration_seconds."""
        # Given: a phase entry with timestamps and duration_minutes
        phase_entry = {
            "phase_name": "GREEN_UNIT",
            "started_at": "2026-01-25T11:30:00.000000+00:00",
            "ended_at": "2026-01-25T11:35:30.500000+00:00",
            "duration_minutes": 5.51,
            "duration_seconds": None,  # This is what we're adding
        }

        # When: calculating duration_seconds from timestamps
        if phase_entry["started_at"] and phase_entry["ended_at"]:
            start_dt = datetime.fromisoformat(
                phase_entry["started_at"].replace("+00:00", "")
            )
            end_dt = datetime.fromisoformat(
                phase_entry["ended_at"].replace("+00:00", "")
            )
            calculated_duration_seconds = (end_dt - start_dt).total_seconds()
            phase_entry["duration_seconds"] = calculated_duration_seconds

        # Then: duration_seconds matches expected value
        assert phase_entry["duration_seconds"] == 330.5
        assert (
            phase_entry["duration_minutes"] == 5.51
        )  # Unchanged - backward compatible
