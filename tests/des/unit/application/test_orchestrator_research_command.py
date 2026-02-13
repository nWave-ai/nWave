"""
Unit tests for research command handling in DESOrchestrator.

Validates that /nw:research commands:
- Are NOT in VALIDATION_COMMANDS constant
- Do NOT receive TIMEOUT_INSTRUCTION section
- Return minimal prompt without DES validation overhead
"""

import pytest

from des.application.orchestrator import DESOrchestrator


class TestResearchCommandValidation:
    """Unit tests for /nw:research command prompt rendering."""

    # Test constants (L1: Extract magic strings to named constants)
    RESEARCH_COMMAND = "/nw:research"
    EXECUTE_COMMAND = "/nw:execute"
    DEVELOP_COMMAND = "/nw:develop"
    TIMEOUT_INSTRUCTION_SECTION = "TIMEOUT_INSTRUCTION"

    def test_research_command_not_in_validation_commands(self):
        """
        GIVEN DESOrchestrator VALIDATION_COMMANDS constant
        WHEN checking for /nw:research
        THEN /nw:research is NOT present in the list

        Business Context:
        Research commands are exploratory, not production workflows.
        They should bypass DES validation entirely.
        """
        # GIVEN
        validation_commands = DESOrchestrator.VALIDATION_COMMANDS

        # THEN
        assert self.RESEARCH_COMMAND not in validation_commands, (
            f"{self.RESEARCH_COMMAND} should NOT be in VALIDATION_COMMANDS - "
            "it's an exploratory command that bypasses validation"
        )
        assert self.EXECUTE_COMMAND in validation_commands, (
            f"Sanity check: {self.EXECUTE_COMMAND} should be in VALIDATION_COMMANDS"
        )
        assert self.DEVELOP_COMMAND in validation_commands, (
            f"Sanity check: {self.DEVELOP_COMMAND} should be in VALIDATION_COMMANDS"
        )

    def test_research_command_no_timeout_instruction(
        self, des_orchestrator, tmp_project_root
    ):
        """
        GIVEN /nw:research command
        WHEN render_prompt() is called
        THEN prompt does NOT contain TIMEOUT_INSTRUCTION section

        Business Context:
        Research commands should execute quickly without turn discipline overhead.
        They don't need TIMEOUT_INSTRUCTION since they're ad-hoc exploration.
        """
        # GIVEN
        command = self.RESEARCH_COMMAND
        topic = "authentication patterns"

        # WHEN
        prompt = des_orchestrator.render_prompt(
            command=command, topic=topic, project_root=tmp_project_root
        )

        # THEN
        assert self.TIMEOUT_INSTRUCTION_SECTION not in prompt, (
            "Research commands should not have TIMEOUT_INSTRUCTION section"
        )
        assert f"## {self.TIMEOUT_INSTRUCTION_SECTION}" not in prompt, (
            "Research commands should not have TIMEOUT_INSTRUCTION header"
        )
        assert f"# {self.TIMEOUT_INSTRUCTION_SECTION}" not in prompt, (
            "Research commands should not have TIMEOUT_INSTRUCTION header"
        )

    def test_research_prompt_structure_excludes_timeout(
        self, des_orchestrator, tmp_project_root
    ):
        """
        GIVEN /nw:research command
        WHEN render_prompt() is called
        THEN prompt structure excludes all timeout-related content

        Business Context:
        Research commands should not have:
        - TIMEOUT_INSTRUCTION section
        - Turn budget guidance
        - Progress checkpoints
        - Early exit protocol
        - Turn count logging instructions

        This test validates comprehensive exclusion of timeout concepts.
        """
        # GIVEN
        command = self.RESEARCH_COMMAND
        topic = "database migration patterns"

        # WHEN
        prompt = des_orchestrator.render_prompt(
            command=command, topic=topic, project_root=tmp_project_root
        )

        # THEN: No timeout-related content
        timeout_indicators = [
            self.TIMEOUT_INSTRUCTION_SECTION,
            "turn budget",
            "50 turn",
            "checkpoint",
            "early exit",
            "turn count",
        ]

        self._assert_no_timeout_indicators(prompt, timeout_indicators)

    def _assert_no_timeout_indicators(self, prompt: str, indicators: list[str]) -> None:
        """L2: Extract assertion logic for timeout indicators check."""
        for indicator in indicators:
            assert indicator.lower() not in prompt.lower(), (
                f"Research command should not contain '{indicator}' "
                f"- timeout concepts not applicable to exploration"
            )

    def test_research_command_returns_minimal_prompt(
        self, des_orchestrator, tmp_project_root
    ):
        """
        GIVEN /nw:research command
        WHEN render_prompt() is called
        THEN prompt is minimal (empty or minimal DES-free content)

        Business Context:
        Research commands bypass DES validation, so the prompt should
        be minimal - just the research topic without validation overhead.
        """
        # GIVEN
        command = self.RESEARCH_COMMAND
        topic = "refactoring techniques"

        # WHEN
        prompt = des_orchestrator.render_prompt(
            command=command, topic=topic, project_root=tmp_project_root
        )

        # THEN: Minimal prompt (empty or very short)
        assert len(prompt) < 100, (
            "Research command prompt should be minimal (< 100 chars) "
            f"but got {len(prompt)} chars"
        )

        # Should not have DES validation markers
        assert "<!-- DES-VALIDATION: required -->" not in prompt, (
            "Research commands should not have DES validation markers"
        )
        assert "<!-- DES-STEP-FILE:" not in prompt, (
            "Research commands should not reference step files"
        )

    def test_render_full_prompt_rejects_research_command(
        self, des_orchestrator, tmp_project_root
    ):
        """
        GIVEN /nw:research command
        WHEN render_full_prompt() is called
        THEN ValueError is raised (research not supported by full prompt)

        Business Context:
        render_full_prompt() is for validation commands only.
        Research commands should raise an error if someone tries to
        use render_full_prompt() with them.
        """
        # GIVEN
        command = self.RESEARCH_COMMAND
        agent = "@researcher"
        step_file = "steps/research.json"

        # WHEN/THEN
        with pytest.raises(ValueError, match="only supports validation commands"):
            des_orchestrator.render_full_prompt(
                command=command,
                agent=agent,
                step_file=step_file,
                project_root=tmp_project_root,
            )
