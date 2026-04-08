"""Hook Protocol Conformance — E2E acceptance tests.

Validates that DES hook handlers conform to the Claude Code hook protocol:
- Allow path: exit 0 with NO stdout (silent allow)
- Block path: exit 2 (PreToolUse, PreWrite) or exit 0 with JSON (SubagentStop)
- PostToolUse: always exit 0, always produces JSON on stdout

These tests invoke the real hook adapter via subprocess, matching how Claude
Code dispatches hooks in production. They capture stdout and verify the
protocol contract.

Issue: nWave-ai/nWave#34
RCA: docs/analysis/rca-pretooluse-allow-stdout-hook-error.md
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when


# Link to feature file
scenarios("hook-protocol-conformance.feature")


# ---------------------------------------------------------------------------
# Subprocess helper — invokes the hook adapter exactly as Claude Code would
# ---------------------------------------------------------------------------

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
SRC_PATH = str(Path(PROJECT_ROOT) / "src")


def _invoke_hook(command: str, stdin_json: str) -> subprocess.CompletedProcess:
    """Invoke the hook adapter as a subprocess with the given command and stdin.

    Mirrors how Claude Code dispatches hooks:
      PYTHONPATH=src python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter {command}

    Args:
        command: Hook command (pre-tool-use, subagent-stop, pre-write, post-tool-use).
        stdin_json: JSON string to pass on stdin.

    Returns:
        CompletedProcess with stdout, stderr, and returncode.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = SRC_PATH + os.pathsep + env.get("PYTHONPATH", "")

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "des.adapters.drivers.hooks.claude_code_hook_adapter",
            command,
        ],
        input=stdin_json,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Shared context fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def ctx() -> dict[str, Any]:
    """Shared mutable context for BDD scenario state."""
    return {}


# ---------------------------------------------------------------------------
# Given steps — PreToolUse
# ---------------------------------------------------------------------------


@given("a non-DES agent invocation with no step markers")
def given_non_des_agent_invocation(ctx: dict[str, Any]) -> None:
    """Prepare stdin for a regular Agent invocation (no step IDs, no DES markers)."""
    ctx["hook_command"] = "pre-tool-use"
    ctx["stdin"] = json.dumps(
        {
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Research the best practices for Python logging.",
                "subagent_type": "researcher",
            },
        }
    )


@given(
    parsers.parse(
        'an agent invocation referencing step "{step_id}" without DES markers'
    )
)
def given_agent_with_step_id_no_markers(ctx: dict[str, Any], step_id: str) -> None:
    """Prepare stdin for an Agent invocation that has a step-id but no DES markers.

    The enforcement policy blocks this because step execution requires DES monitoring.
    """
    ctx["hook_command"] = "pre-tool-use"
    ctx["stdin"] = json.dumps(
        {
            "tool_name": "Agent",
            "tool_input": {
                "prompt": f"Execute step {step_id}: implement the login feature.",
                "subagent_type": "software-crafter",
            },
        }
    )


@given("malformed JSON data on stdin for the PreToolUse hook")
def given_malformed_json(ctx: dict[str, Any]) -> None:
    """Prepare garbage data on stdin to verify graceful error handling."""
    ctx["hook_command"] = "pre-tool-use"
    ctx["stdin"] = "this is not valid JSON {{{!!!"


@given("completely empty stdin for the PreToolUse hook")
def given_empty_stdin(ctx: dict[str, Any]) -> None:
    """Prepare empty stdin to verify graceful handling of missing input."""
    ctx["hook_command"] = "pre-tool-use"
    ctx["stdin"] = ""


@given("a JSON payload without the required tool_name field for PreToolUse")
def given_missing_tool_name(ctx: dict[str, Any]) -> None:
    """Prepare valid JSON but missing tool_name to verify no crash."""
    ctx["hook_command"] = "pre-tool-use"
    ctx["stdin"] = json.dumps(
        {
            "tool_input": {
                "prompt": "Do something without specifying the tool name.",
            },
        }
    )


