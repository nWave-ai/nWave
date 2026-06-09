"""Tests for the shared hook definitions module.

Driving port: hook_definitions module (pure functions).
Tests verify the canonical hook definitions produce correct configs
for both distribution paths (plugin and installer).

Test Budget: 10 distinct behaviors x 2 = 20 max unit tests.
Behaviors:
  1. Hook events define all 9 required registrations
  2. Hook event types cover all 5 distinct event types
  3. generate_hook_config produces correct structure for standard hooks
  4. generate_hook_config uses guard_command_fn for guard hooks
  5. generate_hook_config uses shell_command verbatim for Bash hook
  6. build_guard_command produces shell fast-path with correct structure
  7. is_des_hook_entry detects DES hooks in all formats (Python + shell)
  8. Bash guard shell command has correct structure and content
  9. Bash guard integration: allows non-execution-log commands
  10. Bash guard integration: blocks/allows based on des.cli presence
"""

from __future__ import annotations

import json
import subprocess

import pytest

from scripts.shared.hook_definitions import (
    _BASH_EXECUTION_LOG_GUARD,
    HOOK_EVENT_TYPES,
    HOOK_EVENTS,
    build_guard_command,
    generate_hook_config,
    is_des_hook_entry,
)


class TestHookEventDefinitions:
    """Verify the canonical hook event definitions are complete and correct."""

    def test_defines_all_nine_hook_registrations(self):
        """All 9 hook registrations are defined (4 PreToolUse + 5 others)."""
        assert len(HOOK_EVENTS) == 9

        # Verify exact event/matcher/action triples
        events_matchers = [(h.event, h.matcher, h.action) for h in HOOK_EVENTS]
        assert ("PreToolUse", "Agent", "pre-task") in events_matchers
        assert ("PreToolUse", "Write", "pre-write") in events_matchers
        assert ("PreToolUse", "Edit", "pre-edit") in events_matchers
        assert ("PreToolUse", "Bash", "pre-bash") in events_matchers
        assert ("PostToolUse", "Agent", "post-tool-use") in events_matchers
        assert ("SubagentStop", None, "subagent-stop") in events_matchers
        assert ("SubagentStop", None, "deliver-progress") in events_matchers
        assert ("SessionStart", "startup", "session-start") in events_matchers
        assert ("SubagentStart", None, "subagent-start") in events_matchers

    def test_hook_event_types_covers_five_distinct_types(self):
        """HOOK_EVENT_TYPES contains exactly the 5 Claude Code event types."""
        assert (
            frozenset(
                {
                    "PreToolUse",
                    "PostToolUse",
                    "SubagentStop",
                    "SessionStart",
                    "SubagentStart",
                }
            )
            == HOOK_EVENT_TYPES
        )

    def test_write_and_edit_hooks_are_guards(self):
        """Write and Edit hooks are guards; Bash is NOT (it uses shell_command)."""
        guards = [h for h in HOOK_EVENTS if h.is_guard]
        assert len(guards) == 2
        guard_matchers = {h.matcher for h in guards}
        assert guard_matchers == {"Write", "Edit"}

    def test_agent_matcher_not_task(self):
        """PreToolUse uses 'Agent' matcher, not legacy 'Task' (Claude Code v2.1.63+)."""
        pre_tool_agent = [
            h for h in HOOK_EVENTS if h.event == "PreToolUse" and h.matcher == "Agent"
        ]
        assert len(pre_tool_agent) == 1
        # Verify no 'Task' matcher anywhere
        task_matchers = [h for h in HOOK_EVENTS if h.matcher == "Task"]
        assert len(task_matchers) == 0


