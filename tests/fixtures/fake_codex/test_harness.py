"""Unit tests for the fake-codex harness contract.

Asserts the harness conforms to the documented Codex hooks contract per
``docs/feature/codex-empirical-e2e-support/spike-codex-hooks-schema.md``.
The harness is a TEST FIXTURE — these unit tests exist to guarantee it does
not drift away from the documented Codex behavior over time. If Codex
changes, this test file is the canonical place to update the contract.

Driving port: ``FakeCodexHarness.{load_hooks_document, fire_pre_tool_use}``.
Observable surface: returned ``HookInvocation`` list and raised
``FakeCodexSchemaError`` exceptions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from tests.fixtures.fake_codex import FakeCodexHarness, FakeCodexSchemaError


# --- Helpers ---------------------------------------------------------------


def _write_hooks(hooks_path: Path, doc: object) -> None:
    hooks_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _event_keyed_doc_with_echo(matcher: str = "^Bash$") -> dict:
    """Event-keyed hooks doc whose hook command is a portable shell echo."""
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": matcher,
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                # Echo the stdin envelope to stderr and exit 0.
                                # `cat 1>&2` keeps stdout empty so we can
                                # assert the stderr capture independently.
                                "cat 1>&2"
                            ),
                            "timeout": 10,
                        }
                    ],
                }
            ]
        }
    }


# --- Schema enforcement (Q1) ----------------------------------------------


def test_legacy_top_level_array_raises_schema_error(tmp_path: Path) -> None:
    """SPIKE Q1: top-level array (legacy pre-FM-1) must be rejected.

    Walking-skeleton scenario 3 depends on this contract.
    """
    hooks_path = tmp_path / "hooks.json"
    _write_hooks(hooks_path, [{"matcher": "^Bash$", "hooks": []}])
    harness = FakeCodexHarness(hooks_path)

    with pytest.raises(FakeCodexSchemaError, match="top-level array"):
        harness.load_hooks_document()


def test_missing_hooks_file_raises_schema_error(tmp_path: Path) -> None:
    harness = FakeCodexHarness(tmp_path / "missing.json")
    with pytest.raises(FakeCodexSchemaError, match="not found"):
        harness.load_hooks_document()


def test_malformed_json_raises_schema_error(tmp_path: Path) -> None:
    hooks_path = tmp_path / "hooks.json"
    hooks_path.write_text("{not valid json,,,", encoding="utf-8")
    harness = FakeCodexHarness(hooks_path)
    with pytest.raises(FakeCodexSchemaError, match="not valid JSON"):
        harness.load_hooks_document()


def test_missing_hooks_object_property_raises_schema_error(tmp_path: Path) -> None:
    hooks_path = tmp_path / "hooks.json"
    _write_hooks(hooks_path, {"not_hooks": {}})
    harness = FakeCodexHarness(hooks_path)
    with pytest.raises(FakeCodexSchemaError, match="'hooks' object property"):
        harness.load_hooks_document()


def test_valid_event_keyed_document_loads(tmp_path: Path) -> None:
    hooks_path = tmp_path / "hooks.json"
    _write_hooks(hooks_path, _event_keyed_doc_with_echo())
    harness = FakeCodexHarness(hooks_path)
    document = harness.load_hooks_document()
    assert isinstance(document, dict)
    assert "PreToolUse" in document["hooks"]


# --- Stdin envelope shape (Q4) --------------------------------------------


def test_fire_pre_tool_use_emits_documented_envelope_keys(tmp_path: Path) -> None:
    """SPIKE Q4: stdin envelope must contain all required keys.

    Drives the hook command to dump stdin back to stderr; we then parse it
    and assert every required field per the published JSON schema.
    """
    hooks_path = tmp_path / "hooks.json"
    _write_hooks(hooks_path, _event_keyed_doc_with_echo())

    harness = FakeCodexHarness(hooks_path)
    invocations = harness.fire_pre_tool_use(
        tool_name="Bash", tool_input={"command": "echo hello"}
    )

    assert len(invocations) == 1, f"expected 1 invocation, got {len(invocations)}"
    inv = invocations[0]
    assert inv.exit_code == 0, f"echo hook must exit 0; got {inv.exit_code}"

    # The hook dumped stdin to stderr — parse and check schema-required keys.
    parsed = json.loads(inv.stderr)
    required = {
        "cwd",
        "hook_event_name",
        "model",
        "permission_mode",
        "session_id",
        "tool_input",
        "tool_name",
        "tool_use_id",
        "transcript_path",
        "turn_id",
    }
    assert required.issubset(parsed.keys()), (
        f"envelope missing keys: {required - parsed.keys()}"
    )
    assert parsed["hook_event_name"] == "PreToolUse"
    assert parsed["tool_name"] == "Bash"
    assert parsed["tool_input"] == {"command": "echo hello"}
    assert parsed["transcript_path"] is None


# --- Matcher semantics (Q6) -----------------------------------------------


@pytest.mark.parametrize(
    "matcher,tool_name,should_fire",
    [
        ("^Bash$", "Bash", True),
        ("^Bash$", "BashOther", False),
        ("Bash", "Bash", True),
        ("^Bash$|^apply_patch$", "apply_patch", True),
        ("^Bash$|^apply_patch$", "Task", False),
        ("*", "anything", True),
        ("", "anything", True),
        ("mcp__filesystem__.*", "mcp__filesystem__read_file", True),
        ("mcp__filesystem__.*", "Bash", False),
    ],
)
def test_matcher_regex_semantics(
    tmp_path: Path, matcher: str, tool_name: str, should_fire: bool
) -> None:
    """SPIKE Q6: matcher is a regex string; '*' / '' match everything."""
    hooks_path = tmp_path / "hooks.json"
    _write_hooks(hooks_path, _event_keyed_doc_with_echo(matcher=matcher))

    harness = FakeCodexHarness(hooks_path)
    invocations = harness.fire_pre_tool_use(tool_name=tool_name)

    if should_fire:
        assert len(invocations) == 1, (
            f"matcher={matcher!r} should fire on tool={tool_name!r}"
        )
    else:
        assert invocations == [], (
            f"matcher={matcher!r} should NOT fire on tool={tool_name!r}"
        )


# --- Exit-code semantics (Q5) ---------------------------------------------


def test_exit_code_zero_propagates(tmp_path: Path) -> None:
    """Q5: exit 0 = allow."""
    hooks_path = tmp_path / "hooks.json"
    _write_hooks(
        hooks_path,
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "^Bash$",
                        "hooks": [{"type": "command", "command": "true", "timeout": 5}],
                    }
                ]
            }
        },
    )
    harness = FakeCodexHarness(hooks_path)
    invocations = harness.fire_pre_tool_use(tool_name="Bash")
    assert invocations[0].exit_code == 0


def test_exit_code_two_with_stderr_propagates(tmp_path: Path) -> None:
    """Q5: exit 2 = block + stderr blocking reason."""
    hooks_path = tmp_path / "hooks.json"
    _write_hooks(
        hooks_path,
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "^Bash$",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "echo blocked-reason 1>&2; exit 2",
                                "timeout": 5,
                            }
                        ],
                    }
                ]
            }
        },
    )
    harness = FakeCodexHarness(hooks_path)
    invocations = harness.fire_pre_tool_use(tool_name="Bash")
    assert invocations[0].exit_code == 2
    assert "blocked-reason" in invocations[0].stderr


# --- Argv contract (Q3) ---------------------------------------------------


def test_command_invoked_as_is_no_argv_injection(tmp_path: Path) -> None:
    """Q3: Codex does NOT append positional argv to the command string.

    We assert this by configuring a command that would print its own argv;
    nothing beyond what we wrote in hooks.json should appear.
    """
    hooks_path = tmp_path / "hooks.json"
    # `sh -c 'echo $#'` prints the argv count. Codex documents zero argv
    # injection, so we expect 0.
    _write_hooks(
        hooks_path,
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "^Bash$",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"{sys.executable} -c 'import sys; print(len(sys.argv)-1)'",
                                "timeout": 10,
                            }
                        ],
                    }
                ]
            }
        },
    )
    harness = FakeCodexHarness(hooks_path)
    invocations = harness.fire_pre_tool_use(tool_name="Bash")
    assert invocations[0].exit_code == 0
    assert invocations[0].stdout.strip() == "0", (
        f"expected no argv injection (count=0); got stdout={invocations[0].stdout!r}"
    )


# --- Environment propagation ---------------------------------------------


def test_env_dict_propagates_to_subprocess(tmp_path: Path) -> None:
    """Harness must pipe env vars (DES_AUDIT_LOG_DIR, PYTHONPATH) through.

    Acceptance tests rely on this to wire the real DES adapter's audit log
    output into a tmp_path-scoped directory.
    """
    hooks_path = tmp_path / "hooks.json"
    _write_hooks(
        hooks_path,
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "^Bash$",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "printenv FAKE_CODEX_PROBE",
                                "timeout": 5,
                            }
                        ],
                    }
                ]
            }
        },
    )
    harness = FakeCodexHarness(
        hooks_path, env={"PATH": "/usr/bin:/bin", "FAKE_CODEX_PROBE": "ping"}
    )
    invocations = harness.fire_pre_tool_use(tool_name="Bash")
    assert invocations[0].exit_code == 0
    assert invocations[0].stdout.strip() == "ping"