# ---------------------------------------------------------------------------
# Given steps — SubagentStop
# ---------------------------------------------------------------------------


@given("a completed non-DES agent with no step markers in its transcript")
def given_non_des_agent_completion(ctx: dict[str, Any], tmp_path: Path) -> None:
    """Prepare stdin for SubagentStop with a transcript that has no DES markers.

    Creates a minimal JSONL transcript file with no DES-VALIDATION markers,
    simulating a research agent completing its work.
    """
    transcript = tmp_path / "transcript.jsonl"
    transcript_entry = {
        "message": {
            "role": "user",
            "content": "Research Python logging best practices.",
        }
    }
    transcript.write_text(json.dumps(transcript_entry) + "\n")

    ctx["hook_command"] = "subagent-stop"
    ctx["stdin"] = json.dumps(
        {
            "agent_id": "agent-123",
            "agent_type": "researcher",
            "agent_transcript_path": str(transcript),
            "cwd": str(tmp_path),
        }
    )


@given("a completed DES agent whose step validation fails")
def given_des_agent_validation_failure(ctx: dict[str, Any], tmp_path: Path) -> None:
    """Prepare stdin for SubagentStop with DES markers but incomplete phases.

    Uses the direct DES protocol (executionLogPath, projectId, stepId) to
    trigger validation. The execution log has no phase events, so validation
    will fail (incomplete TDD phases).
    """
    # Create a minimal execution-log.json with no phase events for the step
    execution_log_path = (
        tmp_path
        / "docs"
        / "feature"
        / "test-project"
        / "deliver"
        / "execution-log.json"
    )
    execution_log_path.parent.mkdir(parents=True, exist_ok=True)
    execution_log = {
        "feature_id": "test-project",
        "schema_version": "3.0",
        "events": [],
    }
    execution_log_path.write_text(json.dumps(execution_log))

    ctx["hook_command"] = "subagent-stop"
    ctx["stdin"] = json.dumps(
        {
            "executionLogPath": str(execution_log_path),
            "projectId": "test-project",
            "stepId": "01-01",
            "stop_hook_active": False,
            "cwd": str(tmp_path),
        }
    )


# ---------------------------------------------------------------------------
# Given steps — PreWrite
# ---------------------------------------------------------------------------


@given(parsers.parse('a write to a non-protected file "{file_path}"'))
def given_write_to_non_protected_file(ctx: dict[str, Any], file_path: str) -> None:
    """Prepare stdin for a Write tool targeting a non-protected file."""
    ctx["hook_command"] = "pre-write"
    ctx["stdin"] = json.dumps(
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": file_path,
                "content": "Some documentation content.",
            },
        }
    )


@given(parsers.parse('a write to the execution log "{file_path}"'))
def given_write_to_execution_log(ctx: dict[str, Any], file_path: str) -> None:
    """Prepare stdin for a Write tool targeting the execution log.

    The execution log guard always blocks direct writes regardless of
    session state.
    """
    ctx["hook_command"] = "pre-write"
    ctx["stdin"] = json.dumps(
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": file_path,
                "content": '{"feature_id": "my-feature", "steps": {}}',
            },
        }
    )


# ---------------------------------------------------------------------------
# Given steps — PostToolUse
# ---------------------------------------------------------------------------


@given("a non-DES tool completion event")
def given_non_des_tool_completion(ctx: dict[str, Any]) -> None:
    """Prepare stdin for PostToolUse with a non-DES tool invocation.

    No DES-VALIDATION markers in the prompt means this is a passthrough:
    the handler should emit an empty JSON object.
    """
    ctx["hook_command"] = "post-tool-use"
    ctx["stdin"] = json.dumps(
        {
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Research Python logging best practices.",
                "subagent_type": "researcher",
            },
        }
    )


