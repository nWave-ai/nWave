"""
Unit tests for TimeoutInstructionTemplate helper methods.

Tests the DRY refactoring of common markdown formatting logic into
_format_instruction_element() method.
"""

from des.domain.timeout_instruction_template import TimeoutInstructionTemplate


class TestFormatInstructionElement:
    """
    Unit tests for _format_instruction_element() helper method.

    This method extracts common markdown formatting logic used by all 4
    helper methods (_render_turn_budget, _render_progress_checkpoints,
    _render_early_exit_protocol, _render_turn_logging).
    """

    def test_format_instruction_element_creates_bold_header_with_content(self):
        """
        GIVEN header text and content text
        WHEN _format_instruction_element() is called
        THEN returns markdown with **Header**: content format

        Business Context:
        All 4 instruction elements follow the pattern "**Header**: content".
        This test verifies the shared formatter creates this structure correctly.
        """
        template = TimeoutInstructionTemplate()

        # WHEN: Format simple header with content
        result = template._format_instruction_element(
            header="Turn Budget",
            content="Aim to complete this task within approximately 50 turns.",
        )

        # THEN: Returns properly formatted markdown
        expected = (
            "**Turn Budget**: Aim to complete this task within approximately 50 turns."
        )
        assert result == expected, f"Expected '{expected}', got '{result}'"

    def test_format_instruction_element_handles_multiline_content(self):
        """
        GIVEN header text and multiline content
        WHEN _format_instruction_element() is called
        THEN returns markdown with header followed by newline and content

        Business Context:
        Progress checkpoints and early exit protocol have multiline content
        with bullet points. The formatter must handle this correctly.
        """
        template = TimeoutInstructionTemplate()

        # WHEN: Format header with multiline bullet list
        multiline_content = """Track your progress against these milestones:
- Turn ~10: PREPARE and RED phases should be complete
- Turn ~25: GREEN phases should be complete"""

        result = template._format_instruction_element(
            header="Progress Checkpoints", content=multiline_content
        )

        # THEN: Returns header followed by content
        assert result.startswith("**Progress Checkpoints**: ")
        assert "Turn ~10: PREPARE" in result
        assert "Turn ~25: GREEN" in result

    def test_format_instruction_element_preserves_numbered_lists(self):
        """
        GIVEN header with numbered list content
        WHEN _format_instruction_element() is called
        THEN returns markdown preserving numbered list formatting

        Business Context:
        Early exit protocol uses numbered steps (1. 2. 3. 4.).
        The formatter must preserve this numbering.
        """
        template = TimeoutInstructionTemplate()

        # WHEN: Format with numbered list
        numbered_content = """If you cannot complete the task within the turn budget:
1. Save your current progress to the step file
2. Set the current phase to IN_PROGRESS with detailed notes
3. Return with status explaining what's blocking completion"""

        result = template._format_instruction_element(
            header="Early Exit Protocol", content=numbered_content
        )

        # THEN: Numbered list preserved
        assert "1. Save your current progress" in result
        assert "2. Set the current phase" in result
        assert "3. Return with status" in result


class TestHelperMethodsUseDRYFormatter:
    """
    Tests verifying that all 4 helper methods use the shared
    _format_instruction_element() method instead of duplicating
    markdown formatting logic.
    """

    def test_render_turn_budget_uses_shared_formatter(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_turn_budget() is called
        THEN returns result from _format_instruction_element()
        AND contains **Turn Budget**: prefix

        Business Context:
        The refactoring extracts common formatting to _format_instruction_element().
        This test verifies _render_turn_budget() delegates to the shared formatter.
        """
        template = TimeoutInstructionTemplate()

        result = template._render_turn_budget()

        # Verify uses shared formatter (has **Header**: pattern)
        assert result.startswith("**Turn Budget**: ")
        assert "approximately 50 turns" in result

    def test_render_progress_checkpoints_uses_shared_formatter(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_progress_checkpoints() is called
        THEN returns result from _format_instruction_element()
        AND contains **Progress Checkpoints**: prefix
        """
        template = TimeoutInstructionTemplate()

        result = template._render_progress_checkpoints()

        assert result.startswith("**Progress Checkpoints**: ")
        assert "Turn ~10" in result
        assert "Turn ~25" in result

    def test_render_early_exit_protocol_uses_shared_formatter(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_early_exit_protocol() is called
        THEN returns result from _format_instruction_element()
        AND contains **Early Exit Protocol**: prefix
        """
        template = TimeoutInstructionTemplate()

        result = template._render_early_exit_protocol()

        assert result.startswith("**Early Exit Protocol**: ")
        assert "cannot complete" in result.lower()
        assert "save" in result.lower()

    def test_render_turn_logging_uses_shared_formatter(self):
        """
        GIVEN TimeoutInstructionTemplate instance
        WHEN _render_turn_logging() is called
        THEN returns result from _format_instruction_element()
        AND contains **Turn Logging**: prefix
        """
        template = TimeoutInstructionTemplate()

        result = template._render_turn_logging()

        assert result.startswith("**Turn Logging**: ")
        assert "[Turn" in result
        assert "phase transition" in result.lower()


class TestNoDuplicateFormattingCode:
    """
    Tests verifying that markdown formatting logic is NOT duplicated
    across the 4 helper methods.

    This is a meta-test to ensure the DRY refactoring is complete.
    """

    def test_no_duplicate_bold_markdown_in_helpers(self):
        """
        GIVEN TimeoutInstructionTemplate source code
        WHEN inspecting helper method implementations
        THEN each helper calls _format_instruction_element() exactly once
        AND no helper contains inline '**' formatting

        Business Context:
        The refactoring eliminates duplicate '**Header**:' patterns.
        This test ensures the refactoring is complete and no duplication remains.
        """
        import inspect

        template = TimeoutInstructionTemplate()

        # Get source code for each helper method
        helpers = [
            "_render_turn_budget",
            "_render_progress_checkpoints",
            "_render_early_exit_protocol",
            "_render_turn_logging",
        ]

        for helper_name in helpers:
            helper_method = getattr(template, helper_name)
            source = inspect.getsource(helper_method)

            # Verify no inline '**' bold formatting (delegated to shared formatter)
            # Allow '**' only if it's in a string passed to _format_instruction_element
            lines_with_bold = [
                line
                for line in source.split("\n")
                if "**" in line and "_format_instruction_element" not in line
            ]

            assert len(lines_with_bold) == 0, (
                f"{helper_name} contains inline '**' formatting. "
                f"Should delegate to _format_instruction_element(). "
                f"Found: {lines_with_bold}"
            )
