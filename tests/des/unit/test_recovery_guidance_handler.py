"""
Unit tests for RecoveryGuidanceHandler.

Tests the core recovery guidance generation and persistence functionality.
"""

import json

import pytest

from des.application.recovery_guidance_handler import RecoveryGuidanceHandler


class TestRecoveryGuidanceHandlerInstantiation:
    """Test RecoveryGuidanceHandler instantiation."""

    def test_instantiate_without_errors(self):
        """Should instantiate RecoveryGuidanceHandler without errors."""
        handler = RecoveryGuidanceHandler()
        assert handler is not None
        assert isinstance(handler, RecoveryGuidanceHandler)


class TestGenerateRecoverySuggestions:
    """Test generate_recovery_suggestions method."""

    def test_generate_suggestions_for_abandoned_phase(self):
        """Should generate suggestions for abandoned_phase failure mode."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type="abandoned_phase",
            context={
                "phase": "GREEN_UNIT",
                "step_file": "steps/01-01.json",
            },
        )

        assert suggestions is not None
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        # Each suggestion should be a string
        assert all(isinstance(s, str) for s in suggestions)

    def test_generate_suggestions_for_silent_completion(self):
        """Should generate suggestions for silent_completion failure mode."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type="silent_completion",
            context={
                "step_file": "steps/01-01.json",
                "transcript_path": "/tmp/transcript.log",
            },
        )

        assert suggestions is not None
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert all(isinstance(s, str) for s in suggestions)

    def test_suggestions_include_actionable_elements_abandoned_phase(self):
        """Suggestions should include actionable elements for abandoned phase."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type="abandoned_phase",
            context={
                "phase": "RED_UNIT",
                "step_file": "steps/01-01.json",
            },
        )

        # At least one should mention transcript
        has_transcript_ref = any("transcript" in s.lower() for s in suggestions)
        assert has_transcript_ref, "Should reference transcript"

        # At least one should mention phase name
        has_phase_ref = any("RED_UNIT" in s for s in suggestions)
        assert has_phase_ref, "Should reference the phase name"

        # At least one should mention NOT_EXECUTED or execution command
        has_execution_ref = any(
            "NOT_EXECUTED" in s or "/nw:execute" in s or "execute" in s.lower()
            for s in suggestions
        )
        assert has_execution_ref, "Should reference execution or phase status"

    def test_suggestions_include_actionable_elements_with_transcript_path(self):
        """Suggestions should include specific transcript path when provided."""
        handler = RecoveryGuidanceHandler()
        transcript_path = "/tmp/transcripts/agent-123.log"
        suggestions = handler.generate_recovery_suggestions(
            failure_type="abandoned_phase",
            context={
                "phase": "GREEN_UNIT",
                "transcript_path": transcript_path,
            },
        )

        # At least one should include the specific transcript path
        has_path = any(transcript_path in s for s in suggestions)
        assert has_path, f"Should reference specific transcript path: {transcript_path}"


class TestFormatSuggestion:
    """Test format_suggestion method."""

    def test_format_suggestion_creates_formatted_string(self):
        """Should create properly formatted suggestion from components."""
        handler = RecoveryGuidanceHandler()

        formatted = handler.format_suggestion(
            why_text="The agent crashed during phase execution",
            how_text="Reset the phase status to NOT_EXECUTED and retry",
            actionable_command="/nw:execute @software-crafter 'steps/01-01.json'",
        )

        assert formatted is not None
        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_formatted_suggestion_includes_all_components(self):
        """Formatted suggestion should include WHY, HOW, and actionable elements."""
        handler = RecoveryGuidanceHandler()

        why_text = "Phase left in IN_PROGRESS state indicates interruption"
        how_text = "Resetting allows framework to retry from clean state"
        command = "/nw:execute @software-crafter 'steps/01-01.json'"

        formatted = handler.format_suggestion(
            why_text=why_text,
            how_text=how_text,
            actionable_command=command,
        )

        # Should contain Why
        assert why_text in formatted or any(
            word in formatted for word in why_text.split()
        )
        # Should contain How
        assert how_text in formatted or any(
            word in formatted for word in how_text.split()
        )
        # Should contain actionable command
        assert command in formatted


class TestHandleFailure:
    """Test handle_failure method."""

    def test_handle_failure_returns_dict(self, tmp_path):
        """Should return a dictionary with recovery suggestions."""
        handler = RecoveryGuidanceHandler()

        # Create a simple step file
        step_file_path = tmp_path / "step.json"
        step_data = {
            "task_id": "01-01",
            "state": {
                "status": "IN_PROGRESS",
            },
        }
        step_file_path.write_text(json.dumps(step_data))

        result = handler.handle_failure(
            step_file_path=str(step_file_path),
            failure_type="abandoned_phase",
            context={
                "phase": "GREEN_UNIT",
                "failure_reason": "Agent crashed during GREEN_UNIT phase",
            },
        )

        assert result is not None
        assert isinstance(result, dict)
        assert "recovery_suggestions" in result
        assert isinstance(result["recovery_suggestions"], list)
        assert len(result["recovery_suggestions"]) > 0

    def test_handle_failure_persists_to_step_file(self, tmp_path):
        """Should persist recovery suggestions to step file JSON."""
        handler = RecoveryGuidanceHandler()

        # Create a step file
        step_file_path = tmp_path / "step.json"
        step_data = {
            "task_id": "01-01",
            "state": {
                "status": "IN_PROGRESS",
            },
        }
        step_file_path.write_text(json.dumps(step_data))

        # Handle failure
        handler.handle_failure(
            step_file_path=str(step_file_path),
            failure_type="abandoned_phase",
            context={
                "phase": "GREEN_UNIT",
                "failure_reason": "Agent crashed during GREEN_UNIT phase",
            },
        )

        # Verify step file was updated
        updated_data = json.loads(step_file_path.read_text())
        assert "recovery_suggestions" in updated_data["state"]
        assert isinstance(updated_data["state"]["recovery_suggestions"], list)
        assert len(updated_data["state"]["recovery_suggestions"]) > 0

    def test_handle_failure_includes_failure_reason(self, tmp_path):
        """Should include failure reason in updated state."""
        handler = RecoveryGuidanceHandler()

        step_file_path = tmp_path / "step.json"
        step_data = {
            "task_id": "01-01",
            "state": {
                "status": "IN_PROGRESS",
            },
        }
        step_file_path.write_text(json.dumps(step_data))

        result = handler.handle_failure(
            step_file_path=str(step_file_path),
            failure_type="abandoned_phase",
            context={
                "phase": "RED_UNIT",
                "failure_reason": "Agent crashed during RED_UNIT phase",
            },
        )

        assert "failure_reason" in result or "failure_reason" in str(result)


class TestSupportedFailureModes:
    """Test support for all defined failure modes."""

    @pytest.mark.parametrize(
        "failure_type",
        [
            "abandoned_phase",
            "silent_completion",
            "missing_section",
            "invalid_outcome",
        ],
    )
    def test_generate_suggestions_for_all_supported_modes(self, failure_type):
        """Should generate suggestions for all supported failure modes."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type=failure_type,
            context={
                "phase": "GREEN_UNIT",
                "step_file": "steps/01-01.json",
            },
        )

        assert suggestions is not None
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0


