"""Unit tests for DES config verification in DES plugin verify().

Tests validate the des-config.json check (step 5) added to verify():
- Config exists and is valid JSON: verify passes with 'config OK' in message
- Config values shown: audit_logging=on/off and log_dir displayed in output
- Config missing: verify fails with 'DES config not found' error
- Config has invalid JSON: verify fails with 'not valid JSON' error
- TUI log lines emitted for the config check step with path and values

All other verify() checks (module import, scripts, templates, hooks) are
satisfied via fixtures so these tests isolate the des-config.json behavior.

CRITICAL: Tests follow hexagonal architecture.
DESPlugin is the driving port; subprocess is mocked at port boundary.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin


@pytest.fixture()
def des_env(tmp_path):
    """Set up a complete DES installation environment.

    Satisfies checks 1-4 of verify() so tests can isolate check 5 (des-config.json).
    Returns (plugin, context, project_root) tuple.
    """
    claude_dir = tmp_path / ".claude"
    project_root = tmp_path / "project"
    project_root.mkdir()

    # Check 2: DES scripts
    scripts_dir = claude_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    for script in DESPlugin.DES_SCRIPTS:
        (scripts_dir / script).write_text(f"# {script}")

    # Check 3: DES templates
    templates_dir = claude_dir / "templates"
    templates_dir.mkdir(parents=True)
    for template in DESPlugin.DES_TEMPLATES:
        (templates_dir / template).write_text(f"# {template}")

    # Check 4: settings.json with DES hooks (nested format)
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Task",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "PYTHONPATH=$HOME/.claude/lib/python python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter pre-task",
                        }
                    ],
                },
                {
                    "matcher": "Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "test -f .nwave/des/deliver-session.json || exit 0; PYTHONPATH=$HOME/.claude/lib/python python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter pre-write",
                        }
                    ],
                },
                {
                    "matcher": "Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "test -f .nwave/des/deliver-session.json || exit 0; PYTHONPATH=$HOME/.claude/lib/python python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter pre-edit",
                        }
                    ],
                },
            ],
            "SubagentStop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "PYTHONPATH=$HOME/.claude/lib/python python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter subagent-stop",
                        }
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Task",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "PYTHONPATH=$HOME/.claude/lib/python python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter post-tool-use",
                        }
                    ],
                }
            ],
        }
    }
    settings_file = claude_dir / "settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps(settings, indent=2))

    logger = MagicMock()
    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=scripts_dir,
        templates_dir=templates_dir,
        logger=logger,
        project_root=project_root,
        framework_source=None,
    )

    plugin = DESPlugin()
    return plugin, context, project_root


class TestDESConfigVerify:
    """Test des-config.json verification in DES plugin verify()."""

    @patch("subprocess.run")
    def test_verify_passes_when_des_config_exists(self, mock_subprocess, des_env):
        """
        GIVEN: A complete DES installation with valid .nwave/des-config.json
        WHEN: verify() is called
        THEN: Returns success with 'config OK' in the message
              AND logger output shows audit_logging=off and log_dir value
        """
        plugin, context, project_root = des_env

        # Check 1: mock subprocess for DES module import
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        # Check 5: create valid des-config.json with defaults
        nwave_dir = project_root / ".nwave"
        nwave_dir.mkdir(parents=True)
        config_file = nwave_dir / "des-config.json"
        config_file.write_text(
            json.dumps(
                {"audit_logging_enabled": True, "audit_log_dir": ".nwave/des/logs"}
            )
        )

        result = plugin.verify(context)

        assert result.success is True
        assert "config OK" in result.message

        # Verify the new format shows config values
        log_messages = [str(call) for call in context.logger.info.call_args_list]
        log_text = " ".join(log_messages)
        assert "audit_logging=on" in log_text
        assert "log_dir=.nwave/des/logs" in log_text

    @patch("subprocess.run")
    def test_verify_migrates_config_when_nwave_dir_exists(
        self, mock_subprocess, des_env
    ):
        """
        GIVEN: A DES installation with .nwave/ dir but NO des-config.json
        WHEN: verify() is called
        THEN: Auto-creates des-config.json with audit_logging_enabled=True
              AND returns success
        """
        plugin, context, project_root = des_env

        # Check 1: mock subprocess for DES module import
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        # Create .nwave/ dir but NOT des-config.json
        nwave_dir = project_root / ".nwave"
        nwave_dir.mkdir(parents=True, exist_ok=True)

        result = plugin.verify(context)

        assert result.success is True
        # Verify file was created with correct defaults
        config_file = nwave_dir / "des-config.json"
        assert config_file.exists()
        created_config = json.loads(config_file.read_text())
        assert created_config["audit_logging_enabled"] is True
        assert created_config["audit_log_dir"] == ".nwave/des/logs"

    @patch("subprocess.run")
    def test_verify_fails_when_nwave_dir_missing(self, mock_subprocess, des_env):
        """
        GIVEN: A DES installation WITHOUT .nwave/ directory at all
        WHEN: verify() is called
        THEN: Returns failure with 'DES config not found' in errors
        """
        plugin, context, _project_root = des_env

        # Check 1: mock subprocess for DES module import
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        # No .nwave/ dir and no des-config.json

        result = plugin.verify(context)

        assert result.success is False
        assert any("DES config not found" in e for e in result.errors)

    @patch("subprocess.run")
    def test_verify_fails_when_des_config_invalid_json(self, mock_subprocess, des_env):
        """
        GIVEN: A DES installation with .nwave/des-config.json containing invalid JSON
        WHEN: verify() is called
        THEN: Returns failure with 'not valid JSON' in errors
        """
        plugin, context, project_root = des_env

        # Check 1: mock subprocess for DES module import
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        # Check 5: create invalid des-config.json
        nwave_dir = project_root / ".nwave"
        nwave_dir.mkdir(parents=True)
        config_file = nwave_dir / "des-config.json"
        config_file.write_text("{not valid json content!!!")

        result = plugin.verify(context)

        assert result.success is False
        assert any("not valid JSON" in e for e in result.errors)

    @patch("subprocess.run")
    def test_verify_logs_des_config_check(self, mock_subprocess, des_env):
        """
        GIVEN: A complete DES installation with valid des-config.json
        WHEN: verify() is called
        THEN: Logger emits TUI lines showing config path and values
        """
        plugin, context, project_root = des_env

        # Check 1: mock subprocess for DES module import
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        # Check 5: create valid des-config.json
        nwave_dir = project_root / ".nwave"
        nwave_dir.mkdir(parents=True)
        config_file = nwave_dir / "des-config.json"
        config_file.write_text(
            json.dumps(
                {"audit_logging_enabled": True, "audit_log_dir": ".nwave/des/logs"}
            )
        )

        result = plugin.verify(context)

        assert result.success is True
        log_messages = [str(call) for call in context.logger.info.call_args_list]
        log_text = " ".join(log_messages)
        assert "Verifying DES config" in log_text
        # New format: shows path and config values instead of plain "DES config verified"
        assert "DES config (" in log_text
        assert "des-config.json" in log_text
        assert "audit_logging=on" in log_text
        assert "log_dir=.nwave/des/logs" in log_text

    @patch("subprocess.run")
    def test_verify_shows_audit_logging_on_when_enabled(self, mock_subprocess, des_env):
        """
        GIVEN: A DES config with audit_logging_enabled=True
        WHEN: verify() is called
        THEN: Logger output shows 'audit_logging=on'
        """
        plugin, context, project_root = des_env

        # Check 1: mock subprocess for DES module import
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        # Check 5: create des-config.json with audit logging enabled
        nwave_dir = project_root / ".nwave"
        nwave_dir.mkdir(parents=True)
        config_file = nwave_dir / "des-config.json"
        config_file.write_text(
            json.dumps(
                {"audit_logging_enabled": True, "audit_log_dir": ".nwave/des/logs"}
            )
        )

        result = plugin.verify(context)

        assert result.success is True
        log_messages = [str(call) for call in context.logger.info.call_args_list]
        log_text = " ".join(log_messages)
        assert "audit_logging=on" in log_text

    @patch("subprocess.run")
    def test_verify_shows_not_set_when_log_dir_missing(self, mock_subprocess, des_env):
        """
        GIVEN: A DES config with only audit_logging_enabled (no audit_log_dir key)
        WHEN: verify() is called
        THEN: Logger output shows 'log_dir=not set'
        """
        plugin, context, project_root = des_env

        # Check 1: mock subprocess for DES module import
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        # Check 5: create des-config.json WITHOUT audit_log_dir
        nwave_dir = project_root / ".nwave"
        nwave_dir.mkdir(parents=True)
        config_file = nwave_dir / "des-config.json"
        config_file.write_text(json.dumps({"audit_logging_enabled": True}))

        result = plugin.verify(context)

        assert result.success is True
        log_messages = [str(call) for call in context.logger.info.call_args_list]
        log_text = " ".join(log_messages)
        assert "log_dir=not set" in log_text
