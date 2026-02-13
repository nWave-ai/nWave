"""
Unit tests for TDD Template Loader.

Tests the Single Source of Truth pattern - loading TDD phase definitions
from canonical template instead of hardcoding them.
"""

from des.application.tdd_template_loader import (
    get_expected_phase_count,
    get_phase_execution_log_template,
    get_schema_version,
    get_valid_tdd_phases,
    load_tdd_template,
)


class TestLoadTddTemplate:
    """Test canonical template loading."""

    def test_load_tdd_template_succeeds(self):
        """Template loader successfully loads canonical template JSON."""
        template = load_tdd_template()

        # Verify template structure
        assert isinstance(template, dict)
        assert "schema_version" in template
        assert "valid_tdd_phases" in template
        assert "tdd_cycle" in template

    def test_template_has_version_4_0(self):
        """Template has schema_version 4.0 as canonical version."""
        template = load_tdd_template()

        assert template["schema_version"] == "4.0"
        assert template["version"] == "4.0.0"


class TestGetSchemaVersion:
    """Test schema version extraction."""

    def test_get_schema_version_returns_4_0(self):
        """Schema version extracted from template is 4.0."""
        version = get_schema_version()

        assert version == "4.0"


class TestGetValidTddPhases:
    """Test valid phase list extraction."""

    def test_get_valid_tdd_phases_returns_5_phases(self):
        """Valid phase list contains exactly 5 execution phases (excluding meta-phases)."""
        phases = get_valid_tdd_phases()

        # Schema v4.0 has 5 execution phases
        assert len(phases) == 5

    def test_phases_exclude_meta_phases(self):
        """NOT_STARTED and COMPLETED meta-phases are excluded from execution phases."""
        phases = get_valid_tdd_phases()

        assert "NOT_STARTED" not in phases
        assert "COMPLETED" not in phases

    def test_phases_include_canonical_v4_phases(self):
        """Phase list includes all canonical v4.0 execution phases."""
        phases = get_valid_tdd_phases()

        expected_phases = [
            "PREPARE",
            "RED_ACCEPTANCE",
            "RED_UNIT",
            "GREEN",
            "COMMIT",
        ]

        assert phases == expected_phases


class TestGetExpectedPhaseCount:
    """Test phase count calculation."""

    def test_get_expected_phase_count_returns_5(self):
        """Expected phase count matches canonical v4.0 schema (5 phases)."""
        count = get_expected_phase_count()

        assert count == 5


class TestGetPhaseExecutionLogTemplate:
    """Test phase execution log template extraction."""

    def test_get_phase_execution_log_template_returns_list(self):
        """Phase execution log template is a list of phase definitions."""
        log_template = get_phase_execution_log_template()

        assert isinstance(log_template, list)
        assert len(log_template) == 5  # v4.0 has 5 phases

    def test_each_phase_has_required_fields(self):
        """Each phase definition has required metadata fields."""
        log_template = get_phase_execution_log_template()

        for phase in log_template:
            assert "phase_name" in phase
            assert "phase_index" in phase
            assert "status" in phase

    def test_phase_indices_are_sequential(self):
        """Phase indices are sequential starting from 0."""
        log_template = get_phase_execution_log_template()

        for i, phase in enumerate(log_template):
            assert phase["phase_index"] == i


class TestTemplateCaching:
    """Test template caching behavior."""

    def test_template_caching_works(self):
        """Template is cached - multiple calls return same instance."""
        template1 = load_tdd_template()
        template2 = load_tdd_template()

        # Same instance due to lru_cache
        assert template1 is template2