class TestMissingSectionDetection:
    """Test detection and recovery guidance for missing mandatory sections."""

    def test_generate_suggestions_for_missing_section_with_section_name(self):
        """Should include specific section name in recovery suggestions for missing_section."""
        handler = RecoveryGuidanceHandler()
        section_name = "TDD_PHASES"
        suggestions = handler.generate_recovery_suggestions(
            failure_type="missing_section",
            context={
                "section_name": section_name,
            },
        )

        assert suggestions is not None
        assert isinstance(suggestions, list)
        assert len(suggestions) >= 2

        # Section name should appear in at least one suggestion
        has_section_reference = any(section_name in s for s in suggestions)
        assert has_section_reference, (
            f"Section name '{section_name}' not found in suggestions"
        )

        # At least one suggestion should provide actionable guidance
        has_actionable_guidance = any(
            "add" in s.lower() or "include" in s.lower() or "template" in s.lower()
            for s in suggestions
        )
        assert has_actionable_guidance, "No actionable guidance found in suggestions"

    def test_missing_section_suggestions_include_why_how_action(self):
        """Suggestions for missing_section should include WHY, HOW, and ACTION components."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type="missing_section",
            context={
                "section_name": "BOUNDARY_RULES",
            },
        )

        assert len(suggestions) >= 2

        # Check for WHY, HOW, ACTION components in suggestions
        suggestion_text = "\n".join(suggestions)
        assert "WHY:" in suggestion_text, "Missing 'WHY:' component in suggestions"
        assert "HOW:" in suggestion_text, "Missing 'HOW:' component in suggestions"
        assert "ACTION:" in suggestion_text, (
            "Missing 'ACTION:' component in suggestions"
        )

    def test_missing_section_suggestions_vary_by_section_name(self):
        """Different section names should produce variations in recovery guidance."""
        handler = RecoveryGuidanceHandler()

        suggestions_tdd = handler.generate_recovery_suggestions(
            failure_type="missing_section",
            context={"section_name": "TDD_PHASES"},
        )

        suggestions_boundary = handler.generate_recovery_suggestions(
            failure_type="missing_section",
            context={"section_name": "BOUNDARY_RULES"},
        )

        # Both should mention their respective section names
        assert any("TDD_PHASES" in s for s in suggestions_tdd)
        assert any("BOUNDARY_RULES" in s for s in suggestions_boundary)

        # Suggestions should be distinct based on section name
        tdd_text = "\n".join(suggestions_tdd)
        boundary_text = "\n".join(suggestions_boundary)
        assert tdd_text != boundary_text, "Suggestions should vary by section_name"


class TestMissingPhaseDetection:
    """Test detection and recovery guidance for missing TDD phases."""

    def test_generate_suggestions_for_missing_phase(self):
        """Should generate recovery suggestions for missing_phase failure mode."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type="missing_phase",
            context={
                "phase": "RED_UNIT",
            },
        )

        assert suggestions is not None
        assert isinstance(suggestions, list)
        assert len(suggestions) >= 2
        assert all(isinstance(s, str) for s in suggestions)

    def test_missing_phase_suggestions_include_phase_context(self):
        """Recovery suggestions for missing_phase should reference the specific phase."""
        handler = RecoveryGuidanceHandler()
        phase_name = "GREEN_ACCEPTANCE"
        suggestions = handler.generate_recovery_suggestions(
            failure_type="missing_phase",
            context={
                "phase": phase_name,
            },
        )

        # Phase name should appear in at least one suggestion
        has_phase_reference = any(phase_name in s for s in suggestions)
        assert has_phase_reference, (
            f"Phase name '{phase_name}' not found in suggestions"
        )

    def test_missing_phase_suggestions_include_why_how_action(self):
        """Suggestions for missing_phase should include WHY, HOW, and ACTION components."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type="missing_phase",
            context={
                "phase": "REFACTOR_L2",
            },
        )

        suggestion_text = "\n".join(suggestions)
        assert "WHY:" in suggestion_text, "Missing 'WHY:' component in suggestions"
        assert "HOW:" in suggestion_text, "Missing 'HOW:' component in suggestions"
        assert "ACTION:" in suggestion_text, (
            "Missing 'ACTION:' component in suggestions"
        )

    def test_missing_phase_explains_purpose(self):
        """Recovery suggestions for missing_phase should explain why the phase is needed."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type="missing_phase",
            context={
                "phase": "REVIEW",
            },
        )

        suggestion_text = "\n".join(suggestions).lower()
        # Should explain purpose of the phase (review, validation, refactoring, etc.)
        has_purpose_explanation = any(
            keyword in suggestion_text
            for keyword in ["needed", "required", "purpose", "important", "critical"]
        )
        assert has_purpose_explanation, (
            "Suggestions should explain why the phase is required"
        )