class TestGenerateHookConfig:
    """Verify hook config generation produces valid Claude Code hooks.json structure."""

    @staticmethod
    def _simple_command(action: str) -> str:
        return f"python3 -m des.hook {action}"

    def test_produces_entries_for_all_five_event_types(self):
        """Config has entries for all 5 event types."""
        config = generate_hook_config(self._simple_command)
        assert set(config.keys()) == HOOK_EVENT_TYPES

    def test_pretooluse_has_four_entries(self):
        """PreToolUse has 4 entries: Agent, Write, Edit, Bash."""
        config = generate_hook_config(self._simple_command)
        pre_tool_use = config["PreToolUse"]
        assert len(pre_tool_use) == 4
        matchers = [e.get("matcher") for e in pre_tool_use]
        assert matchers == ["Agent", "Write", "Edit", "Bash"]

    def test_each_entry_has_hooks_array_with_command(self):
        """Every entry has a hooks array with type=command and non-empty command."""
        config = generate_hook_config(self._simple_command)
        for event, entries in config.items():
            for entry in entries:
                hooks_list = entry["hooks"]
                assert len(hooks_list) == 1
                hook = hooks_list[0]
                assert hook["type"] == "command"
                assert len(hook["command"]) > 0

    def test_uses_guard_command_fn_for_guard_hooks(self):
        """Guard hooks (Write/Edit) use guard_command_fn when provided."""
        guard_calls = []

        def guard_fn(action: str) -> str:
            guard_calls.append(action)
            return f"GUARD:{action}"

        config = generate_hook_config(self._simple_command, guard_command_fn=guard_fn)

        # Write and Edit should use guard_fn
        write_entry = next(
            e for e in config["PreToolUse"] if e.get("matcher") == "Write"
        )
        edit_entry = next(e for e in config["PreToolUse"] if e.get("matcher") == "Edit")

        assert write_entry["hooks"][0]["command"] == "GUARD:pre-write"
        assert edit_entry["hooks"][0]["command"] == "GUARD:pre-edit"

        # Agent should NOT use guard_fn
        agent_entry = next(
            e for e in config["PreToolUse"] if e.get("matcher") == "Agent"
        )
        assert agent_entry["hooks"][0]["command"] == "python3 -m des.hook pre-task"

    def test_bash_hook_uses_shell_command_verbatim(self):
        """Bash entry command matches _BASH_EXECUTION_LOG_GUARD exactly."""
        config = generate_hook_config(self._simple_command)
        bash_entry = next(e for e in config["PreToolUse"] if e.get("matcher") == "Bash")
        assert bash_entry["hooks"][0]["command"] == _BASH_EXECUTION_LOG_GUARD

    def test_bash_hook_ignores_guard_command_fn(self):
        """Bash hook uses shell_command even when guard_command_fn is provided."""

        def guard_fn(action: str) -> str:
            return f"GUARD:{action}"

        config = generate_hook_config(self._simple_command, guard_command_fn=guard_fn)
        bash_entry = next(e for e in config["PreToolUse"] if e.get("matcher") == "Bash")
        assert bash_entry["hooks"][0]["command"] == _BASH_EXECUTION_LOG_GUARD

    def test_entries_without_matcher_omit_matcher_key(self):
        """SubagentStop and SubagentStart entries have no matcher key."""
        config = generate_hook_config(self._simple_command)
        for event in ("SubagentStop", "SubagentStart"):
            for entry in config[event]:
                assert "matcher" not in entry


class TestBuildGuardCommand:
    """Verify the shell fast-path guard command generation."""

    def test_guard_command_contains_fast_path_check(self):
        """Guard command checks for deliver-session.json before spawning Python."""
        cmd = build_guard_command("python3 -m des.hook pre-write")
        assert "deliver-session.json" in cmd
        assert "exit 0" in cmd

    def test_guard_command_checks_execution_log(self):
        """Guard command unconditionally invokes Python for execution-log.json targets."""
        cmd = build_guard_command("python3 -m des.hook pre-write")
        assert "execution-log" in cmd

    def test_guard_command_buffers_stdin(self):
        """Guard command captures stdin into INPUT variable."""
        cmd = build_guard_command("python3 -m des.hook pre-write")
        assert "INPUT=$(cat)" in cmd
        assert 'echo "$INPUT"' in cmd


