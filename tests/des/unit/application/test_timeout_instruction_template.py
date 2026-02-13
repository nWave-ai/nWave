"""
Unit tests for TIMEOUT_INSTRUCTION template structure.

Tests verify that the TIMEOUT_INSTRUCTION content includes all 4 required elements:
1. Turn budget (~50 turns)
2. Progress checkpoints (turn ~10, ~25, ~40, ~50)
3. Early exit protocol
4. Turn logging instruction
"""

from des.domain.timeout_instruction_template import TimeoutInstructionTemplate


class TestTimeoutInstructionTemplateStructure:
    """Tests for the overall template structure."""

    def test_timeout_instruction_template_structure(self):
        """
        GIVEN TimeoutInstructionTemplate is instantiated
        WHEN render() is called
        THEN result contains section header and all 4 elements
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        content = template.render()

        # THEN
        assert "TIMEOUT_INSTRUCTION" in content, "Section header missing"
        assert content.strip().startswith("## TIMEOUT_INSTRUCTION"), (
            "Content should start with markdown section header"
        )

        # Verify all 4 elements present (high-level check)
        assert "50" in content and "turn" in content.lower(), "Turn budget missing"
        assert any(marker in content for marker in ["~10", "~25", "~40"]), (
            "Progress checkpoints missing"
        )
        assert (
            "early exit" in content.lower() or "cannot complete" in content.lower()
        ), "Early exit protocol missing"
        assert "log" in content.lower() and (
            "turn" in content.lower() or "phase" in content.lower()
        ), "Turn logging instruction missing"


class TestTurnBudgetElement:
    """Tests for turn budget element formatting."""

    def test_turn_budget_element_format(self):
        """
        GIVEN TimeoutInstructionTemplate is instantiated
        WHEN render() is called
        THEN turn budget element specifies ~50 turns with clear guidance
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        content = template.render()

        # THEN: Turn budget is clearly stated
        # Accept variations: "50 turns", "approximately 50", "~50"
        turn_budget_patterns = ["50 turn", "approximately 50", "~50", "around 50"]
        budget_found = any(
            pattern in content.lower() for pattern in turn_budget_patterns
        )
        assert budget_found, (
            "Turn budget (~50) not clearly specified. "
            "Expected one of: '50 turns', 'approximately 50', '~50', 'around 50'"
        )

        # Turn budget should provide context about what it means
        guidance_terms = ["aim", "target", "complete", "budget", "limit"]
        guidance_found = any(term in content.lower() for term in guidance_terms)
        assert guidance_found, (
            "Turn budget should include guidance on its purpose "
            "(e.g., 'Aim to complete within 50 turns')"
        )


class TestProgressCheckpointsDefinition:
    """Tests for progress checkpoints element."""

    def test_progress_checkpoints_definition(self):
        """
        GIVEN TimeoutInstructionTemplate is instantiated
        WHEN render() is called
        THEN progress checkpoints are defined with TDD phase mapping
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        content = template.render()

        # THEN: Checkpoints at key turn numbers
        checkpoint_indicators = [
            "~10" in content or "turn 10" in content.lower(),
            "~25" in content or "turn 25" in content.lower(),
            "~40" in content or "turn 40" in content.lower(),
        ]
        assert any(checkpoint_indicators), (
            "Progress checkpoints missing. Expected checkpoints at turn ~10, ~25, ~40"
        )

        # Checkpoints should map to TDD phases
        phase_terms = ["prepare", "red", "green", "refactor", "commit"]
        phase_found = any(term in content.lower() for term in phase_terms)
        assert phase_found, (
            "Checkpoints should be associated with TDD phases "
            "(e.g., 'Turn ~10: PREPARE and RED phases complete')"
        )


class TestEarlyExitProtocolSteps:
    """Tests for early exit protocol element."""

    def test_early_exit_protocol_steps(self):
        """
        GIVEN TimeoutInstructionTemplate is instantiated
        WHEN render() is called
        THEN early exit protocol documents clear steps for graceful exit
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        content = template.render()

        # THEN: Early exit protocol is documented
        early_exit_indicators = [
            "early exit" in content.lower(),
            "cannot complete" in content.lower(),
            "stuck" in content.lower(),
        ]
        assert any(early_exit_indicators), (
            "Early exit protocol trigger conditions missing. "
            "Expected mention of 'early exit', 'cannot complete', or 'stuck'"
        )

        # Protocol should mention saving state
        state_save_terms = ["save", "progress", "in_progress", "update"]
        state_guidance = any(term in content.lower() for term in state_save_terms)
        assert state_guidance, (
            "Early exit protocol must include state-saving steps "
            "(e.g., 'save progress', 'update step file', 'set phase to IN_PROGRESS')"
        )

        # Protocol should mention returning/exiting
        exit_terms = ["return", "exit", "stop"]
        exit_guidance = any(term in content.lower() for term in exit_terms)
        assert exit_guidance, (
            "Early exit protocol must include exit instruction "
            "(e.g., 'return with status', 'exit gracefully')"
        )


