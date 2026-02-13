"""Integration tests for DES hook configuration and installation.

Tests verify that:
1. Hook adapter module exists and is referenced correctly
2. Installation scripts configure hooks with correct paths
3. Hooks point to claude_code_hook_adapter module (not missing files)

These tests MUST fail if claude_code_hook_adapter.py is deleted or not referenced.
"""

import json
from pathlib import Path

import pytest


class TestHookAdapterReference:
    """Test that hook adapter is correctly referenced in installation config."""

    def test_hook_adapter_module_exists(self):
        """MUST FAIL if claude_code_hook_adapter.py is missing.

        This test ensures the CLI entry point exists in the codebase.
        If this test fails, the hooks cannot work (module not found error).
        """
        adapter_path = (
            Path(__file__).parent.parent.parent.parent
            / "src/des/adapters/drivers/hooks/claude_code_hook_adapter.py"
        )

        assert adapter_path.exists(), (
            f"Hook adapter module not found: {adapter_path}\n"
            "This file is REQUIRED for DES hooks to work.\n"
            "If deleted, restore from git: git show c8dca89^:src/des/adapters/drivers/hooks/claude_code_hook_adapter.py"
        )

    def test_hook_adapter_is_importable(self):
        """MUST FAIL if hook adapter has import errors.

        Verifies the module can be imported without errors.
        """
        try:
            from des.adapters.drivers.hooks import claude_code_hook_adapter

            # Verify expected functions exist
            assert hasattr(claude_code_hook_adapter, "handle_pre_tool_use")
            assert hasattr(claude_code_hook_adapter, "handle_subagent_stop")
            assert hasattr(claude_code_hook_adapter, "main")
        except ImportError as e:
            pytest.fail(f"Hook adapter cannot be imported: {e}")

    def test_hook_adapter_has_main_entry_point(self):
        """Verify hook adapter can run as CLI module."""
        from des.adapters.drivers.hooks import claude_code_hook_adapter

        # Test main() exists and is callable
        assert callable(claude_code_hook_adapter.main)

        # Verify main() handles commands correctly (mock sys.argv)
        import sys

        original_argv = sys.argv.copy()
        try:
            sys.argv = ["claude_code_hook_adapter.py"]  # No command
            with pytest.raises(SystemExit) as exc_info:
                claude_code_hook_adapter.main()
            assert exc_info.value.code == 1, (
                "Expected error exit code when command missing"
            )
        finally:
            sys.argv = original_argv


class TestHookInstallerConfiguration:
    """Test that hook installer references claude_code_hook_adapter correctly."""

    def test_standalone_installer_references_hook_adapter(self):
        """MUST FAIL if install_des_hooks.py doesn't reference claude_code_hook_adapter.

        Verifies the standalone installer script configures hooks correctly.
        """
        installer_path = (
            Path(__file__).parent.parent.parent.parent
            / "scripts/install/install_des_hooks.py"
        )

        assert installer_path.exists(), "Installer script not found"

        with open(installer_path, encoding="utf-8") as f:
            installer_code = f.read()

        # CRITICAL: Installer MUST reference claude_code_hook_adapter
        assert "claude_code_hook_adapter" in installer_code, (
            "Installer does not reference claude_code_hook_adapter!\n"
            "Hooks will fail with 'module not found' error.\n"
            "Update DES_PRETOOLUSE_HOOK and DES_SUBAGENT_STOP_HOOK constants."
        )

        # Verify both hook types reference the adapter
        assert installer_code.count("claude_code_hook_adapter") >= 2, (
            "Expected at least 2 references to claude_code_hook_adapter "
            "(one for PreToolUse, one for SubagentStop)"
        )

    def test_plugin_installer_references_hook_adapter(self):
        """MUST FAIL if des_plugin.py doesn't reference claude_code_hook_adapter.

        Verifies the plugin installer configures hooks correctly.
        """
        plugin_path = (
            Path(__file__).parent.parent.parent.parent
            / "scripts/install/plugins/des_plugin.py"
        )

        assert plugin_path.exists(), "Plugin installer not found"

        with open(plugin_path, encoding="utf-8") as f:
            plugin_code = f.read()

        # CRITICAL: Plugin MUST reference claude_code_hook_adapter
        assert "claude_code_hook_adapter" in plugin_code, (
            "Plugin installer does not reference claude_code_hook_adapter!\n"
            "Hooks installed via /nw:install will not work.\n"
            "Update HOOK_COMMAND_TEMPLATE constant."
        )

    def test_hook_command_format_is_correct(self):
        """Verify hook commands use python -m module format (not direct .py).

        Schema v2.0 requirement: Use -m format for PYTHONPATH compatibility.
        """
        plugin_path = (
            Path(__file__).parent.parent.parent.parent
            / "scripts/install/plugins/des_plugin.py"
        )

        with open(plugin_path, encoding="utf-8") as f:
            plugin_code = f.read()

        # Expected format: "{python_path} -m des.adapters.drivers.hooks.claude_code_hook_adapter"
        # The template uses {python_path} which is substituted with sys.executable at install time
        assert "-m" in plugin_code and "python" in plugin_code, (
            "Hook command should use 'python -m' format (not direct .py path)"
        )
        assert "des.adapters.drivers.hooks.claude_code_hook_adapter" in plugin_code, (
            "Hook command missing module path"
        )


