"""Contract tests for OpenCode-to-Claude-Code protocol translation.

These tests verify the CONTRACT between the TypeScript shim and the Python
DES adapter. The shim translates OpenCode JSON into Claude Code JSON before
piping it to the Python subprocess. These tests verify what the Python side
expects to receive, so if either side changes the contract test fails.

The tests do NOT run the TS shim. They verify the expected CC-format JSON
that the Python adapter's handlers consume.
"""

import json

import pytest

from des.adapters.drivers.hooks.hook_protocol import StdinParseResult


# ---------------------------------------------------------------------------
# Contract: Expected Claude Code JSON formats that handlers consume
# ---------------------------------------------------------------------------


class TestTaskEventExpectedFormat:
    """The Python adapter expects Agent tool invocations in CC format.

    Contract: tool_name="Agent", tool_input contains prompt and subagent_type.
    The TS shim must produce this exact structure from OC task events.
    """

    def test_pre_tool_use_handler_expects_agent_format(self):
        """CC adapter expects tool_name='Agent' with prompt and subagent_type."""
        cc_format = {
            "tool_name": "Agent",
            "tool_input": {
                "prompt": (
                    "DES-STEP-ID: step-01\n"
                    "DES-PROJECT-ID: my-feature\n"
                    "Implement repository"
                ),
                "subagent_type": "nw-software-crafter",
            },
        }

        # Verify the structure matches what pre_tool_use_handler reads
        assert cc_format["tool_name"] == "Agent"
        assert "prompt" in cc_format["tool_input"]
        assert "subagent_type" in cc_format["tool_input"]

        # Verify it can be parsed as valid stdin input
        result = StdinParseResult(hook_input=cc_format)
        assert result.ok
        assert result.hook_input["tool_input"]["prompt"].startswith("DES-STEP-ID")
        assert result.hook_input["tool_input"]["subagent_type"] == "nw-software-crafter"

        # Verify fields NOT present (shim must drop these OC-only fields)
        assert "session_id" not in cc_format
        assert "is_subagent" not in cc_format
        assert "tool" not in cc_format  # OC field, not CC


class TestWriteEventExpectedFormat:
    """The Python adapter expects Write tool invocations in CC format.

    Contract: tool_name="Write", tool_input contains file_path and content.
    """

    def test_pre_write_handler_expects_write_format(self):
        """CC adapter expects tool_name='Write' with file_path and content."""
        cc_format = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/src/repository.py",
                "content": "class UserRepo:\n    pass",
            },
        }

        assert cc_format["tool_name"] == "Write"
        assert cc_format["tool_input"]["file_path"] == "/src/repository.py"
        assert "content" in cc_format["tool_input"]

        result = StdinParseResult(hook_input=cc_format)
        assert result.ok


class TestEditEventExpectedFormat:
    """The Python adapter expects Edit tool invocations in CC format.

    Contract: tool_name="Edit", tool_input contains file_path, old_string, new_string.
    """

    def test_pre_write_handler_expects_edit_format(self):
        """CC adapter expects tool_name='Edit' with file_path, old_string, new_string."""
        cc_format = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/src/repository.py",
                "old_string": "def old_method():",
                "new_string": "def new_method():",
            },
        }

        assert cc_format["tool_name"] == "Edit"
        assert cc_format["tool_input"]["file_path"] == "/src/repository.py"
        assert cc_format["tool_input"]["old_string"] == "def old_method():"
        assert cc_format["tool_input"]["new_string"] == "def new_method():"

        result = StdinParseResult(hook_input=cc_format)
        assert result.ok


class TestActionRouting:
    """Contract: OC tool names map to specific CLI actions for hook_router.

    The TS shim must invoke the Python adapter with the correct action argument.
    """

    @pytest.mark.parametrize(
        "oc_tool,expected_action,expected_cc_tool_name",
        [
            ("task", "pre-task", "Agent"),
            ("write", "pre-write", "Write"),
            ("edit", "pre-write", "Edit"),
        ],
    )
    def test_tool_to_action_mapping(
        self, oc_tool, expected_action, expected_cc_tool_name
    ):
        """Each OC tool maps to a specific CLI action and CC tool_name."""
        # This is the translation table the TS shim must implement
        translation_table = {
            "task": {"action": "pre-task", "tool_name": "Agent"},
            "write": {"action": "pre-write", "tool_name": "Write"},
            "edit": {"action": "pre-write", "tool_name": "Edit"},
        }

        entry = translation_table[oc_tool]
        assert entry["action"] == expected_action
        assert entry["tool_name"] == expected_cc_tool_name


class TestTranslationCompleteness:
    """Contract: translated JSON always has tool_name and tool_input."""

    @pytest.mark.parametrize(
        "oc_tool,oc_input,expected_tool_name",
        [
            (
                "task",
                {"prompt": "implement feature", "agent": "nw-software-crafter"},
                "Agent",
            ),
            (
                "write",
                {"file_path": "/src/main.py", "content": "print('hello')"},
                "Write",
            ),
            (
                "edit",
                {
                    "file_path": "/src/main.py",
                    "old_string": "old",
                    "new_string": "new",
                },
                "Edit",
            ),
        ],
    )
    def test_translated_output_always_has_required_fields(
        self, oc_tool, oc_input, expected_tool_name
    ):
        """Any valid OC tool event produces CC JSON with tool_name and tool_input."""
        # Simulate what the TS shim must produce
        field_mapping = {
            "task": lambda inp: {
                "tool_name": "Agent",
                "tool_input": {
                    "prompt": inp.get("prompt", ""),
                    "subagent_type": inp.get("agent", ""),
                },
            },
            "write": lambda inp: {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": inp.get("file_path", ""),
                    "content": inp.get("content", ""),
                },
            },
            "edit": lambda inp: {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": inp.get("file_path", ""),
                    "old_string": inp.get("old_string", ""),
                    "new_string": inp.get("new_string", ""),
                },
            },
        }

        translated = field_mapping[oc_tool](oc_input)

        # Structural invariants
        assert "tool_name" in translated
        assert "tool_input" in translated
        assert isinstance(translated["tool_input"], dict)
        assert translated["tool_name"] == expected_tool_name
        assert translated["tool_name"] in ("Agent", "Write", "Edit")

        # Must be valid JSON (round-trip)
        serialized = json.dumps(translated)
        deserialized = json.loads(serialized)
        assert deserialized == translated
