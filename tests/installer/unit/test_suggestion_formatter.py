"""
Unit tests for SuggestionFormatter - formatting recovery suggestions with WHY+HOW+Actionable.

Tests verify that recovery suggestions are formatted consistently with:
- WHY clause: Explains failure cause and implications
- HOW clause: Describes fix mechanism
- Actionable element: Specific command or file path
"""

from des.application.recovery_guidance_handler import SuggestionFormatter


class TestSuggestionFormatterBasics:
    """Test basic suggestion formatting with WHY + HOW + Actionable components."""

    def test_format_suggestion_contains_why_clause(self):
        """Suggestion should contain WHY clause explaining failure."""
        formatter = SuggestionFormatter()

        why_text = "The agent left GREEN_UNIT in IN_PROGRESS state"
        how_text = "Reset the phase to NOT_EXECUTED"
        actionable = "/nw:execute @software-crafter steps/01-01.json"

        suggestion = formatter.format_suggestion(why_text, how_text, actionable)

        assert "WHY:" in suggestion, "Suggestion must contain WHY clause"
        assert why_text in suggestion, "WHY clause must contain provided why_text"

    def test_format_suggestion_contains_how_clause(self):
        """Suggestion should contain HOW clause describing fix mechanism."""
        formatter = SuggestionFormatter()

        why_text = "The agent left phase IN_PROGRESS"
        how_text = "Resetting phase allows retry from clean state"
        actionable = "/nw:execute"

        suggestion = formatter.format_suggestion(why_text, how_text, actionable)

        assert "HOW:" in suggestion, "Suggestion must contain HOW clause"
        assert how_text in suggestion, "HOW clause must contain provided how_text"

    def test_format_suggestion_contains_actionable_element(self):
        """Suggestion should contain ACTIONABLE element with command or path."""
        formatter = SuggestionFormatter()

        why_text = "Phase abandoned by agent"
        how_text = "Manual state reset enables next attempt"
        actionable = (
            "Update step file: state.tdd_cycle.GREEN_UNIT.status = 'NOT_EXECUTED'"
        )

        suggestion = formatter.format_suggestion(why_text, how_text, actionable)

        assert "ACTION:" in suggestion or "ACTIONABLE:" in suggestion, (
            "Suggestion must contain actionable element"
        )
        assert actionable in suggestion, "Must include provided actionable command"

    def test_format_suggestion_structure_consistent(self):
        """All formatted suggestions should follow consistent structure."""
        formatter = SuggestionFormatter()

        suggestions_data = [
            ("Failure cause A", "Fix mechanism A", "Command A"),
            ("Failure cause B", "Fix mechanism B", "Command B"),
            ("Failure cause C", "Fix mechanism C", "Command C"),
        ]

        formatted = [
            formatter.format_suggestion(why, how, action)
            for why, how, action in suggestions_data
        ]

        # All should have same structure markers
        for suggestion in formatted:
            assert "WHY:" in suggestion, f"Missing WHY in: {suggestion}"
            assert "HOW:" in suggestion, f"Missing HOW in: {suggestion}"
            assert "ACTION:" in suggestion or "ACTIONABLE:" in suggestion, (
                f"Missing actionable in: {suggestion}"
            )

    def test_format_suggestion_preserves_text_content(self):
        """Formatting should preserve all provided text content."""
        formatter = SuggestionFormatter()

        why_text = "Complex technical explanation of root cause"
        how_text = "Detailed steps to resolve the issue"
        actionable = "Run specific_command with --flag option"

        suggestion = formatter.format_suggestion(why_text, how_text, actionable)

        # All content preserved
        assert why_text in suggestion
        assert how_text in suggestion
        assert actionable in suggestion

    def test_format_suggestion_readable_length(self):
        """Formatted suggestion should be readable (not too long)."""
        formatter = SuggestionFormatter()

        why_text = "The agent encountered an unhandled error during execution"
        how_text = "Reviewing the transcript helps identify the root cause"
        actionable = "Check transcript at /tmp/transcript.log"

        suggestion = formatter.format_suggestion(why_text, how_text, actionable)

        # Total length should be reasonable for junior developers (<500 chars)
        assert len(suggestion) < 500, (
            f"Suggestion too long ({len(suggestion)} chars). Should be readable."
        )
        assert len(suggestion) > 50, (
            f"Suggestion too short ({len(suggestion)} chars). Should have substance."
        )