class TestHookConfigurationIntegrity:
    """Test installed hook configuration integrity."""

    @staticmethod
    def _is_des_hook_entry(hook_entry: dict) -> bool:
        """Check if a hook entry is a DES hook (supports both old and new format)."""
        # Old flat format: {"command": "...claude_code_hook_adapter..."}
        if "claude_code_hook_adapter" in hook_entry.get("command", ""):
            return True
        # New nested format: {"hooks": [{"type": "command", "command": "...claude_code_hook_adapter..."}]}
        for h in hook_entry.get("hooks", []):
            if "claude_code_hook_adapter" in h.get("command", ""):
                return True
        return False

    @staticmethod
    def _has_nested_format(hook_entry: dict) -> bool:
        """Check if hook entry uses Claude Code v2 nested format."""
        return "hooks" in hook_entry and isinstance(hook_entry["hooks"], list)

    def test_global_settings_json_has_des_hooks(self):
        """Verify ~/.claude/settings.json has DES hooks with correct nested format.

        DES hooks MUST be in the global config (~/.claude/settings.json) to ensure
        they fire for all projects. Project-level settings are not used for hooks.
        """
        settings_path = Path.home() / ".claude/settings.json"

        if not settings_path.exists():
            pytest.skip("~/.claude/settings.json not found (not yet installed)")

        with open(settings_path, encoding="utf-8") as f:
            config = json.load(f)

        assert "hooks" in config, (
            "No hooks in ~/.claude/settings.json!\n"
            "Run: python3 scripts/install/install_des_hooks.py --install"
        )

        hooks = config["hooks"]

        # Find DES hooks
        pre_hooks = hooks.get("PreToolUse", [])
        stop_hooks = hooks.get("SubagentStop", [])

        des_pre = [h for h in pre_hooks if self._is_des_hook_entry(h)]
        des_stop = [h for h in stop_hooks if self._is_des_hook_entry(h)]

        assert len(des_pre) > 0, (
            "No DES PreToolUse hook in ~/.claude/settings.json!\n"
            "Run: python3 scripts/install/install_des_hooks.py --install"
        )

        assert len(des_stop) > 0, (
            "No DES SubagentStop hook in ~/.claude/settings.json!\n"
            "Run: python3 scripts/install/install_des_hooks.py --install"
        )

        # Verify Claude Code v2 nested format (required for hooks to fire)
        for hook in des_pre:
            assert self._has_nested_format(hook), (
                f"PreToolUse DES hook uses old flat format: {hook}\n"
                "Claude Code requires nested format: "
                '{"hooks": [{"type": "command", "command": "..."}]}'
            )

        for hook in des_stop:
            assert self._has_nested_format(hook), (
                f"SubagentStop DES hook uses old flat format: {hook}\n"
                "Claude Code requires nested format: "
                '{"hooks": [{"type": "command", "command": "..."}]}'
            )

    def test_installed_module_has_hook_adapter(self):
        """Verify installed DES module includes claude_code_hook_adapter.

        NOTE: May be skipped if module not installed via /nw:install.
        """
        installed_module_path = (
            Path.home()
            / ".claude/lib/python/des/adapters/drivers/hooks/claude_code_hook_adapter.py"
        )

        if not installed_module_path.parent.exists():
            pytest.skip("DES module not installed (run /nw:install)")

        # CRITICAL: Installed module MUST include the hook adapter
        assert installed_module_path.exists(), (
            f"Hook adapter not found in installed module: {installed_module_path}\n"
            "This means hooks are configured but the module is missing!\n"
            "Re-run /nw:install to fix installation."
        )


