"""
Unit tests for DESOrchestrator class.

Tests the orchestrator's ability to render prompts with DES validation markers
based on command type (execute, develop, research, ad-hoc).
"""


class TestDESOrchestrator:
    """Unit tests for DESOrchestrator class."""

    def test_execute_command_includes_validation_marker(self, des_orchestrator):
        """
        GIVEN /nw:execute command
        WHEN render_prompt is called
        THEN prompt includes <!-- DES-VALIDATION: required --> marker
        """
        prompt = des_orchestrator.render_prompt(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="steps/01-01.json",
            project_root="/tmp/test",
        )
        assert "<!-- DES-VALIDATION: required -->" in prompt

    def test_execute_command_includes_step_file_marker(self, des_orchestrator):
        """
        GIVEN /nw:execute command with step file
        WHEN render_prompt is called
        THEN prompt includes step file marker
        """
        prompt = des_orchestrator.render_prompt(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="steps/01-01.json",
            project_root="/tmp/test",
        )
        assert "<!-- DES-STEP-FILE: steps/01-01.json -->" in prompt

    def test_execute_command_includes_origin_marker(self, des_orchestrator):
        """
        GIVEN /nw:execute command
        WHEN render_prompt is called
        THEN prompt includes origin marker
        """
        prompt = des_orchestrator.render_prompt(
            command="/nw:execute",
            agent="@software-crafter",
            step_file="steps/01-01.json",
            project_root="/tmp/test",
        )
        assert "<!-- DES-ORIGIN: command:/nw:execute -->" in prompt

    def test_develop_command_includes_validation_marker(self, des_orchestrator):
        """
        GIVEN /nw:develop command
        WHEN render_prompt is called
        THEN prompt includes DES-VALIDATION marker
        """
        prompt = des_orchestrator.render_prompt(
            command="/nw:develop",
            agent="@software-crafter",
            step_file="steps/01-01.json",
            project_root="/tmp/test",
        )
        assert "<!-- DES-VALIDATION: required -->" in prompt

    def test_research_command_excludes_validation_marker(self, des_orchestrator):
        """
        GIVEN /nw:research command
        WHEN render_prompt is called
        THEN prompt does NOT include DES-VALIDATION marker
        """
        prompt = des_orchestrator.render_prompt(
            command="/nw:research",
            topic="authentication patterns",
            project_root="/tmp/test",
        )
        assert "<!-- DES-VALIDATION:" not in prompt

    def test_ad_hoc_prompt_excludes_des_markers(self, des_orchestrator):
        """
        GIVEN ad-hoc prompt
        WHEN prepare_ad_hoc_prompt is called
        THEN prompt does NOT include any DES markers
        """
        prompt = des_orchestrator.prepare_ad_hoc_prompt(
            prompt="Find all uses of UserRepository", project_root="/tmp/test"
        )
        assert "<!-- DES-VALIDATION:" not in prompt
        assert "<!-- DES-STEP-FILE:" not in prompt
        assert "<!-- DES-ORIGIN:" not in prompt

    def test_get_validation_level_returns_full_for_execute(self, des_orchestrator):
        """
        GIVEN /nw:execute command
        WHEN _get_validation_level is called
        THEN it returns "full"
        """
        validation_level = des_orchestrator._get_validation_level("/nw:execute")
        assert validation_level == "full"

    def test_get_validation_level_returns_full_for_develop(self, des_orchestrator):
        """
        GIVEN /nw:develop command
        WHEN _get_validation_level is called
        THEN it returns "full"
        """
        validation_level = des_orchestrator._get_validation_level("/nw:develop")
        assert validation_level == "full"

    def test_get_validation_level_returns_none_for_research(self, des_orchestrator):
        """
        GIVEN /nw:research command
        WHEN _get_validation_level is called
        THEN it returns "none"
        """
        validation_level = des_orchestrator._get_validation_level("/nw:research")
        assert validation_level == "none"

    def test_get_validation_level_returns_none_for_unknown_command(
        self, des_orchestrator
    ):
        """
        GIVEN unknown command
        WHEN _get_validation_level is called
        THEN it returns "none" (safe default)
        """
        validation_level = des_orchestrator._get_validation_level("/nw:unknown")
        assert validation_level == "none"

    def test_generate_des_markers_returns_string(self, des_orchestrator):
        """
        GIVEN command and step_file parameters
        WHEN _generate_des_markers is called
        THEN it returns a string
        """
        result = des_orchestrator._generate_des_markers(
            command="/nw:execute", step_file="steps/01-01.json"
        )
        assert isinstance(result, str)

    def test_generate_des_markers_includes_validation_marker(self, des_orchestrator):
        """
        GIVEN command and step_file parameters
        WHEN _generate_des_markers is called
        THEN result includes DES-VALIDATION marker
        """
        result = des_orchestrator._generate_des_markers(
            command="/nw:execute", step_file="steps/01-01.json"
        )
        assert "<!-- DES-VALIDATION: required -->" in result

    def test_generate_des_markers_includes_step_file_marker(self, des_orchestrator):
        """
        GIVEN command and step_file parameters
        WHEN _generate_des_markers is called
        THEN result includes DES-STEP-FILE marker with correct path
        """
        result = des_orchestrator._generate_des_markers(
            command="/nw:execute", step_file="steps/02-03.json"
        )
        assert "<!-- DES-STEP-FILE: steps/02-03.json -->" in result

    def test_generate_des_markers_includes_origin_marker(self, des_orchestrator):
        """
        GIVEN command and step_file parameters
        WHEN _generate_des_markers is called
        THEN result includes DES-ORIGIN marker with command
        """
        result = des_orchestrator._generate_des_markers(
            command="/nw:develop", step_file="steps/01-01.json"
        )
        assert "<!-- DES-ORIGIN: command:/nw:develop -->" in result

    def test_generate_des_markers_format_multiline(self, des_orchestrator):
        """
        GIVEN command and step_file parameters
        WHEN _generate_des_markers is called
        THEN result contains markers separated by newlines
        """
        result = des_orchestrator._generate_des_markers(
            command="/nw:execute", step_file="steps/01-01.json"
        )
        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[0] == "<!-- DES-VALIDATION: required -->"
        assert lines[1] == "<!-- DES-STEP-FILE: steps/01-01.json -->"
        assert lines[2] == "<!-- DES-ORIGIN: command:/nw:execute -->"