@given("a DES tool completion event with a prior failure in the audit log")
def given_des_tool_completion_with_failure(ctx: dict[str, Any], tmp_path: Path) -> None:
    """Prepare stdin for PostToolUse with DES markers.

    Note: The PostToolUseService reads the audit log for failure entries.
    In an E2E environment without a prior SubagentStop failure in the audit
    log, this will produce an empty response (no additionalContext). To
    verify the injection path we would need to seed the audit log with a
    HOOK_SUBAGENT_STOP_FAILED entry, which requires knowledge of the audit
    log path. This scenario tests the handler processes without crashing
    and produces valid output.
    """
    ctx["hook_command"] = "post-tool-use"
    ctx["stdin"] = json.dumps(
        {
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "<!-- DES-VALIDATION --> Execute step 01-01.",
                "subagent_type": "software-crafter",
            },
        }
    )


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when("the PreToolUse hook processes the invocation")
def when_pre_tool_use_processes(ctx: dict[str, Any]) -> None:
    """Invoke the PreToolUse handler via subprocess."""
    ctx["result"] = _invoke_hook(ctx["hook_command"], ctx["stdin"])


@when("the SubagentStop hook processes the completion")
def when_subagent_stop_processes(ctx: dict[str, Any]) -> None:
    """Invoke the SubagentStop handler via subprocess."""
    ctx["result"] = _invoke_hook(ctx["hook_command"], ctx["stdin"])


@when("the PreWrite hook processes the write request")
def when_pre_write_processes(ctx: dict[str, Any]) -> None:
    """Invoke the PreWrite handler via subprocess."""
    ctx["result"] = _invoke_hook(ctx["hook_command"], ctx["stdin"])


@when("the PostToolUse hook processes the completion")
def when_post_tool_use_processes(ctx: dict[str, Any]) -> None:
    """Invoke the PostToolUse handler via subprocess."""
    ctx["result"] = _invoke_hook(ctx["hook_command"], ctx["stdin"])


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then(parsers.parse("the hook exits with code {expected_code:d}"))
def then_exit_code_matches(ctx: dict[str, Any], expected_code: int) -> None:
    """Verify the hook process exited with the expected code."""
    result = ctx["result"]
    assert result.returncode == expected_code, (
        f"Expected exit code {expected_code}, got {result.returncode}.\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )


@then("the hook exits with a non-zero error code")
def then_exit_code_nonzero(ctx: dict[str, Any]) -> None:
    """Verify the hook exited with a non-zero code (error or block)."""
    result = ctx["result"]
    assert result.returncode != 0, (
        f"Expected non-zero exit code, got {result.returncode}.\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )


@then("stdout is completely empty")
def then_stdout_is_empty(ctx: dict[str, Any]) -> None:
    """Verify the hook produced absolutely no output on stdout.

    This is the critical protocol assertion: Claude Code interprets any
    stdout on exit 0 as a hook error. Silent exit is the only correct
    allow behavior.
    """
    result = ctx["result"]
    assert result.stdout == "", (
        f"Expected empty stdout on allow path, but got:\n"
        f"  stdout: {result.stdout!r}\n"
        f"This stdout causes Claude Code to display 'hook error' in the UI.\n"
        f"Fix: remove print() calls on allow paths in the handler."
    )


@then("stdout contains a block decision with a reason")
def then_stdout_contains_block_json(ctx: dict[str, Any]) -> None:
    """Verify stdout contains structured block JSON with decision and reason."""
    result = ctx["result"]
    assert result.stdout.strip(), (
        "Expected structured JSON on stdout for block path, but stdout was empty."
    )

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"stdout is not valid JSON: {e}\nRaw stdout: {result.stdout!r}")

    assert output.get("decision") == "block", (
        f"Expected decision 'block', got {output.get('decision')!r}.\n"
        f"Full output: {json.dumps(output, indent=2)}"
    )
    assert output.get("reason"), (
        f"Block decision must include a non-empty 'reason' field.\n"
        f"Full output: {json.dumps(output, indent=2)}"
    )


@then("stdout contains only an empty JSON object")
def then_stdout_contains_empty_json(ctx: dict[str, Any]) -> None:
    """Verify stdout contains exactly an empty JSON object {}.

    PostToolUse passthrough emits {} on stdout. This is different from the
    allow-path bug: PostToolUse ALWAYS writes to stdout (empty dict or
    additionalContext dict). Claude Code's PostToolUse protocol expects this.
    """
    result = ctx["result"]
    assert result.stdout.strip(), (
        "Expected empty JSON object on stdout, but stdout was completely empty."
    )

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"stdout is not valid JSON: {e}\nRaw stdout: {result.stdout!r}")

    assert output == {}, (
        f"Expected empty JSON object {{}}, got: {json.dumps(output, indent=2)}"
    )


