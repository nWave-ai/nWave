"""Walking skeleton integration tests for the OpenCode DES shim.

These tests invoke the Python DES adapter via subprocess with CC-format JSON,
exactly as the TypeScript shim would. They verify the end-to-end contract:
the adapter accepts CC-format JSON on stdin and returns allow/block decisions.

WS-1: Valid DES markers -> exit 0 (allow)
WS-2: Missing DES markers -> exit 2 (block)
"""

import json
import os
import subprocess
import sys
from pathlib import Path


# Project root for PYTHONPATH
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)

# The adapter module invoked by the TS shim
ADAPTER_MODULE = "des.adapters.drivers.hooks.claude_code_hook_adapter"


def _run_adapter(
    action: str, stdin_json: dict, env_extra: dict | None = None
) -> subprocess.CompletedProcess:
    """Invoke the Python DES adapter as a subprocess, same as TS shim would.

    Args:
        action: CLI action (pre-task, pre-write, pre-edit, session-start)
        stdin_json: JSON dict piped to stdin
        env_extra: Additional environment variables

    Returns:
        CompletedProcess with stdout, stderr, returncode
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    if env_extra:
        env.update(env_extra)

    return subprocess.run(
        [sys.executable, "-m", ADAPTER_MODULE, action],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


class TestWalkingSkeletonValidDispatch:
    """WS-1: Valid DES markers -> adapter allows (exit 0).

    Scenario 1 from acceptance-scenarios.md:
    Given the Python adapter receives CC-format JSON with valid DES markers,
    When invoked with action 'pre-task',
    Then exit code is 0 and decision is 'allow'.
    """

    def test_valid_des_markers_allowed(self, tmp_path):
        """Adapter allows dispatch when DES markers are present."""
        # Create a minimal execution log so the adapter finds a valid project
        des_dir = tmp_path / ".des"
        des_dir.mkdir()
        exec_log = des_dir / "execution-log.json"
        exec_log.write_text(
            json.dumps(
                {
                    "schema_version": "4.0",
                    "feature_id": "my-feature",
                    "steps": [
                        {
                            "step_id": "step-01",
                            "name": "Walking skeleton",
                            "status": "in_progress",
                            "phases": [],
                        }
                    ],
                }
            )
        )

        cc_json = {
            "tool_name": "Agent",
            "tool_input": {
                "prompt": (
                    "DES-STEP-ID: step-01\n"
                    "DES-PROJECT-ID: my-feature\n"
                    "DES-VALIDATION: true\n"
                    "Implement the user repository"
                ),
                "subagent_type": "nw-software-crafter",
            },
        }

        result = _run_adapter(
            "pre-task",
            cc_json,
            env_extra={"DES_PROJECT_DIR": str(tmp_path)},
        )

        # The adapter should allow (exit 0) with valid markers
        assert result.returncode == 0, (
            f"Expected exit 0 (allow), got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        response = json.loads(result.stdout)
        assert response.get("decision") == "allow"


class TestWalkingSkeletonMissingMarkers:
    """WS-2: Missing DES markers -> adapter blocks (exit 2).

    Scenario 2 from acceptance-scenarios.md:
    Given the Python adapter receives CC-format JSON referencing a step-id
    but WITHOUT DES validation markers,
    When invoked with action 'pre-task',
    Then exit code is 2 and decision is 'block'.

    The DesEnforcementPolicy blocks prompts that contain a step-id pattern
    (XX-XX) but lack the DES-VALIDATION marker. This is the bypass prevention
    rule: if you reference a step, you must have DES markers.
    """

    def test_missing_markers_blocked(self, tmp_path):
        """Adapter blocks dispatch when step-id referenced without DES markers."""
        # Prompt references step 01-01 but has NO DES markers
        cc_json = {
            "tool_name": "Agent",
            "tool_input": {
                "prompt": ("Execute step 01-01: implement the user repository"),
                "subagent_type": "nw-software-crafter",
            },
        }

        result = _run_adapter(
            "pre-task",
            cc_json,
            env_extra={"DES_PROJECT_DIR": str(tmp_path)},
        )

        # The adapter should block (exit 2) -- step-id without DES markers
        assert result.returncode == 2, (
            f"Expected exit 2 (block), got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        response = json.loads(result.stdout)
        assert response.get("decision") == "block"
        # The block reason should mention missing DES markers
        reason = response.get("reason", "")
        assert "DES_MARKERS_MISSING" in reason, (
            f"Block reason should mention DES_MARKERS_MISSING, got: {reason}"
        )