class TestDESOrchestratorEdgeCases:
    """Edge case and error handling tests for DESOrchestrator."""

    def test_render_prompt_with_none_command_raises_value_error(self, des_orchestrator):
        """
        GIVEN None as command parameter
        WHEN render_prompt is called
        THEN it should raise ValueError with clear error message
        """
        import pytest

        with pytest.raises(ValueError, match="Command cannot be None or empty"):
            des_orchestrator.render_prompt(
                command=None,
                agent="@software-crafter",
                step_file="steps/01-01.json",
            )

    def test_render_prompt_with_empty_command_raises_value_error(
        self, des_orchestrator
    ):
        """
        GIVEN empty string as command parameter
        WHEN render_prompt is called
        THEN it should raise ValueError with clear error message
        """
        import pytest

        with pytest.raises(ValueError, match="Command cannot be None or empty"):
            des_orchestrator.render_prompt(
                command="",
                agent="@software-crafter",
                step_file="steps/01-01.json",
            )

    def test_render_prompt_with_none_step_file_for_validation_command_raises_error(
        self, des_orchestrator
    ):
        """
        GIVEN /nw:execute command with None step_file
        WHEN render_prompt is called
        THEN it should raise ValueError
        """
        import pytest

        with pytest.raises(
            ValueError, match="Step file required for validation commands"
        ):
            des_orchestrator.render_prompt(
                command="/nw:execute",
                agent="@software-crafter",
                step_file=None,
            )

    def test_render_prompt_with_empty_step_file_for_validation_command_raises_error(
        self, des_orchestrator
    ):
        """
        GIVEN /nw:execute command with empty step_file
        WHEN render_prompt is called
        THEN it should raise ValueError
        """
        import pytest

        with pytest.raises(
            ValueError, match="Step file required for validation commands"
        ):
            des_orchestrator.render_prompt(
                command="/nw:execute",
                agent="@software-crafter",
                step_file="",
            )

    def test_generate_des_markers_with_none_command_raises_value_error(
        self, des_orchestrator
    ):
        """
        GIVEN None as command parameter
        WHEN _generate_des_markers is called
        THEN it should raise ValueError
        """
        import pytest

        with pytest.raises(ValueError, match="Command cannot be None or empty"):
            des_orchestrator._generate_des_markers(
                command=None, step_file="steps/01-01.json"
            )

    def test_generate_des_markers_with_empty_command_raises_value_error(
        self, des_orchestrator
    ):
        """
        GIVEN empty string as command parameter
        WHEN _generate_des_markers is called
        THEN it should raise ValueError
        """
        import pytest

        with pytest.raises(ValueError, match="Command cannot be None or empty"):
            des_orchestrator._generate_des_markers(
                command="", step_file="steps/01-01.json"
            )

    def test_generate_des_markers_with_none_step_file_raises_value_error(
        self, des_orchestrator
    ):
        """
        GIVEN None as step_file parameter
        WHEN _generate_des_markers is called
        THEN it should raise ValueError
        """
        import pytest

        with pytest.raises(ValueError, match="Step file cannot be None or empty"):
            des_orchestrator._generate_des_markers(
                command="/nw:execute", step_file=None
            )

    def test_generate_des_markers_with_empty_step_file_raises_value_error(
        self, des_orchestrator
    ):
        """
        GIVEN empty string as step_file parameter
        WHEN _generate_des_markers is called
        THEN it should raise ValueError
        """
        import pytest

        with pytest.raises(ValueError, match="Step file cannot be None or empty"):
            des_orchestrator._generate_des_markers(command="/nw:execute", step_file="")

    def test_get_validation_level_with_none_command_defaults_to_none(
        self, des_orchestrator
    ):
        """
        GIVEN None as command parameter
        WHEN _get_validation_level is called
        THEN it returns "none" as safe default
        """
        validation_level = des_orchestrator._get_validation_level(None)
        assert validation_level == "none"

    def test_get_validation_level_with_empty_command_defaults_to_none(
        self, des_orchestrator
    ):
        """
        GIVEN empty string as command parameter
        WHEN _get_validation_level is called
        THEN it returns "none" as safe default
        """
        validation_level = des_orchestrator._get_validation_level("")
        assert validation_level == "none"


