"""
Unit tests for TIMEOUT_INSTRUCTION generation in DESOrchestrator.render_full_prompt().

These tests verify that the orchestrator correctly generates the TIMEOUT_INSTRUCTION
section when rendering prompts for validation commands (/nw:execute, /nw:develop).

Test Coverage:
- render_full_prompt() generates TIMEOUT_INSTRUCTION section
- Section includes all 4 required elements (budget, checkpoints, early exit, logging)
- Section only generated for validation commands (not research/ad-hoc)
- Integration with TimeoutInstructionTemplate.render()
"""

import pytest


class TestOrchestratorTimeoutInstruction:
    """Unit tests for TIMEOUT_INSTRUCTION generation in orchestrator."""

    def test_render_full_prompt_includes_timeout_instruction_for_execute(
        self, des_orchestrator, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN /nw:execute command
        WHEN render_full_prompt is called
        THEN prompt includes TIMEOUT_INSTRUCTION section header
        """
        # GIVEN
        command = "/nw:execute"
        agent = "@software-crafter"
        step_file = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent=agent,
            step_file=step_file,
            project_root=tmp_project_root,
        )

        # THEN
        assert "TIMEOUT_INSTRUCTION" in prompt
        assert "## TIMEOUT_INSTRUCTION" in prompt or "# TIMEOUT_INSTRUCTION" in prompt

    def test_render_full_prompt_includes_timeout_instruction_for_develop(
        self, des_orchestrator, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN /nw:develop command
        WHEN render_full_prompt is called
        THEN prompt includes TIMEOUT_INSTRUCTION section header
        """
        # GIVEN
        command = "/nw:develop"
        agent = "@software-crafter"
        step_file = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent=agent,
            step_file=step_file,
            project_root=tmp_project_root,
        )

        # THEN
        assert "TIMEOUT_INSTRUCTION" in prompt

    def test_render_full_prompt_timeout_includes_turn_budget(
        self, des_orchestrator, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN /nw:execute command
        WHEN render_full_prompt is called
        THEN TIMEOUT_INSTRUCTION includes turn budget (~50)
        """
        # GIVEN
        command = "/nw:execute"
        step_file = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file,
            project_root=tmp_project_root,
        )

        # THEN
        turn_budget_patterns = ["50 turn", "approximately 50", "~50", "around 50"]
        assert any(pattern in prompt.lower() for pattern in turn_budget_patterns), (
            "Turn budget (~50) not found in TIMEOUT_INSTRUCTION"
        )

    def test_render_full_prompt_timeout_includes_progress_checkpoints(
        self, des_orchestrator, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN /nw:execute command
        WHEN render_full_prompt is called
        THEN TIMEOUT_INSTRUCTION includes progress checkpoints
        """
        # GIVEN
        command = "/nw:execute"
        step_file = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file,
            project_root=tmp_project_root,
        )

        # THEN
        checkpoint_indicators = [
            "turn 10" in prompt.lower() or "~10" in prompt,
            "turn 25" in prompt.lower() or "~25" in prompt,
            "turn 40" in prompt.lower() or "~40" in prompt,
        ]
        assert any(checkpoint_indicators), "Progress checkpoints not found"

    def test_render_full_prompt_timeout_includes_early_exit_protocol(
        self, des_orchestrator, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN /nw:execute command
        WHEN render_full_prompt is called
        THEN TIMEOUT_INSTRUCTION includes early exit protocol
        """
        # GIVEN
        command = "/nw:execute"
        step_file = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file,
            project_root=tmp_project_root,
        )

        # THEN
        early_exit_indicators = [
            "early exit" in prompt.lower(),
            "cannot complete" in prompt.lower(),
            "save progress" in prompt.lower(),
        ]
        assert any(early_exit_indicators), "Early exit protocol not found"

    def test_render_full_prompt_timeout_includes_turn_logging(
        self, des_orchestrator, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN /nw:execute command
        WHEN render_full_prompt is called
        THEN TIMEOUT_INSTRUCTION includes turn logging instruction
        """
        # GIVEN
        command = "/nw:execute"
        step_file = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file,
            project_root=tmp_project_root,
        )

        # THEN
        logging_indicators = [
            "log" in prompt.lower() and "turn" in prompt.lower(),
            "[turn" in prompt.lower(),
        ]
        assert any(logging_indicators), "Turn logging instruction not found"

    def test_render_full_prompt_raises_for_non_validation_command(
        self, des_orchestrator, tmp_project_root
    ):
        """
        GIVEN non-validation command (/nw:research)
        WHEN render_full_prompt is called
        THEN ValueError is raised
        """
        # GIVEN
        command = "/nw:research"
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

    def test_render_full_prompt_includes_des_markers(
        self, des_orchestrator, tmp_project_root, minimal_step_file
    ):
        """
        GIVEN /nw:execute command
        WHEN render_full_prompt is called
        THEN prompt includes DES validation markers
        """
        # GIVEN
        command = "/nw:execute"
        step_file = str(minimal_step_file.relative_to(tmp_project_root))

        # WHEN
        prompt = des_orchestrator.render_full_prompt(
            command=command,
            agent="@software-crafter",
            step_file=step_file,
            project_root=tmp_project_root,
        )

        # THEN
        assert "<!-- DES-VALIDATION: required -->" in prompt
        assert f"<!-- DES-STEP-FILE: {step_file} -->" in prompt
        assert "<!-- DES-ORIGIN: command:/nw:execute -->" in prompt


