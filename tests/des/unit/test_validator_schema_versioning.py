"""
Unit tests for template validator with canonical schema v4.0.

Tests validate that validator uses canonical 5-phase TDD cycle from
step-tdd-cycle-schema.json (single source of truth).

Schema v4.0 (CURRENT): 5 phases - loaded from canonical template
- REVIEW and REFACTOR_CONTINUOUS moved to deliver level

These tests ensure validator stays synchronized with canonical template.
"""

from des.application.tdd_template_loader import (
    get_expected_phase_count,
    get_schema_version,
    get_valid_tdd_phases,
)
from des.application.validator import (
    ExecutionLogValidator,
    TDDPhaseValidator,
)


class TestTDDPhaseValidatorSchemaV4Current:
    """Tests for current schema v4.0 loaded from Single Source of Truth."""

    def test_validate_v4_0_phases_from_canonical_template(self):
        """
        GIVEN v4.0 schema prompt with phases from canonical template
        WHEN validate() called
        THEN checks for all phases from Single Source of Truth

        This test loads the canonical phase count from nWave/templates/step-tdd-cycle-schema.json
        ensuring validator and tests stay synchronized with template changes.
        """
        # GIVEN: Load canonical phase definitions from template
        canonical_phases = get_valid_tdd_phases()
        phase_count = get_expected_phase_count()
        schema_version = get_schema_version()

        # Build prompt dynamically from canonical template
        tdd_section = "# TDD_PHASES\n"
        tdd_section += f"Execute all {phase_count} phases (schema v{schema_version}):\n"
        for i, phase in enumerate(canonical_phases, 1):
            tdd_section += f"{i}. {phase}\n"

        prompt = f"""
        {tdd_section}
        """
        validator = TDDPhaseValidator()

        # WHEN: Validation performed
        errors = validator.validate(prompt)

        # THEN: No errors when all canonical phases present
        assert len(errors) == 0

    def test_validate_v4_0_execution_log_from_template(self):
        """
        GIVEN v4.0 schema execution log with phases from canonical template
        WHEN validate() called with current schema version
        THEN validates successfully

        This test builds the phase log dynamically from the canonical template.
        """
        # GIVEN: Load canonical phase definitions
        canonical_phases = get_valid_tdd_phases()
        schema_version = get_schema_version()

        # Build phase log dynamically from canonical template
        phase_log = [
            {"phase_name": phase, "status": "EXECUTED", "outcome": "PASS"}
            for phase in canonical_phases
        ]

        validator = ExecutionLogValidator()

        # WHEN: Validation with current schema version
        errors = validator.validate(phase_log, schema_version=schema_version)

        # THEN: No errors for valid current schema log
        assert len(errors) == 0

    def test_canonical_template_has_expected_phase_count(self):
        """
        GIVEN canonical template loaded
        WHEN get_expected_phase_count() called
        THEN returns 5 phases for schema v4.0

        This test verifies the template loader is working correctly.
        If this fails, the canonical template may have changed or is not loading properly.
        """
        # GIVEN/WHEN: Load canonical phase count
        phase_count = get_expected_phase_count()

        # THEN: Current schema v4.0 has 5 phases
        assert phase_count == 5

    def test_canonical_template_has_schema_v4(self):
        """
        GIVEN canonical template loaded
        WHEN get_schema_version() called
        THEN returns "4.0"

        This test verifies we're using the correct schema version.
        """
        # GIVEN/WHEN: Load schema version
        schema_version = get_schema_version()

        # THEN: Current schema is v4.0
        assert schema_version == "4.0"