class TestBashExecutionLogGuard:
    """Verify the Bash guard shell command structure and content."""

    def test_bash_hook_uses_shell_command_not_guard(self):
        """Bash hook has shell_command set, is_guard=False."""
        bash_hook = next(
            h for h in HOOK_EVENTS if h.event == "PreToolUse" and h.matcher == "Bash"
        )
        assert bash_hook.shell_command is not None
        assert bash_hook.is_guard is False

    def test_shell_command_contains_des_hook_marker(self):
        """Shell command starts with DES marker for is_des_hook_entry detection."""
        assert _BASH_EXECUTION_LOG_GUARD.startswith("# des-hook:")

    def test_shell_command_uses_ere_syntax(self):
        """Shell command uses grep -qE (ERE) for portability."""
        assert "grep -qE" in _BASH_EXECUTION_LOG_GUARD

    def test_shell_command_allows_des_cli_commands(self):
        """Shell command contains allow pattern for all 3 approved des.cli commands."""
        assert "des.cli.log_phase" in _BASH_EXECUTION_LOG_GUARD or (
            "log_phase" in _BASH_EXECUTION_LOG_GUARD
        )
        assert "des.cli.init_log" in _BASH_EXECUTION_LOG_GUARD or (
            "init_log" in _BASH_EXECUTION_LOG_GUARD
        )
        assert "des.cli.verify_deliver_integrity" in _BASH_EXECUTION_LOG_GUARD or (
            "verify_deliver_integrity" in _BASH_EXECUTION_LOG_GUARD
        )

    def test_shell_command_blocks_with_correct_json(self):
        """Shell command outputs valid JSON block response with decision=block."""
        assert '{"decision":"block"' in _BASH_EXECUTION_LOG_GUARD


class TestBashGuardIntegration:
    """End-to-end tests running the shell command via subprocess.

    These tests feed JSON through the shell command and verify exit codes,
    confirming the guard works at the shell level (not just string matching).
    """

    @staticmethod
    def _run_guard(input_json: dict) -> subprocess.CompletedProcess:
        """Run the Bash guard shell command with given JSON input."""
        return subprocess.run(
            ["bash", "-c", _BASH_EXECUTION_LOG_GUARD],
            input=json.dumps(input_json),
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_allow_non_execution_log_command(self):
        """Command not mentioning execution-log exits 0 (fast path)."""
        result = self._run_guard(
            {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}
        )
        assert result.returncode == 0

    def test_block_direct_modification(self):
        """Command mentioning execution-log without des.cli exits 2 (block)."""
        result = self._run_guard(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "python3 -c \"import json; f=open('execution-log.json')\""
                },
            }
        )
        assert result.returncode == 2
        output = json.loads(result.stdout)
        assert output["decision"] == "block"

    def test_allow_des_cli_log_phase(self):
        """Command with des.cli.log_phase exits 0 (approved CLI)."""
        result = self._run_guard(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "python3 -m des.cli.log_phase RED_UNIT execution-log.json"
                },
            }
        )
        assert result.returncode == 0

    def test_allow_des_cli_init_log(self):
        """Command with des.cli.init_log exits 0 (approved CLI)."""
        result = self._run_guard(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "python3 -m des.cli.init_log --project-dir . execution-log.json",
                },
            }
        )
        assert result.returncode == 0

    def test_allow_des_cli_verify_deliver_integrity(self):
        """Command with des.cli.verify_deliver_integrity exits 0 (approved CLI)."""
        result = self._run_guard(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "python3 -m des.cli.verify_deliver_integrity --project-dir .",
                },
            }
        )
        assert result.returncode == 0

    def test_allow_command_with_execution_log_in_description_only(self):
        """Guard does NOT block when 'execution-log' appears only in description, not command."""
        result = self._run_guard(
            {
                "tool_name": "Bash",
                "description": "Test: command without execution-log mention",
                "tool_input": {"command": "ls -la"},
            }
        )
        assert result.returncode == 0


class TestIsDESHookEntry:
    """Verify DES hook detection in both old and new formats."""

    @pytest.mark.parametrize(
        "entry,expected",
        [
            # New nested format -- DES hook (Python)
            (
                {
                    "matcher": "Agent",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "PYTHONPATH=... python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter pre-task",
                        }
                    ],
                },
                True,
            ),
            # Old flat format -- DES hook
            (
                {
                    "matcher": "Task",
                    "command": "python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter pre-task",
                },
                True,
            ),
            # Shell-based DES hook (Bash guard)
            (
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "# des-hook:pre-bash; INPUT=$(cat); ...",
                        }
                    ],
                },
                True,
            ),
            # Non-DES hook
            (
                {
                    "matcher": "Agent",
                    "hooks": [{"type": "command", "command": "some-other-hook"}],
                },
                False,
            ),
            # Empty entry
            ({}, False),
        ],
        ids=["nested-des", "flat-des", "shell-des", "non-des", "empty"],
    )
    def test_detects_des_hooks(self, entry: dict, expected: bool):
        assert is_des_hook_entry(entry) == expected