@then("stdout contains additional context for the orchestrator")
def then_stdout_contains_additional_context(ctx: dict[str, Any]) -> None:
    """Verify stdout contains a valid JSON response from PostToolUse.

    PostToolUse either injects additionalContext (when a prior failure exists
    in the audit log) or returns an empty dict (when no failure found). Both
    are valid JSON responses. This step verifies the handler produces valid
    JSON output without crashing.
    """
    result = ctx["result"]
    assert result.stdout.strip(), (
        "Expected JSON on stdout from PostToolUse, but stdout was completely empty."
    )

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"stdout is not valid JSON: {e}\nRaw stdout: {result.stdout!r}")

    # PostToolUse always returns a dict — either {} or {"additionalContext": "..."}
    assert isinstance(output, dict), (
        f"Expected a JSON object, got {type(output).__name__}: {result.stdout!r}"
    )


@then("stdout contains an error response")
def then_stdout_contains_error_response(ctx: dict[str, Any]) -> None:
    """Verify stdout contains a structured error response.

    PreToolUse fail-closed: malformed JSON triggers exit 1 with an error
    response containing status and reason fields.
    """
    result = ctx["result"]
    assert result.stdout.strip(), (
        "Expected error response JSON on stdout, but stdout was empty."
    )

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(
            f"Error response stdout is not valid JSON: {e}\n"
            f"Raw stdout: {result.stdout!r}"
        )

    assert output.get("status") == "error", (
        f"Expected status 'error', got {output.get('status')!r}.\n"
        f"Full output: {json.dumps(output, indent=2)}"
    )
    assert output.get("reason"), (
        f"Error response must include a non-empty 'reason' field.\n"
        f"Full output: {json.dumps(output, indent=2)}"
    )


@then("stdout contains a permissive response")
def then_stdout_contains_permissive_response(ctx: dict[str, Any]) -> None:
    """Verify empty stdin produces silent exit 0 (allow).

    After fix for nWave-ai/nWave#34, all allow paths are silent —
    including the empty stdin case. No stdout on exit 0.
    """
    result = ctx["result"]
    assert result.stdout.strip() == "", (
        f"Empty stdin allow path should produce no stdout. Got: {result.stdout!r}"
    )


@then("the hook does not crash")
def then_hook_does_not_crash(ctx: dict[str, Any]) -> None:
    """Verify the hook process completed without a crash (no signal-based exit).

    A crash would manifest as a negative return code (signal) or an
    unhandled exception traceback. Exit codes 0, 1, and 2 are all valid
    protocol outcomes.
    """
    result = ctx["result"]
    assert result.returncode >= 0, (
        f"Hook crashed with signal {-result.returncode}.\nstderr: {result.stderr!r}"
    )
    # Verify no unhandled Python traceback leaked through
    assert "Traceback (most recent call last)" not in result.stderr, (
        f"Hook produced an unhandled exception traceback:\n{result.stderr}"
    )
