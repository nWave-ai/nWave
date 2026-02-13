"""
Unit Tests: StaleExecution Value Object

DOMAIN LAYER: Pure value object representing a single stale execution detection.

Business Rules:
- Immutable dataclass (frozen=True)
- age_minutes must be >= 0 (business validation)
- No external dependencies (pure domain entity)
- All fields required for complete stale execution representation
"""

from dataclasses import FrozenInstanceError

import pytest


class TestStaleExecutionCreation:
    """Test StaleExecution value object creation and immutability."""

    def test_create_stale_execution_with_valid_data(self):
        """
        GIVEN valid stale execution data
        WHEN creating StaleExecution value object
        THEN object is created with all fields set correctly
        """
        from des.domain.stale_execution import StaleExecution

        stale_exec = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )

        assert stale_exec.step_file == "steps/01-01.json"
        assert stale_exec.phase_name == "RED_UNIT"
        assert stale_exec.age_minutes == 45
        assert stale_exec.started_at == "2026-01-31T10:00:00Z"

    def test_stale_execution_is_immutable(self):
        """
        GIVEN a StaleExecution value object
        WHEN attempting to modify any field
        THEN FrozenInstanceError is raised (dataclass frozen=True)
        """
        from des.domain.stale_execution import StaleExecution

        stale_exec = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )

        with pytest.raises(FrozenInstanceError):
            stale_exec.age_minutes = 50

    def test_create_stale_execution_with_zero_age(self):
        """
        GIVEN age_minutes = 0 (boundary case)
        WHEN creating StaleExecution
        THEN object is created successfully (0 is valid)
        """
        from des.domain.stale_execution import StaleExecution

        stale_exec = StaleExecution(
            step_file="steps/02-01.json",
            phase_name="GREEN",
            age_minutes=0,
            started_at="2026-01-31T11:00:00Z",
        )

        assert stale_exec.age_minutes == 0


class TestStaleExecutionBusinessValidation:
    """Test StaleExecution business validation rules."""

    def test_negative_age_minutes_raises_validation_error(self):
        """
        GIVEN age_minutes < 0 (invalid business rule)
        WHEN creating StaleExecution
        THEN ValueError is raised with descriptive message
        """
        from des.domain.stale_execution import StaleExecution

        with pytest.raises(ValueError) as exc_info:
            StaleExecution(
                step_file="steps/01-01.json",
                phase_name="RED_UNIT",
                age_minutes=-10,
                started_at="2026-01-31T10:00:00Z",
            )

        assert "age_minutes must be >= 0" in str(exc_info.value)

    def test_large_age_minutes_is_valid(self):
        """
        GIVEN very large age_minutes (e.g., 1440 minutes = 24 hours)
        WHEN creating StaleExecution
        THEN object is created successfully (no upper bound limit)
        """
        from des.domain.stale_execution import StaleExecution

        stale_exec = StaleExecution(
            step_file="steps/03-01.json",
            phase_name="REFACTOR_L2",
            age_minutes=1440,
            started_at="2026-01-30T11:00:00Z",
        )

        assert stale_exec.age_minutes == 1440


class TestStaleExecutionEquality:
    """Test StaleExecution value object equality semantics."""

    def test_stale_executions_with_same_values_are_equal(self):
        """
        GIVEN two StaleExecution objects with identical field values
        WHEN comparing for equality
        THEN they are considered equal (value object semantics)
        """
        from des.domain.stale_execution import StaleExecution

        stale1 = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )

        stale2 = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )

        assert stale1 == stale2

    def test_stale_executions_with_different_values_are_not_equal(self):
        """
        GIVEN two StaleExecution objects with different field values
        WHEN comparing for equality
        THEN they are not equal
        """
        from des.domain.stale_execution import StaleExecution

        stale1 = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )

        stale2 = StaleExecution(
            step_file="steps/02-01.json",
            phase_name="GREEN",
            age_minutes=60,
            started_at="2026-01-31T09:00:00Z",
        )

        assert stale1 != stale2


class TestStaleExecutionStringRepresentation:
    """Test StaleExecution string representation for debugging and logging."""

    def test_stale_execution_has_readable_repr(self):
        """
        GIVEN a StaleExecution value object
        WHEN converting to string representation
        THEN repr contains all field values for debugging
        """
        from des.domain.stale_execution import StaleExecution

        stale_exec = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )

        repr_str = repr(stale_exec)

        assert "StaleExecution" in repr_str
        assert "steps/01-01.json" in repr_str
        assert "RED_UNIT" in repr_str
        assert "45" in repr_str


class TestStaleExecutionFieldTypes:
    """Test StaleExecution field type enforcement and edge cases."""

    def test_step_file_can_contain_nested_path(self):
        """
        GIVEN step_file with nested directory path
        WHEN creating StaleExecution
        THEN object is created successfully (supports any valid file path)
        """
        from des.domain.stale_execution import StaleExecution

        stale_exec = StaleExecution(
            step_file="projects/feature-x/steps/05-02.json",
            phase_name="COMMIT",
            age_minutes=30,
            started_at="2026-01-31T10:30:00Z",
        )

        assert stale_exec.step_file == "projects/feature-x/steps/05-02.json"

    def test_phase_name_supports_all_tdd_phases(self):
        """
        GIVEN various TDD phase names
        WHEN creating StaleExecution for each phase
        THEN all phase names are accepted (no enum restriction)
        """
        from des.domain.stale_execution import StaleExecution

        phase_names = [
            "PREPARE",
            "RED_ACCEPTANCE",
            "RED_UNIT",
            "GREEN",
            "REVIEW",
            "REFACTOR_CONTINUOUS",
            "REFACTOR_L4",
            "COMMIT",
        ]

        for phase_name in phase_names:
            stale_exec = StaleExecution(
                step_file="steps/01-01.json",
                phase_name=phase_name,
                age_minutes=30,
                started_at="2026-01-31T10:00:00Z",
            )
            assert stale_exec.phase_name == phase_name
