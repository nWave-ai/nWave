"""
Unit Tests: Invocation Limits Validator

Tests for pre-invocation validation of turn/timeout configuration in step files.
"""

import json


class TestInvocationLimitsValidator:
    """Unit tests for InvocationLimitsValidator."""

    def test_missing_both_limits_returns_validation_error(self, tmp_path):
        """
        GIVEN step file without max_turns or duration_minutes
        WHEN validator checks limits
        THEN validation fails with errors for both missing fields
        """
        # GIVEN
        step_file = tmp_path / "step.json"
        step_data = {"task_id": "01-01", "tdd_cycle": {"phase_execution_log": []}}
        step_file.write_text(json.dumps(step_data))

        # WHEN
        from des.domain.invocation_limits_validator import InvocationLimitsValidator

        validator = InvocationLimitsValidator()
        result = validator.validate_limits(step_file)

        # THEN
        assert result.is_valid is False
        assert len(result.errors) >= 2
        errors_text = " ".join(result.errors).lower()
        assert "max_turns" in errors_text
        assert "duration_minutes" in errors_text

    def test_missing_max_turns_only_returns_specific_error(self, tmp_path):
        """
        GIVEN step file with duration_minutes but no max_turns
        WHEN validator checks limits
        THEN validation fails with error about missing max_turns
        """
        # GIVEN
        step_file = tmp_path / "step.json"
        step_data = {
            "task_id": "01-01",
            "tdd_cycle": {"duration_minutes": 30, "phase_execution_log": []},
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN
        from des.domain.invocation_limits_validator import InvocationLimitsValidator

        validator = InvocationLimitsValidator()
        result = validator.validate_limits(step_file)

        # THEN
        assert result.is_valid is False
        assert any("max_turns" in error.lower() for error in result.errors)

    def test_missing_duration_minutes_only_returns_specific_error(self, tmp_path):
        """
        GIVEN step file with max_turns but no duration_minutes
        WHEN validator checks limits
        THEN validation fails with error about missing duration_minutes
        """
        # GIVEN
        step_file = tmp_path / "step.json"
        step_data = {
            "task_id": "01-01",
            "tdd_cycle": {"max_turns": 50, "phase_execution_log": []},
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN
        from des.domain.invocation_limits_validator import InvocationLimitsValidator

        validator = InvocationLimitsValidator()
        result = validator.validate_limits(step_file)

        # THEN
        assert result.is_valid is False
        assert any("duration_minutes" in error.lower() for error in result.errors)

    def test_negative_max_turns_returns_invalid_error(self, tmp_path):
        """
        GIVEN step file with negative max_turns
        WHEN validator checks limits
        THEN validation fails with error about invalid value
        """
        # GIVEN
        step_file = tmp_path / "step.json"
        step_data = {
            "task_id": "01-01",
            "tdd_cycle": {
                "max_turns": -1,
                "duration_minutes": 30,
                "phase_execution_log": [],
            },
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN
        from des.domain.invocation_limits_validator import InvocationLimitsValidator

        validator = InvocationLimitsValidator()
        result = validator.validate_limits(step_file)

        # THEN
        assert result.is_valid is False
        assert any(
            "max_turns" in error.lower()
            and (
                "negative" in error.lower()
                or "invalid" in error.lower()
                or "positive" in error.lower()
            )
            for error in result.errors
        )

    def test_zero_duration_minutes_returns_invalid_error(self, tmp_path):
        """
        GIVEN step file with zero duration_minutes
        WHEN validator checks limits
        THEN validation fails with error about invalid value
        """
        # GIVEN
        step_file = tmp_path / "step.json"
        step_data = {
            "task_id": "01-01",
            "tdd_cycle": {
                "max_turns": 50,
                "duration_minutes": 0,
                "phase_execution_log": [],
            },
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN
        from des.domain.invocation_limits_validator import InvocationLimitsValidator

        validator = InvocationLimitsValidator()
        result = validator.validate_limits(step_file)

        # THEN
        assert result.is_valid is False
        assert any(
            "duration_minutes" in error.lower()
            and (
                "zero" in error.lower()
                or "invalid" in error.lower()
                or "positive" in error.lower()
            )
            for error in result.errors
        )

    def test_valid_limits_pass_validation(self, tmp_path):
        """
        GIVEN step file with valid max_turns and duration_minutes
        WHEN validator checks limits
        THEN validation passes with no errors
        """
        # GIVEN
        step_file = tmp_path / "step.json"
        step_data = {
            "task_id": "01-01",
            "tdd_cycle": {
                "max_turns": 50,
                "duration_minutes": 30,
                "phase_execution_log": [],
            },
        }
        step_file.write_text(json.dumps(step_data))

        # WHEN
        from des.domain.invocation_limits_validator import InvocationLimitsValidator

        validator = InvocationLimitsValidator()
        result = validator.validate_limits(step_file)

        # THEN
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validation_includes_guidance_on_error(self, tmp_path):
        """
        GIVEN step file with missing limits
        WHEN validator checks limits
        THEN result includes guidance on how to configure limits
        """
        # GIVEN
        step_file = tmp_path / "step.json"
        step_data = {"task_id": "01-01", "tdd_cycle": {"phase_execution_log": []}}
        step_file.write_text(json.dumps(step_data))

        # WHEN
        from des.domain.invocation_limits_validator import InvocationLimitsValidator

        validator = InvocationLimitsValidator()
        result = validator.validate_limits(step_file)

        # THEN
        assert result.is_valid is False
        assert result.guidance is not None
        assert len(result.guidance) > 0

        guidance_text = " ".join(result.guidance).lower()
        assert "tdd_cycle" in guidance_text or "configure" in guidance_text
