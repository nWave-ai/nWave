"""
Unit Tests: StaleDetectionResult Entity

Tests the StaleDetectionResult domain entity that aggregates multiple
StaleExecution instances and provides blocking logic and alert formatting.

Business Rules:
- Aggregates StaleExecution instances (uses value object from step 01-01)
- is_blocked = True if stale_executions list is not empty
- Alert message format: 'Stale execution found: {step_file}, phase {phase_name} ({age} min)'
- Multiple stale executions supported
"""

from des.domain.stale_detection_result import StaleDetectionResult
from des.domain.stale_execution import StaleExecution


class TestStaleDetectionResultShould:
    """Unit tests for StaleDetectionResult entity."""

    # =========================================================================
    # Test Group 1: Construction and Basic Properties
    # =========================================================================

    def test_create_result_with_empty_stale_executions_list(self):
        """
        GIVEN no stale executions detected
        WHEN StaleDetectionResult is created with empty list
        THEN result is created successfully with empty list
        """
        result = StaleDetectionResult(stale_executions=[])

        assert result.stale_executions == []

    def test_create_result_with_single_stale_execution(self):
        """
        GIVEN one stale execution detected
        WHEN StaleDetectionResult is created with one StaleExecution
        THEN result contains the stale execution
        """
        stale = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )

        result = StaleDetectionResult(stale_executions=[stale])

        assert len(result.stale_executions) == 1
        assert result.stale_executions[0] == stale

    def test_create_result_with_multiple_stale_executions(self):
        """
        GIVEN multiple stale executions detected
        WHEN StaleDetectionResult is created with multiple StaleExecution instances
        THEN result contains all stale executions in order
        """
        stale1 = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )
        stale2 = StaleExecution(
            step_file="steps/02-01.json",
            phase_name="GREEN_UNIT",
            age_minutes=60,
            started_at="2026-01-31T09:00:00Z",
        )
        stale3 = StaleExecution(
            step_file="steps/03-01.json",
            phase_name="REFACTOR_L1",
            age_minutes=30,
            started_at="2026-01-31T10:30:00Z",
        )

        result = StaleDetectionResult(stale_executions=[stale1, stale2, stale3])

        assert len(result.stale_executions) == 3
        assert result.stale_executions[0] == stale1
        assert result.stale_executions[1] == stale2
        assert result.stale_executions[2] == stale3

    # =========================================================================
    # Test Group 2: Blocking Logic (is_blocked property)
    # =========================================================================

    def test_is_blocked_returns_false_when_no_stale_executions(self):
        """
        GIVEN no stale executions detected
        WHEN is_blocked is checked
        THEN returns False (execution not blocked)
        """
        result = StaleDetectionResult(stale_executions=[])

        assert result.is_blocked is False

    def test_is_blocked_returns_true_when_one_stale_execution_exists(self):
        """
        GIVEN one stale execution detected
        WHEN is_blocked is checked
        THEN returns True (execution should be blocked)
        """
        stale = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )
        result = StaleDetectionResult(stale_executions=[stale])

        assert result.is_blocked is True

    def test_is_blocked_returns_true_when_multiple_stale_executions_exist(self):
        """
        GIVEN multiple stale executions detected
        WHEN is_blocked is checked
        THEN returns True (execution should be blocked)
        """
        stale1 = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )
        stale2 = StaleExecution(
            step_file="steps/02-01.json",
            phase_name="GREEN_UNIT",
            age_minutes=60,
            started_at="2026-01-31T09:00:00Z",
        )
        result = StaleDetectionResult(stale_executions=[stale1, stale2])

        assert result.is_blocked is True

    # =========================================================================
    # Test Group 3: Alert Message Formatting (Single Stale Execution)
    # =========================================================================

    def test_alert_message_format_for_single_stale_execution(self):
        """
        GIVEN one stale execution detected
        WHEN alert_message is requested
        THEN returns formatted message with step_file, phase_name, and age
        Format: 'Stale execution found: {step_file}, phase {phase_name} ({age} min)'
        """
        stale = StaleExecution(
            step_file="steps/03-02.json",
            phase_name="REFACTOR_L2",
            age_minutes=60,
            started_at="2026-01-31T09:00:00Z",
        )
        result = StaleDetectionResult(stale_executions=[stale])

        expected_message = (
            "Stale execution found: steps/03-02.json, phase REFACTOR_L2 (60 min)"
        )
        assert result.alert_message == expected_message

    def test_alert_message_includes_step_file_path(self):
        """
        GIVEN stale execution with specific step file
        WHEN alert_message is requested
        THEN message includes exact step file path
        """
        stale = StaleExecution(
            step_file="steps/feature-x/01-01.json",
            phase_name="GREEN_UNIT",
            age_minutes=90,
            started_at="2026-01-31T08:30:00Z",
        )
        result = StaleDetectionResult(stale_executions=[stale])

        assert "steps/feature-x/01-01.json" in result.alert_message

    def test_alert_message_includes_phase_name(self):
        """
        GIVEN stale execution with specific phase
        WHEN alert_message is requested
        THEN message includes exact phase name
        """
        stale = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="POST_REFACTOR_REVIEW",
            age_minutes=120,
            started_at="2026-01-31T08:00:00Z",
        )
        result = StaleDetectionResult(stale_executions=[stale])

        assert "phase POST_REFACTOR_REVIEW" in result.alert_message

    def test_alert_message_includes_age_in_minutes(self):
        """
        GIVEN stale execution with specific age
        WHEN alert_message is requested
        THEN message includes age with 'min' suffix
        """
        stale = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=75,
            started_at="2026-01-31T08:45:00Z",
        )
        result = StaleDetectionResult(stale_executions=[stale])

        assert "(75 min)" in result.alert_message

    # =========================================================================
    # Test Group 4: Alert Message for Multiple Stale Executions
    # =========================================================================

    def test_alert_message_for_multiple_stale_executions_combines_all(self):
        """
        GIVEN multiple stale executions detected
        WHEN alert_message is requested
        THEN returns combined message with all stale execution details
        """
        stale1 = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )
        stale2 = StaleExecution(
            step_file="steps/02-01.json",
            phase_name="GREEN_UNIT",
            age_minutes=60,
            started_at="2026-01-31T09:00:00Z",
        )
        result = StaleDetectionResult(stale_executions=[stale1, stale2])

        alert = result.alert_message

        # All stale executions should be included
        assert "steps/01-01.json" in alert
        assert "RED_UNIT" in alert
        assert "(45 min)" in alert
        assert "steps/02-01.json" in alert
        assert "GREEN_UNIT" in alert
        assert "(60 min)" in alert

    def test_alert_message_empty_when_no_stale_executions(self):
        """
        GIVEN no stale executions
        WHEN alert_message is requested
        THEN returns empty string (no alert needed)
        """
        result = StaleDetectionResult(stale_executions=[])

        assert result.alert_message == ""

    # =========================================================================
    # Test Group 5: Business Invariants and Edge Cases
    # =========================================================================

    def test_stale_executions_list_is_immutable_after_creation(self):
        """
        GIVEN StaleDetectionResult created with stale executions
        WHEN attempting to modify the stale_executions list directly
        THEN modification should not affect the original result
        (This tests immutability principle for domain entities)
        """
        stale = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="RED_UNIT",
            age_minutes=45,
            started_at="2026-01-31T10:00:00Z",
        )
        original_list = [stale]
        result = StaleDetectionResult(stale_executions=original_list)

        # Modify the original list
        original_list.append(
            StaleExecution(
                step_file="steps/02-01.json",
                phase_name="GREEN",
                age_minutes=30,
                started_at="2026-01-31T10:30:00Z",
            )
        )

        # Result should not be affected if properly encapsulated
        assert len(result.stale_executions) == 1

    def test_handles_zero_age_stale_execution(self):
        """
        GIVEN stale execution with zero age (just started)
        WHEN StaleDetectionResult is created
        THEN result includes it and formats alert correctly
        """
        stale = StaleExecution(
            step_file="steps/01-01.json",
            phase_name="PREPARE",
            age_minutes=0,
            started_at="2026-01-31T10:00:00Z",
        )
        result = StaleDetectionResult(stale_executions=[stale])

        assert result.is_blocked is True
        assert "(0 min)" in result.alert_message
