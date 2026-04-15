"""Tests for session start in the OpenCode DES shim.

The TS shim handles session.created events by invoking the Python adapter
with action 'session-start'. Per ADR-OC-004, the shim does NOT emit any
degraded-mode warning — full DES enforcement applies to both primary and
sub-agent tool calls via OpenCode's plugin hook pipeline.
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

# Path to the TS shim template (regression guard source of truth)
TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "nWave"
    / "templates"
    / "opencode-des-plugin.ts.template"
)


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


class TestNoDegradedModeWarning:
    """Regression guard: the TS shim must not carry legacy degraded-mode code.

    ADR-OC-004 superseded ADR-OC-002's "degraded mode" approach after an
    empirical probe proved sub-agent hooks fire on OpenCode. These tests
    assert the template contains no residual degraded-mode language so a
    future revert or copy-paste can't silently reintroduce it.
    """

    def test_template_has_no_degraded_mode_text(self):
        """Template must not contain the string 'degraded mode'."""
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "degraded mode" not in template.lower(), (
            "Template still contains 'degraded mode' — ADR-OC-004 removed it"
        )

    def test_template_has_no_obsolete_issue_reference(self):
        """Template must not reference obsolete OpenCode Issue #5894."""
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "5894" not in template, (
            "Template still references obsolete Issue #5894 — ADR-OC-004 removed it"
        )

    def test_template_has_no_mutable_degraded_flag(self):
        """Template must not carry the _degradedModeWarned module flag."""
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "_degradedModeWarned" not in template
        assert "emitDegradedModeWarning" not in template