class TestOrchestratorHookIntegration:
    """Unit tests for DESOrchestrator hook integration."""

    def test_orchestrator_has_on_subagent_complete_method(self, des_orchestrator):
        """
        GIVEN DESOrchestrator class instantiated
        WHEN checking for on_subagent_complete method
        THEN method should exist and be callable
        """
        assert hasattr(des_orchestrator, "on_subagent_complete")
        assert callable(des_orchestrator.on_subagent_complete)

    def test_on_subagent_complete_returns_hook_result(
        self, des_orchestrator, in_memory_filesystem
    ):
        """
        GIVEN DESOrchestrator instance with valid step file
        WHEN on_subagent_complete is called
        THEN it should return a HookResult object
        """
        from pathlib import Path

        from des.application.orchestrator import HookResult

        # Seed in-memory filesystem with minimal step file
        step_file_path = Path("/test-step.json")
        step_data = {
            "task_specification": {"task_id": "01-01"},
            "state": {"status": "COMPLETED"},
            "tdd_cycle": {"phase_execution_log": []},
        }
        in_memory_filesystem.seed_file(step_file_path, step_data)

        result = des_orchestrator.on_subagent_complete(
            step_file_path=str(step_file_path)
        )

        assert isinstance(result, HookResult)

    def test_on_subagent_complete_delegates_to_hook(
        self, des_orchestrator, in_memory_filesystem
    ):
        """
        GIVEN DESOrchestrator instance
        WHEN on_subagent_complete is called with step file
        THEN it should delegate to SubagentStopHook.on_agent_complete
        """
        from pathlib import Path

        # Seed in-memory filesystem with minimal step file
        step_file_path = Path("/test-step.json")
        step_data = {
            "task_specification": {"task_id": "01-01"},
            "state": {"status": "COMPLETED"},
            "tdd_cycle": {"phase_execution_log": []},
        }
        in_memory_filesystem.seed_file(step_file_path, step_data)

        result = des_orchestrator.on_subagent_complete(
            step_file_path=str(step_file_path)
        )

        # Verify delegation worked (hook_fired should be True)
        assert result.hook_fired is True
