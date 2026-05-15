"""Unit tests for DES config verification in DES plugin verify().

Tests validate the des-config.json check (step 5) added to verify():
- Config exists and is valid JSON: verify passes with config values in logs
- Config missing (with .nwave/ dir): auto-created; state-delta exposes hidden mutations
- Config missing (.nwave/ dir absent): verify fails with 'DES config not found'
- Config has invalid JSON: verify fails with 'not valid JSON'
- Config without audit_log_dir: log shows 'log_dir=not set'

All other verify() checks (module import, scripts, templates, hooks) are
satisfied via fixtures so these tests isolate the des-config.json behavior.

CRITICAL: Tests follow hexagonal architecture.
DESPlugin is the driving port; subprocess is mocked at port boundary.

State-delta migration summary
------------------------------
CONVERTED (1 test) — assert_state_delta + implicit-unchanged invariant:
  - test_verify_migrates_config_when_nwave_dir_exists: filesystem multi-slot
    (config_file.exists) + config multi-slot (audit_logging_enabled, audit_log_dir);
    implicit-unchanged catches any undeclared key written to the config.

MERGED (3 → 1 test):
  - test_verify_passes_when_des_config_exists (result.success + log values)
  - test_verify_logs_des_config_check (log path and TUI labels)
  - test_verify_shows_audit_logging_on_when_enabled (audit_logging=on label)
  → merged into test_verify_passes_with_valid_config (all three covered one
    behavior: valid config → pass + logs show config values)

KEPT as-is (4 tests) — no state-delta benefit:
  - test_verify_fails_when_nwave_dir_missing: failure path; result.errors assertion
  - test_verify_fails_when_des_config_invalid_json: failure path; result.errors assertion
  - test_verify_shows_not_set_when_log_dir_missing: distinct scenario (partial config);
    log mock assertion; no filesystem mutation to track
  - test_verify_passes_with_valid_config: read-only verify path; primary assertions
    are on logger mock calls, not filesystem writes

Hidden mutations found: 1 detected.
  test_verify_migrates_config_when_nwave_dir_exists: previously asserted only
  config_file.exists + two explicit config keys, missing the implicit contract
  that NO other key is written. assert_state_delta now enforces this via
  implicit-unchanged across the full config universe.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from nwave_ai.state_delta import assert_state_delta, set_to

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin


# ---------------------------------------------------------------------------
# State-delta helpers
# ---------------------------------------------------------------------------


def _flatten_config(config_path: Path) -> dict[str, object]:
    """Return a flat dict with dotted-path keys for a JSON config file.

    Example: {"audit_logging_enabled": True, "audit_log_dir": ".nwave/des/logs"}
    becomes  {"audit_logging_enabled": True, "audit_log_dir": ".nwave/des/logs"}.

    For nested dicts: {"a": {"b": 1}} becomes {"a.b": 1}.
    Returns an empty dict when the file does not exist.
    """
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        raw: dict[str, object] = json.load(f)

    result: dict[str, object] = {}

    def _recurse(node: object, prefix: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                _recurse(v, f"{prefix}.{k}" if prefix else k)
        else:
            result[prefix] = node

    _recurse(raw, "")
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
                            "command": (
                                "INPUT=$(cat); "
                                "echo \"$INPUT\" | grep -q 'execution-log\\.json' && "
                                '{ echo "$INPUT" | PYTHONPATH=$HOME/.claude/lib/python python3 -m '
                                "des.adapters.drivers.hooks.claude_code_hook_adapter pre-write; exit $?; }; "
                                "test -f .nwave/des/deliver-session.json || exit 0; "
                                'echo "$INPUT" | PYTHONPATH=$HOME/.claude/lib/python python3 -m '
                                "des.adapters.drivers.hooks.claude_code_hook_adapter pre-write"
                            ),
                        }
                    ],
                },
                {
                    "matcher": "Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                "INPUT=$(cat); "
                                "echo \"$INPUT\" | grep -q 'execution-log\\.json' && "
                                '{ echo "$INPUT" | PYTHONPATH=$HOME/.claude/lib/python python3 -m '
                                "des.adapters.drivers.hooks.claude_code_hook_adapter pre-edit; exit $?; }; "
                                "test -f .nwave/des/deliver-session.json || exit 0; "
                                'echo "$INPUT" | PYTHONPATH=$HOME/.claude/lib/python python3 -m '
                                "des.adapters.drivers.hooks.claude_code_hook_adapter pre-edit"
                            ),
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDESConfigVerify:
    """Test des-config.json verification in DES plugin verify()."""

    @patch("subprocess.run")
    def test_verify_passes_with_valid_config(self, mock_subprocess, des_env):
        """
        GIVEN: A complete DES installation with valid .nwave/des-config.json
               containing audit_logging_enabled=True and audit_log_dir set
        WHEN: verify() is called
        THEN: Returns success with 'config OK' in the message
              AND logger emits TUI lines showing config path, audit_logging=on,
              and log_dir value
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

        log_messages = [str(call) for call in context.logger.info.call_args_list]
        log_text = " ".join(log_messages)
        assert "Verifying DES config" in log_text
        assert "DES config (" in log_text
        assert "des-config.json" in log_text
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
              AND audit_log_dir='.nwave/des/logs'
              AND no undeclared key is written to the config (implicit-unchanged)
              AND returns success
        """
        plugin, context, project_root = des_env

        # Check 1: mock subprocess for DES module import
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        # Create .nwave/ dir but NOT des-config.json
        nwave_dir = project_root / ".nwave"
        nwave_dir.mkdir(parents=True, exist_ok=True)
        config_file = nwave_dir / "des-config.json"

        # Snapshot filesystem + config state before
        before_fs: dict[str, object] = {"config_file.exists": config_file.exists()}
        before_config = _flatten_config(config_file)

        result = plugin.verify(context)

        assert result.success is True

        after_fs: dict[str, object] = {"config_file.exists": config_file.exists()}
        after_config = _flatten_config(config_file)

        # Filesystem slot: config file must have been created
        assert_state_delta(
            before=before_fs,
            after=after_fs,
            universe={"config_file.exists"},
            expected={"config_file.exists": set_to(True)},
        )

        # Config slots: exactly the two expected keys written; no undeclared mutations
        config_universe = set(before_config.keys()) | set(after_config.keys())
        assert_state_delta(
            before=before_config,
            after=after_config,
            universe=config_universe,
            expected={
                "audit_logging_enabled": set_to(True),
                "audit_log_dir": set_to(".nwave/des/logs"),
            },
        )

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
