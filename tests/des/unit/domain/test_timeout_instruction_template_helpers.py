"""
Unit tests for TimeoutInstructionTemplate helper methods.

This module tests the 4 private helper methods that render individual
sections of the TIMEOUT_INSTRUCTION:
- _render_turn_budget()
- _render_progress_checkpoints()
- _render_early_exit_protocol()
- _render_turn_logging()

Test Coverage:
- Each method produces expected markdown structure
- Content includes all required elements
- Format consistency across all methods
- 100% code coverage for helper methods
"""

from des.domain.timeout_instruction_template import TimeoutInstructionTemplate


class TestRenderTurnBudget:
    """Unit tests for _render_turn_budget() helper method."""

    def test_render_turn_budget_includes_header(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_turn_budget() is called
        THEN output includes 'Turn Budget' header
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_turn_budget()

        # THEN
        assert "**Turn Budget**:" in result

    def test_render_turn_budget_includes_turn_count(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_turn_budget() is called
        THEN output includes '50' turn count
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_turn_budget()

        # THEN
        assert "50" in result
        assert "turn" in result.lower()

    def test_render_turn_budget_format(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_turn_budget() is called
        THEN output format matches '**Header**: content' pattern
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_turn_budget()

        # THEN
        expected_format = (
            "**Turn Budget**: Aim to complete this task within approximately 50 turns."
        )
        assert result == expected_format


class TestRenderProgressCheckpoints:
    """Unit tests for _render_progress_checkpoints() helper method."""

    def test_render_progress_checkpoints_includes_header(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_progress_checkpoints() is called
        THEN output includes 'Progress Checkpoints' header
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_progress_checkpoints()

        # THEN
        assert "**Progress Checkpoints**:" in result

    def test_render_progress_checkpoints_includes_all_checkpoints(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_progress_checkpoints() is called
        THEN output includes all 4 checkpoint turns: ~10, ~25, ~40, ~50
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_progress_checkpoints()

        # THEN
        assert "~10" in result
        assert "~25" in result
        assert "~40" in result
        assert "~50" in result

    def test_render_progress_checkpoints_maps_tdd_phases(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_progress_checkpoints() is called
        THEN output maps checkpoints to TDD phases (PREPARE, RED, GREEN, REFACTOR, COMMIT)
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_progress_checkpoints()

        # THEN
        # Check for phase mentions
        assert "PREPARE" in result or "RED" in result
        assert "GREEN" in result
        assert "REFACTOR" in result
        assert "COMMIT" in result

    def test_render_progress_checkpoints_has_multiline_content(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_progress_checkpoints() is called
        THEN output contains multiple lines (checkpoint list)
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_progress_checkpoints()

        # THEN
        lines = result.split("\n")
        assert len(lines) >= 5  # Header + 4 checkpoints


class TestRenderEarlyExitProtocol:
    """Unit tests for _render_early_exit_protocol() helper method."""

    def test_render_early_exit_protocol_includes_header(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_early_exit_protocol() is called
        THEN output includes 'Early Exit Protocol' header
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_early_exit_protocol()

        # THEN
        assert "**Early Exit Protocol**:" in result

    def test_render_early_exit_protocol_has_numbered_steps(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_early_exit_protocol() is called
        THEN output contains numbered steps
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_early_exit_protocol()

        # THEN
        assert "1." in result
        assert "2." in result
        assert "3." in result
        assert "4." in result

    def test_render_early_exit_protocol_step_1_save_progress(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_early_exit_protocol() is called
        THEN step 1 mentions saving progress to step file
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_early_exit_protocol()

        # THEN
        assert "save" in result.lower() or "Save" in result
        assert "progress" in result.lower()
        assert "step file" in result.lower()

    def test_render_early_exit_protocol_step_2_set_in_progress(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_early_exit_protocol() is called
        THEN step 2 mentions setting phase to IN_PROGRESS
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_early_exit_protocol()

        # THEN
        assert "IN_PROGRESS" in result or "in_progress" in result.lower()

    def test_render_early_exit_protocol_step_3_return_status(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_early_exit_protocol() is called
        THEN step 3 mentions returning status with blocking explanation
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_early_exit_protocol()

        # THEN
        assert "return" in result.lower() or "Return" in result
        assert "status" in result.lower() or "blocking" in result.lower()

    def test_render_early_exit_protocol_step_4_request_guidance(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_early_exit_protocol() is called
        THEN step 4 mentions requesting human guidance
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_early_exit_protocol()

        # THEN
        assert "human" in result.lower() or "guidance" in result.lower()


class TestRenderTurnLogging:
    """Unit tests for _render_turn_logging() helper method."""

    def test_render_turn_logging_includes_header(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_turn_logging() is called
        THEN output includes 'Turn Logging' header
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_turn_logging()

        # THEN
        assert "**Turn Logging**:" in result

    def test_render_turn_logging_includes_format_examples(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_turn_logging() is called
        THEN output includes example log format with [Turn X]
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_turn_logging()

        # THEN
        assert "[Turn" in result
        assert "Example:" in result or "example:" in result

    def test_render_turn_logging_shows_phase_transition_format(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_turn_logging() is called
        THEN output shows format for logging phase transitions
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_turn_logging()

        # THEN
        # Should show examples like "[Turn 15] Starting GREEN_UNIT phase"
        assert "phase" in result.lower()
        assert (
            "Starting" in result
            or "Completed" in result
            or "starting" in result
            or "completed" in result
        )

    def test_render_turn_logging_explains_purpose(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_turn_logging() is called
        THEN output explains why turn logging is useful
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        result = template._render_turn_logging()

        # THEN
        # Should mention tracking, pacing, or identifying phases
        assert (
            "track" in result.lower()
            or "pacing" in result.lower()
            or "identify" in result.lower()
        )


class TestFormatInstructionElement:
    """Unit tests for _format_instruction_element() formatting helper."""

    def test_format_instruction_element_basic_format(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _format_instruction_element() is called with header and content
        THEN output follows '**Header**: content' pattern
        """
        # GIVEN
        template = TimeoutInstructionTemplate()
        header = "Test Header"
        content = "Test content"

        # WHEN
        result = template._format_instruction_element(header, content)

        # THEN
        assert result == f"**{header}**: {content}"

    def test_format_instruction_element_with_multiline_content(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _format_instruction_element() is called with multiline content
        THEN output preserves multiline structure
        """
        # GIVEN
        template = TimeoutInstructionTemplate()
        header = "Test Header"
        content = "Line 1\nLine 2\nLine 3"

        # WHEN
        result = template._format_instruction_element(header, content)

        # THEN
        assert result.startswith(f"**{header}**: ")
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result


class TestCompleteCoverage:
    """Integration tests ensuring 100% coverage of all helper methods."""

    def test_all_helper_methods_callable(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN all 4 helper methods are called
        THEN all methods execute without errors
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN/THEN - all should succeed
        budget = template._render_turn_budget()
        checkpoints = template._render_progress_checkpoints()
        exit_protocol = template._render_early_exit_protocol()
        logging = template._render_turn_logging()

        assert budget is not None
        assert checkpoints is not None
        assert exit_protocol is not None
        assert logging is not None

    def test_all_helpers_return_non_empty_strings(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN all helper methods are called
        THEN all return non-empty strings
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        budget = template._render_turn_budget()
        checkpoints = template._render_progress_checkpoints()
        exit_protocol = template._render_early_exit_protocol()
        logging = template._render_turn_logging()

        # THEN
        assert len(budget) > 0
        assert len(checkpoints) > 0
        assert len(exit_protocol) > 0
        assert len(logging) > 0

    def test_all_helpers_follow_consistent_format(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN all helper methods are called
        THEN all follow consistent **Header**: content markdown format
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        budget = template._render_turn_budget()
        checkpoints = template._render_progress_checkpoints()
        exit_protocol = template._render_early_exit_protocol()
        logging = template._render_turn_logging()

        # THEN - all should start with **Header**:
        assert budget.startswith("**Turn Budget**:")
        assert checkpoints.startswith("**Progress Checkpoints**:")
        assert exit_protocol.startswith("**Early Exit Protocol**:")
        assert logging.startswith("**Turn Logging**:")
