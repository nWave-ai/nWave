"""Step bodies for slice-02 (US-1) — event-keyed hooks schema.

Driving port: ``CodexDESPlugin.install(context)`` invoked against tmp-scoped
``CODEX_HOME``. Asserts at the driven-FS boundary (the installed
``hooks.json`` file). Port-to-port: if the install-time write site is
unwired, every scenario fails on the schema assertion — not on collection.
"""

from __future__ import annotations

import json
from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from scripts.install.plugins.codex_des_plugin import CodexDESPlugin


scenarios("../hooks-event-keyed.feature")


# --- Helpers ---------------------------------------------------------------


def _read_hooks_file(hooks_path: Path) -> object:
    return json.loads(hooks_path.read_text(encoding="utf-8"))


def _pretooluse_entries(parsed: dict) -> list[dict]:
    """Return the PreToolUse entry list from an event-keyed hooks doc."""
    assert isinstance(parsed, dict), (
        f"hooks.json root must be an object, got {type(parsed).__name__}"
    )
    hooks_obj = parsed.get("hooks")
    assert isinstance(hooks_obj, dict), (
        f"hooks.json must have a 'hooks' object property, got {type(hooks_obj).__name__}"
    )
    pretool = hooks_obj.get("PreToolUse")
    assert isinstance(pretool, list), (
        f"hooks.hooks.PreToolUse must be a list, got {type(pretool).__name__}"
    )
    return pretool


def _nwave_entries(pretool_entries: list[dict]) -> list[dict]:
    return [
        e
        for e in pretool_entries
        if any(
            "claude_code_hook_adapter" in h.get("command", "")
            for h in e.get("hooks", [])
        )
    ]


# --- Given -----------------------------------------------------------------


@given("a clean Codex environment with no prior nWave hooks")
def clean_codex_environment(codex_home: Path) -> None:
    # codex_home fixture already creates an empty .codex/ dir. Assert clean.
    assert codex_home.is_dir()
    assert not (codex_home / "hooks.json").exists()


@given("the nwave-ai installer has been run with --platform codex once")
def installer_run_once(install_context, patched_resolvers, hooks_path, state) -> None:
    plugin = CodexDESPlugin()
    result = plugin.install(install_context)
    assert result.success, f"first install must succeed; got {result.message}"
    assert hooks_path.exists()
    parsed = _read_hooks_file(hooks_path)
    state["first_pretooluse_count"] = len(_pretooluse_entries(parsed))
    state["first_pretooluse_serialized"] = json.dumps(
        _pretooluse_entries(parsed), sort_keys=True
    )


@given(
    "a legacy hooks file already exists as a top-level array at the Codex hooks path"
)
def legacy_array_hooks_file_exists(hooks_path: Path) -> None:
    legacy = [
        {
            "matcher": "^Task$|^Bash$",
            "hooks": [
                {
                    "type": "command",
                    "command": "echo legacy-array",
                    "timeout": 30,
                }
            ],
        }
    ]
    hooks_path.write_text(json.dumps(legacy, indent=2) + "\n", encoding="utf-8")


@given("a user-authored hooks file exists with a PostToolUse entry the user owns")
def user_hooks_file_with_post_tool_use(hooks_path: Path, state) -> None:
    user_doc = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "^Bash$",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "/usr/bin/echo user-post",
                            "timeout": 10,
                        }
                    ],
                }
            ]
        }
    }
    hooks_path.write_text(json.dumps(user_doc, indent=2) + "\n", encoding="utf-8")
    state["user_post_signature"] = json.dumps(
        user_doc["hooks"]["PostToolUse"], sort_keys=True
    )


@given("a hooks file already exists at the Codex hooks path containing malformed JSON")
def hooks_file_with_malformed_json(hooks_path: Path) -> None:
    hooks_path.write_text("{not valid json,,,", encoding="utf-8")


# --- When ------------------------------------------------------------------


@when("the nwave-ai installer is run with --platform codex")
def installer_run_codex(install_context, patched_resolvers, state) -> None:
    plugin = CodexDESPlugin()
    state["install_result"] = plugin.install(install_context)


@when("the nwave-ai installer is run with --platform codex a second time")
def installer_run_codex_second_time(install_context, patched_resolvers, state) -> None:
    plugin = CodexDESPlugin()
    state["install_result"] = plugin.install(install_context)


# --- Then ------------------------------------------------------------------


@then("the installed hooks file root is an object, not an array")
def hooks_root_is_object(hooks_path: Path) -> None:
    parsed = _read_hooks_file(hooks_path)
    assert isinstance(parsed, dict), (
        f"hooks.json root must be a JSON object, got {type(parsed).__name__}"
    )
    assert not isinstance(parsed, list)


@then('the object has a "hooks" property')
def object_has_hooks_property(hooks_path: Path) -> None:
    parsed = _read_hooks_file(hooks_path)
    assert isinstance(parsed, dict)
    assert "hooks" in parsed, "root object must have a 'hooks' property"
    assert isinstance(parsed["hooks"], dict)


