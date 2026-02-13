"""Unit tests for DES hook installer."""

import json
import subprocess
import sys


class TestInstallDESHooks:
    """Test installer merges DES hooks into settings.json."""

    def test_install_merges_hooks_into_existing_config(self, tmp_path):
        """Install merges DES hooks into existing .claude/settings.json."""
        # Given: existing .claude/settings.json with non-DES hooks
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"

        existing_config = {
            "hooks": {
                "PreToolUse": [{"matcher": "OtherTool", "command": "other_command"}],
                "SubagentStop": [{"command": "other_stop_command"}],
            }
        }
        settings_file.write_text(json.dumps(existing_config, indent=2))

        # When: run installer
        result = subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--install",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # Then: installer succeeds
        assert result.returncode == 0, f"Installer failed: {result.stderr}"

        # And: DES hooks are added
        config = json.loads(settings_file.read_text())
        assert "hooks" in config
        assert "PreToolUse" in config["hooks"]
        assert "SubagentStop" in config["hooks"]
        assert "PostToolUse" in config["hooks"]

        # And: DES PreToolUse hook exists (nested format)
        des_pre_hook = next(
            (
                h
                for h in config["hooks"]["PreToolUse"]
                if any(
                    "claude_code_hook_adapter" in sub.get("command", "")
                    for sub in h.get("hooks", [])
                )
            ),
            None,
        )
        assert des_pre_hook is not None, "DES PreToolUse hook not found"
        assert des_pre_hook["matcher"] == "Task"

        # And: DES SubagentStop hook exists (nested format)
        des_stop_hook = next(
            (
                h
                for h in config["hooks"]["SubagentStop"]
                if any(
                    "claude_code_hook_adapter" in sub.get("command", "")
                    for sub in h.get("hooks", [])
                )
            ),
            None,
        )
        assert des_stop_hook is not None, "DES SubagentStop hook not found"

        # And: existing hooks preserved
        assert len(config["hooks"]["PreToolUse"]) == 2
        assert len(config["hooks"]["SubagentStop"]) == 2
        other_pre = next(
            h for h in config["hooks"]["PreToolUse"] if h.get("matcher") == "OtherTool"
        )
        assert other_pre["command"] == "other_command"

    def test_install_creates_settings_file_if_missing(self, tmp_path):
        """Install creates .claude/settings.json if it doesn't exist."""
        # Given: .claude directory exists but settings.json doesn't
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"

        # When: run installer
        result = subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--install",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # Then: installer succeeds
        assert result.returncode == 0, f"Installer failed: {result.stderr}"

        # And: settings file created
        assert settings_file.exists()

        # And: DES hooks configured
        config = json.loads(settings_file.read_text())
        assert "hooks" in config
        assert len(config["hooks"]["PreToolUse"]) == 1
        assert len(config["hooks"]["SubagentStop"]) == 1
        assert len(config["hooks"]["PostToolUse"]) == 1

    def test_install_is_idempotent(self, tmp_path):
        """Install detects existing DES hooks and doesn't duplicate."""
        # Given: empty config dir
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # When: run installer twice
        for _ in range(2):
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/install/install_des_hooks.py",
                    "--install",
                    "--config-dir",
                    str(claude_dir),
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Installer failed: {result.stderr}"

        # Then: no duplicate hooks created
        config = json.loads((claude_dir / "settings.json").read_text())
        assert len(config["hooks"]["PreToolUse"]) == 1
        assert len(config["hooks"]["SubagentStop"]) == 1
        assert len(config["hooks"]["PostToolUse"]) == 1

    def test_install_configures_pretooluse_hook_correctly(self, tmp_path):
        """Install configures PreToolUse hook with Task matcher and python3 -m command."""
        # Given: empty config
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # When: run installer
        subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--install",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # Then: PreToolUse hook configured correctly (nested format)
        config = json.loads((claude_dir / "settings.json").read_text())
        pre_hook = config["hooks"]["PreToolUse"][0]

        assert pre_hook["matcher"] == "Task"
        assert "hooks" in pre_hook
        assert len(pre_hook["hooks"]) == 1

        inner = pre_hook["hooks"][0]
        assert inner["type"] == "command"
        assert "-m" in inner["command"]
        assert "claude_code_hook_adapter" in inner["command"]
        assert "pre-task" in inner["command"]

    def test_install_configures_agentstop_hook_correctly(self, tmp_path):
        """Install configures SubagentStop hook with python3 -m command."""
        # Given: empty config
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # When: run installer
        subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--install",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # Then: SubagentStop hook configured correctly (nested format)
        config = json.loads((claude_dir / "settings.json").read_text())
        stop_hook = config["hooks"]["SubagentStop"][0]

        assert "hooks" in stop_hook
        assert len(stop_hook["hooks"]) == 1

        inner = stop_hook["hooks"][0]
        assert inner["type"] == "command"
        assert "-m" in inner["command"]
        assert "claude_code_hook_adapter" in inner["command"]
        assert "subagent-stop" in inner["command"]

    def test_install_configures_posttooluse_hook_correctly(self, tmp_path):
        """Install configures PostToolUse hook with Task matcher and python3 -m command."""
        # Given: empty config
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # When: run installer
        subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--install",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # Then: PostToolUse hook configured correctly (nested format)
        config = json.loads((claude_dir / "settings.json").read_text())
        assert "PostToolUse" in config["hooks"]
        post_hook = config["hooks"]["PostToolUse"][0]

        assert post_hook["matcher"] == "Task"
        assert "hooks" in post_hook
        assert len(post_hook["hooks"]) == 1

        inner = post_hook["hooks"][0]
        assert inner["type"] == "command"
        assert "-m" in inner["command"]
        assert "claude_code_hook_adapter" in inner["command"]
        assert "post-tool-use" in inner["command"]

    def test_uninstall_removes_only_des_hooks(self, tmp_path):
        """Uninstall removes only DES hooks, preserves others."""
        # Given: settings with DES and non-DES hooks (install first, then add non-DES)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"

        # Install DES hooks first
        subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--install",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # Add non-DES hooks
        config = json.loads(settings_file.read_text())
        config["hooks"]["PreToolUse"].append(
            {"matcher": "OtherTool", "command": "other_command"}
        )
        config["hooks"]["SubagentStop"].append({"command": "other_stop_command"})
        settings_file.write_text(json.dumps(config, indent=2))

        # When: run uninstaller
        result = subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--uninstall",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # Then: uninstaller succeeds
        assert result.returncode == 0, f"Uninstaller failed: {result.stderr}"

        # And: DES hooks removed
        config = json.loads(settings_file.read_text())
        des_pre = [
            h
            for h in config["hooks"]["PreToolUse"]
            if any(
                "claude_code_hook_adapter" in sub.get("command", "")
                for sub in h.get("hooks", [])
            )
        ]
        des_stop = [
            h
            for h in config["hooks"]["SubagentStop"]
            if any(
                "claude_code_hook_adapter" in sub.get("command", "")
                for sub in h.get("hooks", [])
            )
        ]
        des_post = [
            h
            for h in config["hooks"].get("PostToolUse", [])
            if any(
                "claude_code_hook_adapter" in sub.get("command", "")
                for sub in h.get("hooks", [])
            )
        ]
        assert len(des_pre) == 0
        assert len(des_stop) == 0
        assert len(des_post) == 0

        # And: other hooks preserved
        assert len(config["hooks"]["PreToolUse"]) == 1
        assert len(config["hooks"]["SubagentStop"]) == 1
        assert config["hooks"]["PreToolUse"][0]["matcher"] == "OtherTool"

    def test_uninstall_handles_missing_file_gracefully(self, tmp_path):
        """Uninstall succeeds when settings.json doesn't exist."""
        # Given: .claude directory exists but settings file doesn't
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # When: run uninstaller
        result = subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--uninstall",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # Then: uninstaller succeeds without error
        assert result.returncode == 0, f"Uninstaller failed: {result.stderr}"

    def test_merged_config_is_valid_json(self, tmp_path):
        """Merged configuration validates as valid JSON."""
        # Given: empty config
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # When: run installer
        subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--install",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # Then: config file is valid JSON
        settings_file = claude_dir / "settings.json"
        config_text = settings_file.read_text()

        # Should not raise exception
        config = json.loads(config_text)
        assert isinstance(config, dict)

    def test_status_detects_installed_state(self, tmp_path):
        """Status command detects whether hooks are installed."""
        # Given: DES hooks installed
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--install",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # When: run status command
        result = subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--status",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # Then: status reports installed
        assert result.returncode == 0
        assert "installed" in result.stdout.lower()

    def test_status_detects_not_installed_state(self, tmp_path):
        """Status command detects when hooks are not installed."""
        # Given: no DES hooks
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # When: run status command
        result = subprocess.run(
            [
                sys.executable,
                "scripts/install/install_des_hooks.py",
                "--status",
                "--config-dir",
                str(claude_dir),
            ],
            capture_output=True,
            text=True,
        )

        # Then: status reports not installed
        assert result.returncode == 0
        assert "not installed" in result.stdout.lower()