class TestPrepareAdHocPrompt:
    """Unit tests for prepare_ad_hoc_prompt() - ad-hoc tasks should NOT receive TIMEOUT_INSTRUCTION."""

    def test_prepare_ad_hoc_prompt_no_timeout_instruction(
        self, des_orchestrator, tmp_project_root
    ):
        """
        GIVEN ad-hoc Task invocation with simple prompt
        WHEN prepare_ad_hoc_prompt is called
        THEN prompt does NOT contain TIMEOUT_INSTRUCTION section

        Business Context:
        Ad-hoc exploration tasks should execute immediately without turn discipline overhead.
        """
        # GIVEN
        prompt_text = "Find all uses of UserRepository in the codebase"

        # WHEN
        result = des_orchestrator.prepare_ad_hoc_prompt(
            prompt=prompt_text, project_root=str(tmp_project_root)
        )

        # THEN
        assert "TIMEOUT_INSTRUCTION" not in result, (
            "Ad-hoc prompts should not include TIMEOUT_INSTRUCTION"
        )
        assert result == prompt_text, (
            "Ad-hoc prompts should be returned as-is (pass-through)"
        )

    def test_ad_hoc_bypasses_validation_commands_check(self, des_orchestrator):
        """
        GIVEN ad-hoc prompt (no command context)
        WHEN prepare_ad_hoc_prompt is called
        THEN no validation level check is performed
        AND no DES markers are added

        Business Context:
        Ad-hoc prompts bypass DES validation entirely - they are quick research tasks.
        """
        # GIVEN
        prompt_text = "List all classes implementing IRepository"

        # WHEN
        result = des_orchestrator.prepare_ad_hoc_prompt(prompt=prompt_text)

        # THEN
        assert "<!-- DES-VALIDATION:" not in result, (
            "Ad-hoc prompts should not have DES validation markers"
        )
        assert "<!-- DES-STEP-FILE:" not in result, (
            "Ad-hoc prompts should not reference step files"
        )
        assert "<!-- DES-ORIGIN:" not in result, (
            "Ad-hoc prompts should not have DES origin markers"
        )

    def test_ad_hoc_prompt_structure_excludes_timeout(self, des_orchestrator):
        """
        GIVEN ad-hoc prompt with multiline content
        WHEN prepare_ad_hoc_prompt is called
        THEN result contains only original prompt content
        AND excludes all DES-specific sections

        Business Context:
        Ad-hoc prompts should be minimal and fast - no turn budgets, checkpoints, or protocols.
        """
        # GIVEN
        prompt_text = """
        Analyze the authentication flow:
        1. Find all authentication middleware
        2. Identify token validation logic
        3. List any security vulnerabilities
        """

        # WHEN
        result = des_orchestrator.prepare_ad_hoc_prompt(
            prompt=prompt_text, project_root="/tmp/project"
        )

        # THEN
        # Should not contain any TIMEOUT_INSTRUCTION elements
        assert "turn" not in result.lower() or "return" in result.lower(), (
            "Should not mention turn budgets (but 'return' in prompt is OK)"
        )
        assert "checkpoint" not in result.lower(), (
            "Should not mention progress checkpoints"
        )
        assert "early exit" not in result.lower(), (
            "Should not mention early exit protocol"
        )

        # Should be exact pass-through
        assert result == prompt_text, "Ad-hoc prompt should be returned unchanged"