class TestTimeoutFailureFormatting:
    """Test formatting of timeout failure recovery suggestions with time analysis."""

    def test_timeout_suggestion_includes_timeout_values(self):
        """Timeout suggestion should include configured and actual timeout values."""
        formatter = SuggestionFormatter()

        why_text = "Phase ran 35 minutes (exceeded 30-minute timeout)"
        how_text = "Optimize performance or increase timeout threshold"
        actionable = "/nw:execute with --timeout=50"

        suggestion = formatter.format_suggestion(why_text, how_text, actionable)

        assert "35" in suggestion or "timeout" in suggestion.lower(), (
            "Should reference actual runtime"
        )
        assert "30" in suggestion or "threshold" in suggestion.lower(), (
            "Should reference configured timeout"
        )

    def test_timeout_suggestion_recommends_optimization_or_adjustment(self):
        """Timeout suggestion should recommend either optimization or adjustment."""
        formatter = SuggestionFormatter()

        why_text = "Exceeded timeout threshold"
        how_text = "Try code optimization or increase timeout limit"
        actionable = "/nw:execute @software-crafter --timeout=45"

        suggestion = formatter.format_suggestion(why_text, how_text, actionable)

        # Should address both approaches
        has_optimization = any(
            word in suggestion.lower()
            for word in ["optimize", "improve", "performance", "reduce", "simplify"]
        )
        has_adjustment = any(
            word in suggestion.lower()
            for word in ["increase", "threshold", "adjust", "extend", "raise"]
        )

        assert has_optimization or has_adjustment, (
            "Should recommend either optimization or threshold adjustment"
        )

    def test_timeout_suggestion_includes_actionable_command(self):
        """Timeout suggestion should include specific executable command."""
        formatter = SuggestionFormatter()

        why_text = "Phase timed out after 40 minutes"
        how_text = "Increase timeout and retry"
        actionable = "pytest tests/unit/ --timeout=3000"

        suggestion = formatter.format_suggestion(why_text, how_text, actionable)

        assert (
            "pytest" in suggestion
            or "timeout" in suggestion
            or "command" in suggestion.lower()
            or "--timeout" in suggestion
        ), "Should include specific command or timeout parameter"


class TestEdgeCasesAndValidation:
    """Test edge cases and validation of suggestion formatter."""

    def test_format_with_empty_strings_still_structured(self):
        """Formatter should handle empty strings while maintaining structure."""
        formatter = SuggestionFormatter()

        suggestion = formatter.format_suggestion("", "", "")

        # Should still have structure even with empty content
        assert "WHY:" in suggestion
        assert "HOW:" in suggestion
        assert "ACTION:" in suggestion or "ACTIONABLE:" in suggestion

    def test_format_with_special_characters(self):
        """Formatter should preserve special characters (quotes, paths, etc.)."""
        formatter = SuggestionFormatter()

        why_text = 'Error: "connection refused" on /tmp/socket'
        how_text = "Restart service: `systemctl restart myapp`"
        actionable = '/usr/bin/script.sh --config="/etc/config.yaml"'

        suggestion = formatter.format_suggestion(why_text, how_text, actionable)

        assert why_text in suggestion
        assert how_text in suggestion
        assert actionable in suggestion

    def test_format_with_multiline_content(self):
        """Formatter should handle multiline content appropriately."""
        formatter = SuggestionFormatter()

        why_text = "Multiple reasons for failure:\n- Network timeout\n- Server overload"
        how_text = "Recovery steps:\n1. Check network\n2. Restart server"
        actionable = "Run: /nw:execute"

        suggestion = formatter.format_suggestion(why_text, how_text, actionable)

        assert why_text in suggestion
        assert how_text in suggestion


class TestSuggestionFormatterIntegration:
    """Integration tests verifying formatter works with RecoveryGuidanceHandler."""

    def test_formatter_available_in_recovery_handler(self):
        """SuggestionFormatter should be integrated with RecoveryGuidanceHandler."""
        from des.application.recovery_guidance_handler import (
            RecoveryGuidanceHandler,
        )

        handler = RecoveryGuidanceHandler()

        # Handler should have format_suggestion method
        assert hasattr(handler, "format_suggestion"), (
            "RecoveryGuidanceHandler must have format_suggestion method"
        )

    def test_recovery_handler_format_suggestion_works(self):
        """RecoveryGuidanceHandler.format_suggestion should format correctly."""
        from des.application.recovery_guidance_handler import (
            RecoveryGuidanceHandler,
        )

        handler = RecoveryGuidanceHandler()

        suggestion = handler.format_suggestion(
            why_text="Test reason",
            how_text="Test fix",
            actionable_command="test command",
        )

        assert "WHY:" in suggestion
        assert "Test reason" in suggestion
        assert "HOW:" in suggestion
        assert "Test fix" in suggestion
        assert "ACTION:" in suggestion or "ACTIONABLE:" in suggestion
