"""
Unit tests for DESOrchestrator schema version detection and routing.

Tests validate that orchestrator correctly:
1. Detects schema version from step files (v1.0 vs v2.0)
2. Routes to appropriate validator based on detected version
3. Supports mixed-schema during US-005 Phase 2→3 transition
4. Maps phase counts correctly (14 for v1.0, 8 for v2.0)

These tests drive implementation for Step US-005-03 schema versioning.
"""

from pathlib import Path


class TestSchemaVersionDetection:
    """Unit tests for schema version detection in DESOrchestrator."""

    def test_detect_schema_version_v2_0_from_step_file(
        self, des_orchestrator, in_memory_filesystem
    ):
        """
        GIVEN step file with schema_version: "2.0"
        WHEN detect_schema_version() called
        THEN returns "2.0"

        This enables routing to 8-phase validator.
        """
        # GIVEN: Step file with v2.0 schema
        step_file_path = Path("/tmp/step-v2.json")
        step_data = {
            "schema_version": "2.0",
            "task_id": "01-01",
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "NOT_EXECUTED"},
                    {"phase_name": "RED_ACCEPTANCE", "status": "NOT_EXECUTED"},
                    {"phase_name": "RED_UNIT", "status": "NOT_EXECUTED"},
                    {"phase_name": "GREEN", "status": "NOT_EXECUTED"},
                    {"phase_name": "REVIEW", "status": "NOT_EXECUTED"},
                    {"phase_name": "REFACTOR_CONTINUOUS", "status": "NOT_EXECUTED"},
                    {"phase_name": "REFACTOR_L4", "status": "NOT_EXECUTED"},
                    {"phase_name": "COMMIT", "status": "NOT_EXECUTED"},
                ]
            },
        }
        in_memory_filesystem.write_json(step_file_path, step_data)

        # WHEN: detect_schema_version() called
        detected_version = des_orchestrator.detect_schema_version(step_file_path)

        # THEN: v2.0 returned
        assert detected_version == "2.0"

    def test_detect_schema_version_v1_0_default_when_missing(
        self, des_orchestrator, in_memory_filesystem
    ):
        """
        GIVEN step file WITHOUT schema_version field
        WHEN detect_schema_version() called
        THEN returns "1.0" (backward compatibility default)

        This ensures legacy step files (US-005 Phase 2) work correctly.
        """
        # GIVEN: Step file without schema_version (legacy)
        step_file_path = Path("/tmp/step-legacy.json")
        step_data = {
            "task_id": "02-01",
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "NOT_EXECUTED"},
                    {"phase_name": "RED_ACCEPTANCE", "status": "NOT_EXECUTED"},
                    # ... 14 phases total
                ]
            },
        }
        in_memory_filesystem.write_json(step_file_path, step_data)

        # WHEN: detect_schema_version() called
        detected_version = des_orchestrator.detect_schema_version(step_file_path)

        # THEN: v1.0 returned as default
        assert detected_version == "1.0"

    def test_detect_schema_version_handles_nested_location(
        self, des_orchestrator, in_memory_filesystem
    ):
        """
        GIVEN step file with schema_version in tdd_cycle section
        WHEN detect_schema_version() called
        THEN detects version from nested location

        This supports multiple possible schema_version locations.
        """
        # GIVEN: Step file with schema_version nested in tdd_cycle
        step_file_path = Path("/tmp/step-nested.json")
        step_data = {
            "task_id": "03-01",
            "tdd_cycle": {
                "schema_version": "2.0",  # Nested location
                "phase_execution_log": [
                    {"phase_name": "PREPARE", "status": "NOT_EXECUTED"},
                    # ... 8 phases
                ],
            },
        }
        in_memory_filesystem.write_json(step_file_path, step_data)

        # WHEN: detect_schema_version() called
        detected_version = des_orchestrator.detect_schema_version(step_file_path)

        # THEN: v2.0 detected from nested location
        assert detected_version == "2.0"


class TestPhaseCountMapping:
    """Unit tests for phase count mapping based on schema version."""

    def test_get_phase_count_for_schema_v1_0_returns_14(self, des_orchestrator):
        """
        GIVEN schema_version "1.0"
        WHEN get_phase_count_for_schema() called
        THEN returns 14 (legacy TDD cycle)
        """
        # GIVEN: v1.0 schema version
        schema_version = "1.0"

        # WHEN: get_phase_count_for_schema() called
        phase_count = des_orchestrator.get_phase_count_for_schema(schema_version)

        # THEN: 14 phases returned
        assert phase_count == 14

    def test_get_phase_count_for_schema_v2_0_returns_8(self, des_orchestrator):
        """
        GIVEN schema_version "2.0"
        WHEN get_phase_count_for_schema() called
        THEN returns 8 (optimized TDD cycle)
        """
        # GIVEN: v2.0 schema version
        schema_version = "2.0"

        # WHEN: get_phase_count_for_schema() called
        phase_count = des_orchestrator.get_phase_count_for_schema(schema_version)

        # THEN: 8 phases returned
        assert phase_count == 8

    def test_get_phase_count_for_schema_unknown_defaults_to_14(self, des_orchestrator):
        """
        GIVEN unknown schema_version
        WHEN get_phase_count_for_schema() called
        THEN returns 14 (backward compatibility default)
        """
        # GIVEN: Unknown schema version
        schema_version = "3.0"  # Future version not yet supported

        # WHEN: get_phase_count_for_schema() called
        phase_count = des_orchestrator.get_phase_count_for_schema(schema_version)

        # THEN: 14 phases returned as default
        assert phase_count == 14


class TestMixedSchemaDuringTransition:
    """Unit tests for mixed-schema support during US-005 Phase 2→3 transition."""

    def test_mixed_schema_step_files_in_same_feature(
        self, des_orchestrator, in_memory_filesystem
    ):
        """
        GIVEN feature with mixed schema step files (v1.0 and v2.0)
        WHEN detect_schema_version() called on each step
        THEN each step returns correct version

        This validates backward compatibility during transition.
        Example: steps 02-04, 02-05 use v1.0; steps 03-01+ use v2.0
        """
        # GIVEN: Mixed schema steps in same feature directory
        step_v1_path = Path("/tmp/steps/02-04.json")
        step_v2_path = Path("/tmp/steps/03-01.json")

        # v1.0 step (14 phases)
        step_v1_data = {
            "task_id": "02-04",
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": f"PHASE_{i}", "status": "NOT_EXECUTED"}
                    for i in range(14)
                ]
            },
        }

        # v2.0 step (8 phases)
        step_v2_data = {
            "schema_version": "2.0",
            "task_id": "03-01",
            "tdd_cycle": {
                "phase_execution_log": [
                    {"phase_name": f"PHASE_{i}", "status": "NOT_EXECUTED"}
                    for i in range(8)
                ]
            },
        }

        in_memory_filesystem.write_json(step_v1_path, step_v1_data)
        in_memory_filesystem.write_json(step_v2_path, step_v2_data)

        # WHEN: detect_schema_version() called on each step
        version_v1 = des_orchestrator.detect_schema_version(step_v1_path)
        version_v2 = des_orchestrator.detect_schema_version(step_v2_path)

        # THEN: Each step returns correct version
        assert version_v1 == "1.0"  # v1 step detected as v1.0
        assert version_v2 == "2.0"  # v2 step detected as v2.0

        # AND: Phase counts mapped correctly
        assert des_orchestrator.get_phase_count_for_schema(version_v1) == 14
        assert des_orchestrator.get_phase_count_for_schema(version_v2) == 8
