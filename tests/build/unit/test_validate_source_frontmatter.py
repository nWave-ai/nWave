"""Tests for source frontmatter validation script.

Validates that validate_source_frontmatter.py correctly checks
agent files (name, description, model) and command files (description),
reporting errors and returning appropriate exit codes.
"""

import subprocess
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "validation" / "validate_source_frontmatter.py"


# ---------------------------------------------------------------------------
# Acceptance test: script validates all source files and returns exit code
# ---------------------------------------------------------------------------


class TestValidateSourceFrontmatterAcceptance:
    """Acceptance: Script validates agents and commands, exits non-zero on failure."""

    def test_script_exits_zero_on_valid_source_files(self):
        """Running the script against the real repo must exit 0 (all files valid)."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, (
            f"Script exited with {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_script_reports_agents_and_commands_validated(self):
        """Output must mention both agents and commands were validated."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert "agent" in result.stdout.lower(), "Output should mention agents"
        assert "command" in result.stdout.lower(), "Output should mention commands"

    def test_script_exits_nonzero_for_invalid_files(self, tmp_path):
        """Script must exit non-zero when pointed at a directory with invalid files."""
        # Create an agent file missing required fields
        agents_dir = tmp_path / "nWave" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "nw-bad-agent.md").write_text(
            "---\nname: nw-bad-agent\n---\n# Bad agent\n"
        )
        # Create a command file missing description
        commands_dir = tmp_path / "nWave" / "tasks" / "nw"
        commands_dir.mkdir(parents=True)
        (commands_dir / "bad-cmd.md").write_text("---\ntitle: oops\n---\n# Bad\n")

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--project-root", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            f"Expected non-zero exit code for invalid files.\nstdout: {result.stdout}"
        )


# ---------------------------------------------------------------------------
# Unit tests: validation logic through the driving port (validate functions)
# ---------------------------------------------------------------------------


class TestValidateFrontmatterLogic:
    """Unit: Frontmatter validation logic via public API."""

    def _make_agent_file(self, tmp_path, name, frontmatter_dict):
        """Helper: create an agent .md file with given frontmatter."""
        agents_dir = tmp_path / "nWave" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        fm_yaml = yaml.dump(frontmatter_dict, default_flow_style=False)
        (agents_dir / f"{name}.md").write_text(f"---\n{fm_yaml}---\n# Agent\n")

    def _make_command_file(self, tmp_path, name, frontmatter_dict):
        """Helper: create a command .md file with given frontmatter."""
        cmds_dir = tmp_path / "nWave" / "tasks" / "nw"
        cmds_dir.mkdir(parents=True, exist_ok=True)
        fm_yaml = yaml.dump(frontmatter_dict, default_flow_style=False)
        (cmds_dir / f"{name}.md").write_text(f"---\n{fm_yaml}---\n# Command\n")

    def test_valid_agent_file_passes_validation(self, tmp_path):
        """Agent with name, description, model passes validation."""
        from scripts.validation.validate_source_frontmatter import validate_project

        self._make_agent_file(
            tmp_path,
            "nw-test-agent",
            {
                "name": "nw-test-agent",
                "description": "A test agent",
                "model": "inherit",
            },
        )
        # Ensure commands dir exists (empty is fine)
        (tmp_path / "nWave" / "tasks" / "nw").mkdir(parents=True, exist_ok=True)

        errors = validate_project(tmp_path)
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

    def test_agent_missing_description_fails(self, tmp_path):
        """Agent without description field must produce an error."""
        from scripts.validation.validate_source_frontmatter import validate_project

        self._make_agent_file(
            tmp_path,
            "nw-bad",
            {
                "name": "nw-bad",
                "model": "inherit",
            },
        )
        (tmp_path / "nWave" / "tasks" / "nw").mkdir(parents=True, exist_ok=True)

        errors = validate_project(tmp_path)
        assert len(errors) > 0
        assert any("description" in e.lower() for e in errors)

    def test_agent_missing_model_fails(self, tmp_path):
        """Agent without model field must produce an error."""
        from scripts.validation.validate_source_frontmatter import validate_project

        self._make_agent_file(
            tmp_path,
            "nw-nomodel",
            {
                "name": "nw-nomodel",
                "description": "Has desc",
            },
        )
        (tmp_path / "nWave" / "tasks" / "nw").mkdir(parents=True, exist_ok=True)

        errors = validate_project(tmp_path)
        assert len(errors) > 0
        assert any("model" in e.lower() for e in errors)

    def test_agent_without_frontmatter_fails(self, tmp_path):
        """Agent file without --- frontmatter must produce an error."""
        from scripts.validation.validate_source_frontmatter import validate_project

        agents_dir = tmp_path / "nWave" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "nw-nofm.md").write_text("# No frontmatter\nJust markdown.\n")
        (tmp_path / "nWave" / "tasks" / "nw").mkdir(parents=True, exist_ok=True)

        errors = validate_project(tmp_path)
        assert len(errors) > 0
        assert any("frontmatter" in e.lower() for e in errors)

    def test_valid_command_file_passes(self, tmp_path):
        """Command with description field passes validation."""
        from scripts.validation.validate_source_frontmatter import validate_project

        self._make_command_file(
            tmp_path,
            "test-cmd",
            {
                "description": "A test command",
            },
        )
        # Ensure agents dir exists (empty is fine)
        (tmp_path / "nWave" / "agents").mkdir(parents=True, exist_ok=True)

        errors = validate_project(tmp_path)
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

    def test_command_missing_description_fails(self, tmp_path):
        """Command without description field must produce an error."""
        from scripts.validation.validate_source_frontmatter import validate_project

        self._make_command_file(
            tmp_path,
            "bad-cmd",
            {
                "title": "not description",
            },
        )
        (tmp_path / "nWave" / "agents").mkdir(parents=True, exist_ok=True)

        errors = validate_project(tmp_path)
        assert len(errors) > 0
        assert any("description" in e.lower() for e in errors)

    def test_command_without_frontmatter_fails(self, tmp_path):
        """Command file without --- frontmatter must produce an error."""
        from scripts.validation.validate_source_frontmatter import validate_project

        cmds_dir = tmp_path / "nWave" / "tasks" / "nw"
        cmds_dir.mkdir(parents=True, exist_ok=True)
        (cmds_dir / "nofm.md").write_text("# No frontmatter\n")
        (tmp_path / "nWave" / "agents").mkdir(parents=True, exist_ok=True)

        errors = validate_project(tmp_path)
        assert len(errors) > 0
        assert any("frontmatter" in e.lower() for e in errors)