class TestTimeoutFailureDetection:
    """Test detection and recovery guidance for timeout failures."""

    def test_generate_suggestions_for_timeout_failure(self):
        """Should generate recovery suggestions for timeout_failure failure mode."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type="timeout_failure",
            context={
                "configured_timeout_minutes": "30",
                "actual_runtime_minutes": "35",
            },
        )

        assert suggestions is not None
        assert isinstance(suggestions, list)
        assert len(suggestions) >= 2
        assert all(isinstance(s, str) for s in suggestions)

    def test_timeout_failure_suggestions_include_timeout_context(self):
        """Recovery suggestions for timeout_failure should reference timeout values."""
        handler = RecoveryGuidanceHandler()
        configured_timeout = "30"
        actual_runtime = "35"
        suggestions = handler.generate_recovery_suggestions(
            failure_type="timeout_failure",
            context={
                "configured_timeout_minutes": configured_timeout,
                "actual_runtime_minutes": actual_runtime,
            },
        )

        # Both timeout values should appear in suggestions
        has_configured = any(configured_timeout in s for s in suggestions)
        has_actual = any(actual_runtime in s for s in suggestions)
        assert has_configured, (
            f"Configured timeout '{configured_timeout}' not found in suggestions"
        )
        assert has_actual, f"Actual runtime '{actual_runtime}' not found in suggestions"

    def test_timeout_failure_suggestions_include_why_how_action(self):
        """Suggestions for timeout_failure should include WHY, HOW, and ACTION components."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type="timeout_failure",
            context={
                "configured_timeout_minutes": "30",
                "actual_runtime_minutes": "35",
            },
        )

        suggestion_text = "\n".join(suggestions)
        assert "WHY:" in suggestion_text, "Missing 'WHY:' component in suggestions"
        assert "HOW:" in suggestion_text, "Missing 'HOW:' component in suggestions"
        assert "ACTION:" in suggestion_text, (
            "Missing 'ACTION:' component in suggestions"
        )

    def test_timeout_failure_suggests_optimization(self):
        """Recovery suggestions for timeout_failure should suggest optimization approaches."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type="timeout_failure",
            context={
                "configured_timeout_minutes": "30",
                "actual_runtime_minutes": "35",
            },
        )

        suggestion_text = "\n".join(suggestions).lower()
        optimization_keywords = [
            "optimize",
            "performance",
            "profile",
            "improve",
            "reduce",
            "simplify",
        ]
        has_optimization = any(
            keyword in suggestion_text for keyword in optimization_keywords
        )
        assert has_optimization, (
            f"No optimization keywords found in suggestions. Expected one of: {optimization_keywords}"
        )

    def test_timeout_failure_suggests_threshold_adjustment(self):
        """Recovery suggestions for timeout_failure should suggest timeout threshold adjustment."""
        handler = RecoveryGuidanceHandler()
        suggestions = handler.generate_recovery_suggestions(
            failure_type="timeout_failure",
            context={
                "configured_timeout_minutes": "30",
                "actual_runtime_minutes": "35",
            },
        )

        suggestion_text = "\n".join(suggestions).lower()
        threshold_keywords = [
            "increase",
            "threshold",
            "timeout",
            "extend",
            "raise",
            "adjust",
        ]
        has_threshold = any(
            keyword in suggestion_text for keyword in threshold_keywords
        )
        assert has_threshold, (
            f"No threshold adjustment keywords found in suggestions. Expected one of: {threshold_keywords}"
        )