@then('the "hooks.PreToolUse" property is a non-empty list')
def pretooluse_is_nonempty_list(hooks_path: Path) -> None:
    parsed = _read_hooks_file(hooks_path)
    entries = _pretooluse_entries(parsed)
    assert len(entries) >= 1, "hooks.hooks.PreToolUse must be non-empty"


@then("the PreToolUse entry exposes a non-empty command string")
def pretooluse_command_nonempty(hooks_path: Path) -> None:
    parsed = _read_hooks_file(hooks_path)
    entries = _pretooluse_entries(parsed)
    # Drill into the first matcher group's first command entry
    first_handler = entries[0]["hooks"][0]
    cmd = first_handler.get("command", "")
    assert isinstance(cmd, str) and cmd, (
        "PreToolUse handler must expose a non-empty command string"
    )


@then("the command string references the DES hook adapter")
def command_references_adapter(hooks_path: Path) -> None:
    parsed = _read_hooks_file(hooks_path)
    entries = _pretooluse_entries(parsed)
    cmd = entries[0]["hooks"][0]["command"]
    assert "claude_code_hook_adapter" in cmd, (
        f"command must reference the DES adapter; got {cmd!r}"
    )


@then("the count of nWave PreToolUse entries is identical to the first run")
def pretooluse_count_unchanged(hooks_path: Path, state) -> None:
    parsed = _read_hooks_file(hooks_path)
    entries = _pretooluse_entries(parsed)
    nwave = _nwave_entries(entries)
    assert len(nwave) == state["first_pretooluse_count"], (
        f"reinstall must preserve PreToolUse count; first={state['first_pretooluse_count']} "
        f"second={len(nwave)}"
    )


@then("no entry is duplicated")
def no_duplicate_entries(hooks_path: Path) -> None:
    parsed = _read_hooks_file(hooks_path)
    entries = _pretooluse_entries(parsed)
    nwave = _nwave_entries(entries)
    assert len(nwave) == 1, (
        f"reinstall must leave exactly one nWave PreToolUse entry, got {len(nwave)}"
    )


@then(
    "the installer either migrates the file to the event-keyed schema or refuses to overwrite"
)
def installer_migrates_or_refuses(hooks_path: Path, state) -> None:
    result = state["install_result"]
    # Either path is acceptable per the AC:
    #   (a) installer rebuilt the file in event-keyed shape and reported success
    #   (b) installer refused to overwrite and surfaced an error
    if result.success:
        parsed = _read_hooks_file(hooks_path)
        assert isinstance(parsed, dict), (
            "successful install must leave an event-keyed object, not an array"
        )
    else:
        assert result.errors, "refusal must surface an error message"


@then("the resulting file is never left as a top-level array")
def file_not_top_level_array(hooks_path: Path) -> None:
    if not hooks_path.exists():
        return
    parsed = _read_hooks_file(hooks_path)
    assert not isinstance(parsed, list), (
        f"hooks.json must not be a top-level array post-install; got {type(parsed).__name__}"
    )


@then("the user's PostToolUse entry remains intact")
def user_post_tool_use_preserved(hooks_path: Path, state) -> None:
    parsed = _read_hooks_file(hooks_path)
    assert isinstance(parsed, dict)
    post = parsed.get("hooks", {}).get("PostToolUse")
    assert post is not None, "PostToolUse key must remain"
    assert json.dumps(post, sort_keys=True) == state["user_post_signature"], (
        "user-owned PostToolUse entry must be preserved byte-for-byte"
    )


@then("a PreToolUse entry is added without disturbing other event keys")
def pretooluse_added_no_disturbance(hooks_path: Path) -> None:
    parsed = _read_hooks_file(hooks_path)
    pretool = _pretooluse_entries(parsed)
    nwave = _nwave_entries(pretool)
    assert len(nwave) >= 1, "PreToolUse entry must be added"
    # PostToolUse already asserted intact by the sibling step.


@then("the installer either rebuilds the file from scratch or reports a parse error")
def installer_rebuilds_or_errors(hooks_path: Path, state) -> None:
    result = state["install_result"]
    if result.success:
        parsed = _read_hooks_file(hooks_path)
        assert isinstance(parsed, dict), "rebuilt file must be a JSON object"
        entries = _pretooluse_entries(parsed)
        assert _nwave_entries(entries), "rebuilt file must contain the nWave entry"
    else:
        assert result.errors, "parse error must surface an error message"


@then("the installer does not leave the malformed bytes in place silently")
def installer_does_not_silently_keep_malformed(hooks_path: Path, state) -> None:
    result = state["install_result"]
    if result.success:
        # success ⇒ malformed must be gone (parse-able JSON now)
        parsed = _read_hooks_file(hooks_path)
        assert isinstance(parsed, dict)
    else:
        # failure path must surface an error rather than swallow silently
        assert result.errors, (
            "if installer cannot recover, it must surface an error not stay silent"
        )
