"""
E2E Acceptance Tests: Enforcement Policy False Positives (nWave-ai/nWave#33)

PERSONA: Orchestrator (Parent Agent)
STORY: As an orchestrator launching non-DES agents, I want prompts containing
       dates, line ranges, version ranges, and similar patterns to pass through,
       so that only genuine step execution work triggers DES enforcement.

BUSINESS VALUE:
- Eliminates false-positive blocks on legitimate non-DES agent invocations
- Preserves enforcement on real step-id references (true positives)
- Resolves intermittent, hard-to-diagnose agent launch failures

SCOPE: False positive regression tests for DesEnforcementPolicy STEP_ID_PATTERN.
       7 false-positive scenarios (currently RED) + 6 true-positive scenarios (GREEN).

TEST BOUNDARY: E2E via subprocess — invokes the real hook adapter CLI with JSON
on stdin, asserts exit code and stdout content. No mocks, no test doubles.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
HOOK_ADAPTER = (
    PROJECT_ROOT
    / "src"
    / "des"
    / "adapters"
    / "drivers"
    / "hooks"
    / "claude_code_hook_adapter.py"
)


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------


def _invoke_pre_tool_use_hook(prompt: str) -> subprocess.CompletedProcess:
    """Invoke the real PreToolUse hook via subprocess with the given prompt.

    Builds a Claude Code PreToolUse JSON payload and pipes it to the hook
    adapter. Returns the CompletedProcess with exit code, stdout, stderr.
    """
    payload = json.dumps(
        {
            "tool_name": "Agent",
            "tool_input": {
                "prompt": prompt,
            },
        }
    )

    env = os.environ.copy()
    src_path = str(PROJECT_ROOT / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    return subprocess.run(
        [sys.executable, str(HOOK_ADAPTER), "pre-tool-use"],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def _assert_allowed(result: subprocess.CompletedProcess) -> None:
    """Assert the hook allowed the prompt (exit 0, no block in stdout)."""
    assert result.returncode == 0, (
        f"Expected exit code 0 (allow), got {result.returncode}.\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    # stdout should either be empty or contain an allow decision — never a block
    if result.stdout.strip():
        response = json.loads(result.stdout.strip())
        assert response.get("decision") != "block", (
            f"Expected allow decision, got block: {response}"
        )


def _assert_blocked_with_reason(
    result: subprocess.CompletedProcess, expected_reason: str
) -> None:
    """Assert the hook blocked the prompt with the expected reason substring."""
    assert result.returncode == 2, (
        f"Expected exit code 2 (block), got {result.returncode}.\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert result.stdout.strip(), "Expected non-empty stdout with block response"
    response = json.loads(result.stdout.strip())
    assert response.get("decision") == "block", (
        f"Expected block decision, got: {response}"
    )
    assert expected_reason in response.get("reason", ""), (
        f"Expected '{expected_reason}' in reason, got: {response.get('reason')}"
    )


# =============================================================================
# FALSE POSITIVE SCENARIOS — must NOT trigger enforcement (currently RED)
# =============================================================================


class TestFalsePositives:
    """Prompts with non-step NN-NN patterns must pass through enforcement.

    These scenarios are currently RED because the regex matches any \\d{2}-\\d{2}
    pattern regardless of context. After the fix, they should be GREEN.
    """

    @pytest.mark.e2e
    def test_date_reference_not_blocked(self):
        """
        GIVEN an agent prompt mentioning "Fix the issue from 03-29"
        AND no DES markers are present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is allowed through
        AND no block reason is returned
        """
        result = _invoke_pre_tool_use_hook("Fix the issue from 03-29")
        _assert_allowed(result)

    @pytest.mark.e2e
    def test_numeric_build_range_not_blocked(self):
        """
        GIVEN an agent prompt mentioning "builds 10-12 failed in CI"
        AND no DES markers are present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is allowed through
        AND no block reason is returned
        """
        result = _invoke_pre_tool_use_hook("builds 10-12 failed in CI")
        _assert_allowed(result)

    @pytest.mark.e2e
    def test_line_range_not_blocked(self):
        """
        GIVEN an agent prompt mentioning "see lines 50-80"
        AND no DES markers are present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is allowed through
        AND no block reason is returned
        """
        result = _invoke_pre_tool_use_hook("see lines 50-80")
        _assert_allowed(result)

    @pytest.mark.e2e
    def test_port_range_not_blocked(self):
        """
        GIVEN an agent prompt mentioning "ports 80-82 are exposed"
        AND no DES markers are present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is allowed through
        AND no block reason is returned
        """
        result = _invoke_pre_tool_use_hook("ports 80-82 are exposed")
        _assert_allowed(result)

    @pytest.mark.e2e
    def test_page_reference_not_blocked(self):
        """
        GIVEN an agent prompt mentioning "pages 10-15"
        AND no DES markers are present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is allowed through
        AND no block reason is returned
        """
        result = _invoke_pre_tool_use_hook("pages 10-15")
        _assert_allowed(result)

    @pytest.mark.e2e
    def test_time_reference_not_blocked(self):
        """
        GIVEN an agent prompt mentioning "meeting at 09-30"
        AND no DES markers are present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is allowed through
        AND no block reason is returned
        """
        result = _invoke_pre_tool_use_hook("meeting at 09-30")
        _assert_allowed(result)

    @pytest.mark.e2e
    def test_exempt_marker_overrides_enforcement(self):
        """
        GIVEN an agent prompt mentioning "Review step 04-02 for completeness"
        AND the DES-ENFORCEMENT exempt marker is present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is allowed through
        AND no block reason is returned
        """
        prompt = "<!-- DES-ENFORCEMENT : exempt -->\nReview step 04-02 for completeness"
        result = _invoke_pre_tool_use_hook(prompt)
        _assert_allowed(result)


# =============================================================================
# TRUE POSITIVE SCENARIOS — MUST trigger enforcement (currently GREEN)
# =============================================================================


class TestTruePositives:
    """Prompts with real step-id references must be blocked without DES markers.

    These scenarios verify that enforcement correctly catches genuine step
    execution work that lacks DES monitoring markers.
    """

    @pytest.mark.e2e
    def test_bare_step_keyword_triggers_enforcement(self):
        """
        GIVEN an agent prompt mentioning "Execute step 04-02"
        AND no DES markers are present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is blocked
        AND the block reason contains "DES_MARKERS_MISSING"
        """
        result = _invoke_pre_tool_use_hook("Execute step 04-02")
        _assert_blocked_with_reason(result, "DES_MARKERS_MISSING")

    @pytest.mark.e2e
    def test_des_step_id_marker_triggers_enforcement(self):
        """
        GIVEN an agent prompt containing a DES-STEP-ID marker with value "04-02"
        AND no DES-VALIDATION marker is present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is blocked
        AND the block reason contains "DES_MARKERS_MISSING"
        """
        prompt = "<!-- DES-STEP-ID : 04-02 -->\nImplement the feature changes"
        result = _invoke_pre_tool_use_hook(prompt)
        _assert_blocked_with_reason(result, "DES_MARKERS_MISSING")

    @pytest.mark.e2e
    def test_step_reference_in_natural_language_triggers_enforcement(self):
        """
        GIVEN an agent prompt mentioning "step 11-01 of the roadmap"
        AND no DES markers are present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is blocked
        AND the block reason contains "DES_MARKERS_MISSING"
        """
        result = _invoke_pre_tool_use_hook("step 11-01 of the roadmap")
        _assert_blocked_with_reason(result, "DES_MARKERS_MISSING")

    @pytest.mark.e2e
    def test_step_id_in_html_comment_triggers_enforcement(self):
        """
        GIVEN an agent prompt mentioning "<!-- step 04-02 -->"
        AND no DES markers are present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is blocked
        AND the block reason contains "DES_MARKERS_MISSING"
        """
        result = _invoke_pre_tool_use_hook("<!-- step 04-02 -->")
        _assert_blocked_with_reason(result, "DES_MARKERS_MISSING")

    @pytest.mark.e2e
    def test_step_id_with_trailing_punctuation_triggers_enforcement(self):
        """
        GIVEN an agent prompt mentioning "Execute step 04-02."
        AND no DES markers are present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is blocked
        AND the block reason contains "DES_MARKERS_MISSING"
        """
        result = _invoke_pre_tool_use_hook("Execute step 04-02.")
        _assert_blocked_with_reason(result, "DES_MARKERS_MISSING")

    @pytest.mark.e2e
    def test_step_id_in_quotes_triggers_enforcement(self):
        """
        GIVEN an agent prompt mentioning '"step 04-02"'
        AND no DES markers are present
        WHEN the enforcement hook evaluates the prompt
        THEN the prompt is blocked
        AND the block reason contains "DES_MARKERS_MISSING"
        """
        result = _invoke_pre_tool_use_hook('"step 04-02"')
        _assert_blocked_with_reason(result, "DES_MARKERS_MISSING")
