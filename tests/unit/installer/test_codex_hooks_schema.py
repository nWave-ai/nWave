"""Unit tests for Codex DES plugin event-keyed hooks-schema helpers.

Driving ports: the module-level helpers ``_build_hook_entry``,
``_read_hooks``, ``_remove_nwave_hooks`` — each is its own port (pure function
signature). Port-to-port at the function-signature scope.

Test budget: 3 distinct behaviors x 2 = 6 max.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.install.plugins.codex_des_plugin import (
    _build_hook_entry,
    _read_hooks,
    _remove_nwave_hooks,
)


# ---------------------------------------------------------------------------
# Behavior 1 — _build_hook_entry returns a Codex matcher-group dict
# ---------------------------------------------------------------------------


class TestBuildHookEntry:
    def test_matcher_group_shape(self):
        entry = _build_hook_entry("/usr/bin/python3", "/opt/des/lib")
        # Matcher-group shape per developers.openai.com/codex/hooks:
        # {"matcher": <regex>, "hooks": [{"type": "command", "command": ...}, ...]}
        assert isinstance(entry, dict)
        assert "matcher" in entry and isinstance(entry["matcher"], str)
        assert "hooks" in entry and isinstance(entry["hooks"], list)
        assert len(entry["hooks"]) >= 1
        handler = entry["hooks"][0]
        assert handler["type"] == "command"
        cmd = handler["command"]
        assert "/usr/bin/python3" in cmd
        assert "/opt/des/lib" in cmd
        assert "claude_code_hook_adapter" in cmd


# ---------------------------------------------------------------------------
# Behavior 2 — _read_hooks parses event-keyed object, defaults safely,
# migrates legacy top-level array
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,write,expected_pretool",
    [
        # missing file → empty event-keyed doc
        ("missing.json", None, []),
        # event-keyed object on disk → PreToolUse list preserved
        (
            "event_keyed.json",
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "^Bash$",
                            "hooks": [
                                {"type": "command", "command": "echo a", "timeout": 10}
                            ],
                        }
                    ]
                }
            },
            [
                {
                    "matcher": "^Bash$",
                    "hooks": [{"type": "command", "command": "echo a", "timeout": 10}],
                }
            ],
        ),
        # legacy top-level array → migrated into PreToolUse list (DDD-1 migration)
        (
            "legacy_array.json",
            [
                {
                    "matcher": "^Task$|^Bash$",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "echo legacy",
                            "timeout": 30,
                        }
                    ],
                }
            ],
            [
                {
                    "matcher": "^Task$|^Bash$",
                    "hooks": [
                        {"type": "command", "command": "echo legacy", "timeout": 30}
                    ],
                }
            ],
        ),
    ],
)
def test_read_hooks_event_keyed_universe(
    tmp_path: Path, filename: str, write, expected_pretool
):
    """_read_hooks returns an event-keyed doc; legacy array auto-migrates."""
    path = tmp_path / filename
    if write is not None:
        path.write_text(json.dumps(write), encoding="utf-8")

    doc = _read_hooks(path)

    assert isinstance(doc, dict), (
        f"_read_hooks must return an event-keyed dict, got {type(doc).__name__}"
    )
    assert isinstance(doc.get("hooks"), dict), "must have 'hooks' object property"
    assert doc["hooks"].get("PreToolUse", []) == expected_pretool


def test_read_hooks_malformed_json_returns_empty_event_keyed(tmp_path: Path):
    path = tmp_path / "malformed.json"
    path.write_text("{not valid,,,", encoding="utf-8")

    doc = _read_hooks(path)

    assert isinstance(doc, dict)
    assert doc == {"hooks": {}} or doc.get("hooks") == {}


# ---------------------------------------------------------------------------
# Behavior 3 — _remove_nwave_hooks filters nWave entries inside event-keyed doc
# ---------------------------------------------------------------------------


def test_remove_nwave_hooks_strips_only_nwave_pretooluse_entries():
    """_remove_nwave_hooks operates on event-keyed PreToolUse list.

    User-authored entries on PreToolUse remain; nWave entries (identified by
    claude_code_hook_adapter in command) are removed. Other event keys
    (PostToolUse) are untouched.
    """
    nwave_entry = {
        "matcher": "^Bash$",
        "hooks": [
            {
                "type": "command",
                "command": (
                    "PYTHONPATH=/x /usr/bin/python3 -m "
                    "des.adapters.drivers.hooks.claude_code_hook_adapter pre-tool-use"
                ),
                "timeout": 30,
            }
        ],
    }
    user_pretool_entry = {
        "matcher": "^Bash$",
        "hooks": [
            {"type": "command", "command": "/usr/bin/echo user-pre", "timeout": 10}
        ],
    }
    user_post_entry = {
        "matcher": "^Bash$",
        "hooks": [
            {"type": "command", "command": "/usr/bin/echo user-post", "timeout": 10}
        ],
    }
    doc = {
        "hooks": {
            "PreToolUse": [nwave_entry, user_pretool_entry],
            "PostToolUse": [user_post_entry],
        }
    }

    cleaned = _remove_nwave_hooks(doc)

    assert isinstance(cleaned, dict)
    assert cleaned["hooks"]["PreToolUse"] == [user_pretool_entry], (
        "user PreToolUse entry must survive; nWave entry must be removed"
    )
    assert cleaned["hooks"]["PostToolUse"] == [user_post_entry], (
        "PostToolUse event must be untouched"
    )


def test_remove_nwave_hooks_handles_empty_or_missing_pretooluse():
    """Empty or missing PreToolUse must not raise."""
    assert _remove_nwave_hooks({"hooks": {}}) == {"hooks": {}}
    assert _remove_nwave_hooks({"hooks": {"PreToolUse": []}}) == {
        "hooks": {"PreToolUse": []}
    }
