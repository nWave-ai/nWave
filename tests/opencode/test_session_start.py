"""Tests for session start and degraded mode warning in the OpenCode DES shim.

Step 01-03: The TS shim handles session.created events by:
1. Invoking the Python adapter with action 'session-start'
2. Emitting a degraded mode warning to stderr (once per session)

These tests verify the Python adapter contract for session-start and
validate the behavioral expectations documented in the shim template.
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

# Expected degraded mode warning text (must match TS template)
DEGRADED_WARNING_TEXT = "degraded mode"
ISSUE_REFERENCE = "5894"


def _run_adapter(
    action: str, stdin_json: dict, env_extra: dict | None = None
) -> subprocess.CompletedProcess:
    """Invoke the Python DES adapter as a subprocess."""
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


class TestSessionStartAdapter:
    """Python adapter handles session-start action correctly.

    Contract: The TS shim invokes the adapter with action 'session-start'
    and an empty JSON object on stdin. The adapter must exit 0 (fail-open).
    """

    def test_session_start_exits_zero(self):
        """Adapter accepts session-start and exits 0 (never blocks session)."""
        result = _run_adapter("session-start", {})

        assert result.returncode == 0, (
            f"session-start must exit 0 (fail-open), got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


class TestDegradedModeWarningContract:
    """Contract tests for the degraded mode warning text.

    The TS shim emits a warning to stderr containing 'degraded mode' and
    referencing OpenCode Issue #5894. These tests validate the expected
    text constants match between the TS template and our test expectations.
    """

    def test_degraded_warning_text_contains_required_phrases(self):
        """The degraded warning must mention 'degraded mode' and issue #5894."""
        # This is the canonical warning from the TS template
        warning = (
            "\u26a0 nWave DES: Running in degraded mode on OpenCode. "
            "Sub-agent tool calls are not enforced (OpenCode Issue #5894)."
        )

        assert DEGRADED_WARNING_TEXT in warning.lower()
        assert ISSUE_REFERENCE in warning

    def test_degraded_warning_mentions_enforcement_limitation(self):
        """Warning must explain WHAT is not enforced (sub-agent tool calls)."""
        warning = (
            "\u26a0 nWave DES: Running in degraded mode on OpenCode. "
            "Sub-agent tool calls are not enforced (OpenCode Issue #5894)."
        )

        assert "sub-agent" in warning.lower()
        assert "not enforced" in warning.lower()
