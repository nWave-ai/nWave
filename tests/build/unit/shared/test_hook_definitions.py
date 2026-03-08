"""Tests for the shared hook definitions module.

Driving port: hook_definitions module (pure functions).
Tests verify the canonical hook definitions produce correct configs
for both distribution paths (plugin and installer).

Test Budget: 7 distinct behaviors x 2 = 14 max unit tests.
Behaviors:
  1. Hook events define all 7 required registrations
  2. Hook event types cover all 5 distinct event types
  3. generate_hook_config produces correct structure for standard hooks
  4. generate_hook_config uses guard_command_fn for guard hooks
  5. build_guard_command produces shell fast-path with correct structure
  6. is_des_hook_entry detects DES hooks in both formats
  7. Plugin and installer paths produce equivalent event coverage (parity)
"""

from __future__ import annotations

import pytest

from scripts.shared.hook_definitions import (
    HOOK_EVENT_TYPES,
    HOOK_EVENTS,
    build_guard_command,
    generate_hook_config,
    is_des_hook_entry,
)


class TestHookEventDefinitions:
    """Verify the canonical hook event definitions are complete and correct."""

    def test_defines_all_seven_hook_registrations(self):
        """All 7 hook registrations are defined (3 PreToolUse + 4 others)."""
        assert len(HOOK_EVENTS) == 7

        # Verify exact event/matcher/action triples
        events_matchers = [(h.event, h.matcher, h.action) for h in HOOK_EVENTS]
        assert ("PreToolUse", "Agent", "pre-task") in events_matchers
        assert ("PreToolUse", "Write", "pre-write") in events_matchers
        assert ("PreToolUse", "Edit", "pre-edit") in events_matchers
        assert ("PostToolUse", "Agent", "post-tool-use") in events_matchers
        assert ("SubagentStop", None, "subagent-stop") in events_matchers
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
        """Write and Edit hooks are marked as guards for shell fast-path."""
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

    def test_pretooluse_has_three_entries(self):
        """PreToolUse has 3 entries: Agent, Write, Edit."""
        config = generate_hook_config(self._simple_command)
        pre_tool_use = config["PreToolUse"]
        assert len(pre_tool_use) == 3
        matchers = [e.get("matcher") for e in pre_tool_use]
        assert matchers == ["Agent", "Write", "Edit"]

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


class TestIsDESHookEntry:
    """Verify DES hook detection in both old and new formats."""

    @pytest.mark.parametrize(
        "entry,expected",
        [
            # New nested format -- DES hook
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
        ids=["nested-des", "flat-des", "non-des", "empty"],
    )
    def test_detects_des_hooks(self, entry: dict, expected: bool):
        assert is_des_hook_entry(entry) == expected