class TestHookAdapterFunctionality:
    """Test that hook adapter works correctly with Schema v2.0."""

    def test_hook_adapter_accepts_schema_v2_input(self):
        """Verify hook adapter handles Schema v2.0 input format.

        Schema v2.0 input:
            {
                "executionLogPath": "/abs/path",
                "projectId": "foo",
                "stepId": "01-01"
            }

        NOTE: Only checks PUBLIC interface (handle_subagent_stop).
        Internal validation functions are implementation details.
        """
        from des.adapters.drivers.hooks import claude_code_hook_adapter

        # Verify public interface for Schema v2.0 handling exists
        assert hasattr(claude_code_hook_adapter, "handle_subagent_stop"), (
            "Hook adapter missing handle_subagent_stop (Schema v2.0 entry point)"
        )

    def test_pre_tool_use_reads_tool_input_from_top_level(self):
        """Regression: PreToolUse must read tool_input at top level, not nested under tool.input.

        Claude Code sends: {"tool_name": "Task", "tool_input": {"max_turns": 30, ...}}
        NOT: {"tool": {"input": {"max_turns": 30, ...}}}

        Bug (fixed 2026-02-06): handle_pre_tool_use() read hook_input["tool"]["input"]
        which always returned {} because Claude Code puts tool_input at the top level.
        This caused MISSING_MAX_TURNS for ALL Task invocations even with max_turns set.
        """
        import sys
        from io import StringIO

        from des.adapters.drivers.hooks import claude_code_hook_adapter

        # Claude Code protocol: tool_input at top level
        test_input = json.dumps(
            {
                "session_id": "test-session",
                "hook_event_name": "PreToolUse",
                "tool_name": "Task",
                "tool_input": {
                    "prompt": "Find all Python files",
                    "max_turns": 30,
                    "subagent_type": "Explore",
                },
            }
        )

        original_stdin = sys.stdin
        original_stdout = sys.stdout
        try:
            sys.stdin = StringIO(test_input)
            sys.stdout = captured = StringIO()

            exit_code = claude_code_hook_adapter.handle_pre_tool_use()

            output = json.loads(captured.getvalue())
            assert exit_code == 0, (
                f"Expected allow (exit 0) for valid tool_input with max_turns=30, "
                f"got exit {exit_code}: {output}"
            )
            assert output["decision"] == "allow"
        finally:
            sys.stdin = original_stdin
            sys.stdout = original_stdout

    def test_pre_tool_use_rejects_missing_max_turns(self):
        """PreToolUse must block when max_turns is absent from tool_input."""
        import sys
        from io import StringIO

        from des.adapters.drivers.hooks import claude_code_hook_adapter

        test_input = json.dumps(
            {
                "tool_name": "Task",
                "tool_input": {
                    "prompt": "Find all Python files",
                    "subagent_type": "Explore",
                },
            }
        )

        original_stdin = sys.stdin
        original_stdout = sys.stdout
        try:
            sys.stdin = StringIO(test_input)
            sys.stdout = captured = StringIO()

            exit_code = claude_code_hook_adapter.handle_pre_tool_use()

            output = json.loads(captured.getvalue())
            assert exit_code == 2, (
                f"Expected block (exit 2) for missing max_turns, "
                f"got exit {exit_code}: {output}"
            )
            assert output["decision"] == "block"
            assert "MISSING_MAX_TURNS" in output["reason"]
        finally:
            sys.stdin = original_stdin
            sys.stdout = original_stdout

    def test_hook_adapter_rejects_missing_required_fields(self):
        """Test that hook adapter validates Schema v2.0 required fields.

        This is a unit test verifying the adapter's input validation.
        """
        import sys
        from io import StringIO

        from des.adapters.drivers.hooks import claude_code_hook_adapter

        # Mock stdin with missing fields
        test_input = json.dumps(
            {"executionLogPath": "/tmp/log.yaml"}
        )  # Missing projectId, stepId

        original_stdin = sys.stdin
        original_stdout = sys.stdout
        try:
            sys.stdin = StringIO(test_input)
            sys.stdout = StringIO()

            exit_code = claude_code_hook_adapter.handle_subagent_stop()

            # Should fail (exit 1) due to missing required fields
            assert exit_code == 1, (
                "Expected error exit code for missing required fields"
            )
        finally:
            sys.stdin = original_stdin
            sys.stdout = original_stdout