class TestRenderEarlyExitProtocolHelper:
    """Tests for _render_early_exit_protocol() helper method (US-006 step 01-04)."""

    def test_render_early_exit_protocol_contains_4_steps(self):
        """
        GIVEN TimeoutInstructionTemplate is instantiated
        WHEN _render_early_exit_protocol() is called
        THEN output contains 4 numbered steps for graceful exit
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        protocol = template._render_early_exit_protocol()

        # THEN: 4 steps are documented
        # Count numbered items (1., 2., 3., 4.)
        numbered_steps = [f"{i}." for i in range(1, 5)]
        steps_found = sum(1 for step in numbered_steps if step in protocol)

        assert steps_found == 4, (
            f"Early exit protocol should contain 4 numbered steps, found {steps_found}. "
            "Expected: 1. Save progress, 2. Set IN_PROGRESS, 3. Return status, 4. Don't continue"
        )

    def test_render_early_exit_protocol_includes_save_progress(self):
        """
        GIVEN TimeoutInstructionTemplate is instantiated
        WHEN _render_early_exit_protocol() is called
        THEN output includes instruction to save progress to step file
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        protocol = template._render_early_exit_protocol()

        # THEN: Save progress instruction present
        save_indicators = [
            "save" in protocol.lower(),
            "progress" in protocol.lower(),
            "step file" in protocol.lower(),
        ]

        assert any(save_indicators), (
            "Early exit protocol must include 'save progress to step file' instruction. "
            "Agents need to preserve work before exiting."
        )

    def test_render_early_exit_protocol_includes_partial_completion(self):
        """
        GIVEN TimeoutInstructionTemplate is instantiated
        WHEN _render_early_exit_protocol() is called
        THEN output mentions PARTIAL_COMPLETION or partial status concept
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        protocol = template._render_early_exit_protocol()

        # THEN: Partial completion or status mentioned
        partial_indicators = [
            "partial" in protocol.lower(),
            "status" in protocol.lower(),
            "blocking" in protocol.lower(),
            "cannot complete" in protocol.lower(),
        ]

        assert any(partial_indicators), (
            "Early exit protocol must explain returning with status explaining blockage. "
            "Expected mention of 'status', 'partial', 'blocking', or 'cannot complete'."
        )

    def test_render_early_exit_protocol_valid_markdown(self):
        """
        GIVEN TimeoutInstructionTemplate is instantiated
        WHEN _render_early_exit_protocol() is called
        THEN output is valid markdown with numbered list format
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        protocol = template._render_early_exit_protocol()

        # THEN: Valid markdown structure
        # Should have markdown header or bold section title
        has_header = (
            protocol.startswith("**")
            or protocol.startswith("#")
            or "**Early Exit" in protocol
        )
        assert has_header, (
            "Early exit protocol should start with markdown header or bold title "
            "(e.g., '**Early Exit Protocol**' or '### Early Exit Protocol')"
        )

        # Should have numbered list format
        has_numbered_list = "1." in protocol and "2." in protocol
        assert has_numbered_list, (
            "Early exit protocol should use markdown numbered list format (1., 2., 3., 4.)"
        )


class TestTurnLoggingFormatSpecification:
    """Tests for turn logging instruction element."""

    def test_turn_logging_format_specification(self):
        """
        GIVEN TimeoutInstructionTemplate is instantiated
        WHEN render() is called
        THEN turn logging instruction specifies format for phase transitions
        """
        # GIVEN
        template = TimeoutInstructionTemplate()

        # WHEN
        content = template.render()

        # THEN: Turn logging instruction present
        logging_indicators = [
            "log" in content.lower() and "turn" in content.lower(),
            "[turn" in content.lower(),  # Example format like "[Turn 15]"
        ]
        assert any(logging_indicators), (
            "Turn logging instruction missing. "
            "Expected instruction to log turn count (e.g., 'Log turn count at phase transitions')"
        )

        # Logging should be associated with phase transitions
        transition_terms = ["phase", "transition", "start", "complete"]
        transition_guidance = any(term in content.lower() for term in transition_terms)
        assert transition_guidance, (
            "Turn logging should be associated with phase transitions "
            "(e.g., 'Log turn count when starting/completing each phase')"
        )

        # Should provide example format
        format_example = "[turn" in content.lower() or "turn x" in content.lower()
        assert format_example, (
            "Turn logging should include example format "
            "(e.g., '[Turn 15] Starting GREEN_UNIT phase')"
        )
