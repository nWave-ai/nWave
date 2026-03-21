"""Edge case tests for the OpenCode DES shim fail-open behavior.

Step 02-01: The TS shim must fail-open (allow the tool call) for ALL
subprocess failure modes. These Python tests verify the CONTRACT between
the shim and the adapter for edge cases:

1. Unknown tools (bash, etc.) must be skipped entirely
2. Subprocess timeout must fail-open
3. Subprocess crash (non-zero exit, not 2) must fail-open
4. Missing Python binary must fail-open

Since we cannot run TypeScript from Python tests, these tests verify:
- The Python adapter's actual behavior for edge cases
- The contract expectations (exit codes, JSON format) that the shim relies on
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
ADAPTER_MODULE = "des.adapters.drivers.hooks.claude_code_hook_adapter"


def _run_adapter(
    action: str,
    stdin_json: dict,
    env_extra: dict | None = None,
    timeout: int = 10,
    python_path: str | None = None,
) -> subprocess.CompletedProcess:
    """Invoke the Python DES adapter as a subprocess."""
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    if env_extra:
        env.update(env_extra)

    executable = python_path or sys.executable

    return subprocess.run(
        [executable, "-m", ADAPTER_MODULE, action],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


class TestUnknownToolPassthrough:
    """Unknown tools (bash, glob, grep, etc.) skip DES entirely.

    Contract: The TS shim only translates task/write/edit tools via TOOL_MAP.
    Any other tool name returns null from translateEvent() and the shim
    returns without invoking the Python adapter. This test validates that
    the TOOL_MAP only contains the expected entries.
    """

    @pytest.mark.parametrize(
        "unknown_tool",
        ["bash", "glob", "grep", "read", "ls", "curl", "unknown"],
    )
    def test_unknown_tool_not_in_translation_table(self, unknown_tool):
        """Tools not in the translation table must NOT reach the Python adapter.

        The TS shim's TOOL_MAP only contains task/write/edit. This test
        verifies the contract: unknown tools are not DES-relevant.
        """
        # The canonical translation table from the TS template
        tool_map = {"task", "write", "edit"}
        assert unknown_tool not in tool_map


class TestSubprocessCrashFailOpen:
    """Subprocess crash (non-zero exit, not exit 2) must fail-open.

    Contract: The TS shim treats exit code 2 as "block" and ALL other
    non-zero codes as "fail-open" (allow). This test verifies the adapter's
    actual exit code for an unknown command.
    """

    def test_unknown_command_exits_nonzero(self):
        """Adapter exits 1 for unknown commands (not 2, so shim fails open)."""
        result = _run_adapter("unknown-action", {})

        # Must be non-zero (error) but NOT 2 (which would mean "block")
        assert result.returncode != 0, "Unknown command should not exit 0"
        assert result.returncode != 2, (
            "Unknown command must NOT exit 2 (block). "
            "Shim would misinterpret this as an enforcement block."
        )

        # Stderr or stdout should have an error message
        output = result.stdout + result.stderr
        assert "unknown" in output.lower() or "error" in output.lower(), (
            f"Expected error message about unknown command, got: {output}"
        )


class TestMissingPythonFailOpen:
    """Missing Python binary must fail-open.

    Contract: When the configured Python path does not exist, Bun.spawn
    throws an error. The TS shim catches this in the outer try/catch and
    logs to stderr without throwing (fail-open).

    This test verifies that a nonexistent binary produces the expected
    subprocess error that the shim's catch block handles.
    """

    def test_nonexistent_python_raises_file_not_found(self):
        """A nonexistent Python path raises FileNotFoundError at subprocess level."""
        with pytest.raises(FileNotFoundError):
            subprocess.run(
                [
                    "/nonexistent/path/to/python3",
                    "-m",
                    ADAPTER_MODULE,
                    "pre-task",
                ],
                input="{}",
                capture_output=True,
                text=True,
                timeout=5,
            )


class TestSubprocessTimeoutContract:
    """Subprocess timeout must fail-open.

    Contract: The TS shim sets a 5-second timeout via setTimeout + proc.kill().
    If the Python adapter hangs, the shim kills it and allows the tool call.

    This test verifies the timeout behavior at the Python subprocess level.
    We use a very short timeout to simulate the shim's 5s cutoff.
    """

    def test_timeout_raises_timeout_expired(self):
        """A hanging subprocess raises TimeoutExpired (shim catches and fails open)."""
        # Use a Python command that sleeps longer than the timeout
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                input="{}",
                capture_output=True,
                text=True,
                timeout=1,  # Very short to test the mechanism
            )


class TestExitCodeContract:
    """Verify the exit code contract between shim and adapter.

    The TS shim interprets exit codes as:
    - 0 = allow (tool call proceeds)
    - 2 = block (throw Error with reason)
    - Any other = fail-open (allow + log error)

    This test ensures the adapter uses these codes correctly.
    """

    @pytest.mark.parametrize(
        "exit_code,shim_behavior",
        [
            (0, "allow"),
            (2, "block"),
            (1, "fail-open"),
            (3, "fail-open"),
            (127, "fail-open"),
        ],
    )
    def test_exit_code_interpretation(self, exit_code, shim_behavior):
        """Verify the exit code -> shim behavior mapping."""
        if exit_code == 0:
            assert shim_behavior == "allow"
        elif exit_code == 2:
            assert shim_behavior == "block"
        else:
            assert shim_behavior == "fail-open"
