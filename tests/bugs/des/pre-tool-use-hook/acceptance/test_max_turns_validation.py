"""
Bug Test: PreToolUse Hook MUST Validate max_turns in Tool Invocation

PROBLEM STATEMENT:
The PreToolUse hook currently validates the prompt content but does NOT validate
that the Task tool invocation includes the mandatory max_turns parameter.

REQUIREMENT (from CLAUDE.md):
> **CRITICAL**: Always include `max_turns` when invoking the Task tool.

CURRENT BEHAVIOR (BUG):
Task invocations without max_turns are allowed to proceed, violating the requirement.

EXPECTED BEHAVIOR:
PreToolUse hook should:
1. Extract max_turns from tool_input
2. BLOCK invocations if max_turns is missing
3. ALLOW invocations if max_turns is present with valid value

BUSINESS IMPACT:
- Without max_turns validation, agents can run indefinitely
- Excessive token consumption
- No control over execution duration
- Violation of explicit safety requirement

This test documents the expected behavior and will FAIL until the bug is fixed.
"""

import json

import pytest


class TestPreToolUseMaxTurnsValidation:
    """Acceptance tests for max_turns validation in PreToolUse hook."""

    def test_missing_max_turns_should_block_invocation(
        self, tmp_path, claude_code_hook_stdin
    ):
        """
        GIVEN Task tool invocation WITHOUT max_turns parameter
        WHEN PreToolUse hook processes the invocation
        THEN hook BLOCKS invocation with exit code 2
        AND error message indicates missing max_turns parameter
        AND provides guidance on adding max_turns

        Business Context:
        Developer calls Task(...) without max_turns parameter.
        Hook must catch this before invoking sub-agent to prevent
        unbounded execution.
        """
        # GIVEN: Tool invocation WITHOUT max_turns
        hook_input = {
            "tool_input": {
                "subagent_type": "Explore",
                "prompt": "Find all Python files",
                "description": "Quick exploration",
                # ❌ MISSING: max_turns parameter
            }
        }

        # WHEN: Hook processes invocation
        exit_code, stdout, stderr = claude_code_hook_stdin(
            "pre-task", json.dumps(hook_input)
        )

        # THEN: Invocation is BLOCKED
        assert exit_code == 2, (
            f"Hook should block with exit code 2 when max_turns missing. "
            f"Got: {exit_code}, stdout: {stdout}, stderr: {stderr}"
        )

        # THEN: Error message indicates missing max_turns
        output = json.loads(stdout)
        assert output.get("decision") == "block", "Decision should be 'block'"

        reason = output.get("reason", "").lower()
        assert "max_turns" in reason, (
            f"Error should mention max_turns. Got: {output.get('reason')}"
        )

        # THEN: Provides guidance
        assert any(
            keyword in reason
            for keyword in ["missing", "required", "must", "add", "include"]
        ), f"Error should indicate max_turns is required. Got: {reason}"

    def test_valid_max_turns_should_allow_invocation(
        self, tmp_path, claude_code_hook_stdin
    ):
        """
        GIVEN Task tool invocation WITH valid max_turns parameter
        WHEN PreToolUse hook processes the invocation
        THEN hook ALLOWS invocation with exit code 0
        AND no error message about max_turns

        Business Context:
        Developer correctly includes max_turns=30 in Task call.
        Hook should validate and allow execution to proceed.
        """
        # GIVEN: Tool invocation WITH valid max_turns
        hook_input = {
            "tool_input": {
                "subagent_type": "Explore",
                "prompt": "Find all Python files",
                "description": "Quick exploration",
                "max_turns": 30,  # ✅ PRESENT
            }
        }

        # WHEN: Hook processes invocation
        exit_code, stdout, stderr = claude_code_hook_stdin(
            "pre-task", json.dumps(hook_input)
        )

        # THEN: Invocation is ALLOWED
        assert exit_code == 0, (
            f"Hook should allow with exit code 0 when max_turns present. "
            f"Got: {exit_code}, stdout: {stdout}, stderr: {stderr}"
        )

        output = json.loads(stdout)
        assert output.get("decision") == "allow", "Decision should be 'allow'"

    def test_invalid_max_turns_values_should_block(
        self, tmp_path, claude_code_hook_stdin
    ):
        """
        GIVEN Task tool invocation WITH invalid max_turns values
        WHEN PreToolUse hook processes the invocation
        THEN hook BLOCKS invocation with exit code 2
        AND error message indicates invalid value

        Business Context:
        Developer sets max_turns to invalid value (negative, zero, or too high).
        Hook should catch this configuration error.
        """
        invalid_values = [
            (0, "zero"),
            (-1, "negative"),
            (-50, "negative"),
            (1000, "too high"),  # Excessive, indicates misconfiguration
        ]

        for invalid_value, description in invalid_values:
            # GIVEN: Tool invocation with invalid max_turns
            hook_input = {
                "tool_input": {
                    "subagent_type": "Explore",
                    "prompt": "Find files",
                    "max_turns": invalid_value,
                }
            }

            # WHEN: Hook processes invocation
            exit_code, stdout, _stderr = claude_code_hook_stdin(
                "pre-task", json.dumps(hook_input)
            )

            # THEN: Invocation is BLOCKED
            assert exit_code == 2, (
                f"Hook should block {description} max_turns ({invalid_value}). "
                f"Got: {exit_code}"
            )

            output = json.loads(stdout)
            assert output.get("decision") == "block"

            reason = output.get("reason", "").lower()
            assert any(
                keyword in reason
                for keyword in ["invalid", "positive", "range", "value"]
            ), f"Error should indicate invalid value for {description}. Got: {reason}"

    def test_max_turns_boundaries_are_enforced(self, tmp_path, claude_code_hook_stdin):
        """
        GIVEN Task tool invocation with max_turns at boundary values
        WHEN PreToolUse hook processes the invocation
        THEN appropriate boundaries are enforced

        Boundaries (from CLAUDE.md):
        - Minimum: 10 (too low indicates likely error)
        - Maximum: 100 (too high indicates likely error)
        - Recommended ranges:
          * Quick edit: 15
          * Background task: 25
          * Standard task: 30
          * Research: 35
          * Complex refactoring: 50
        """
        test_cases = [
            (1, "block", "too low"),
            (5, "block", "too low"),
            (10, "allow", "minimum acceptable"),  # Edge case: barely acceptable
            (15, "allow", "quick edit"),
            (30, "allow", "standard"),
            (50, "allow", "complex"),
            (100, "allow", "maximum acceptable"),  # Edge case: barely acceptable
            (101, "block", "too high"),
            (500, "block", "too high"),
        ]

        for value, expected_decision, description in test_cases:
            hook_input = {
                "tool_input": {
                    "subagent_type": "Explore",
                    "prompt": "Test",
                    "max_turns": value,
                }
            }

            _exit_code, stdout, _stderr = claude_code_hook_stdin(
                "pre-task", json.dumps(hook_input)
            )

            output = json.loads(stdout)
            actual_decision = output.get("decision")

            assert actual_decision == expected_decision, (
                f"max_turns={value} ({description}) should result in '{expected_decision}'. "
                f"Got: '{actual_decision}', reason: {output.get('reason')}"
            )

    def test_non_des_tasks_still_require_max_turns(
        self, tmp_path, claude_code_hook_stdin
    ):
        """
        GIVEN ad-hoc Task invocation (no DES marker) WITHOUT max_turns
        WHEN PreToolUse hook processes the invocation
        THEN hook should BLOCK (max_turns is universal requirement)

        Clarification:
        Even though ad-hoc tasks don't require DES template validation,
        they STILL require max_turns per CLAUDE.md requirement.

        max_turns is a TOOL-LEVEL requirement, not a DES-specific requirement.
        """
        # GIVEN: Ad-hoc task (no DES marker) without max_turns
        hook_input = {
            "tool_input": {
                "subagent_type": "Explore",
                "prompt": "Simple search - no DES markers",
                # No DES-VALIDATION marker
                # ❌ MISSING: max_turns
            }
        }

        # WHEN: Hook processes
        exit_code, stdout, _stderr = claude_code_hook_stdin(
            "pre-task", json.dumps(hook_input)
        )

        # THEN: Still BLOCKED due to missing max_turns
        assert exit_code == 2, (
            f"Even ad-hoc tasks require max_turns. Got exit code: {exit_code}"
        )

        output = json.loads(stdout)
        assert "max_turns" in output.get("reason", "").lower()


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def claude_code_hook_stdin(tmp_path):
    """
    Fixture to invoke Claude Code hook adapter directly (no subprocess).

    Returns callable that:
    1. Takes (command, stdin_data)
    2. Invokes hook adapter function directly with mocked stdin/stdout
    3. Returns (exit_code, stdout, stderr)

    Note: Direct function calls are ~10x faster than subprocess invocation.
    """
    from io import StringIO
    from unittest.mock import patch

    def invoke_hook(command: str, stdin_data: str) -> tuple[int, str, str]:
        """Invoke hook adapter function directly with mocked I/O."""
        from des.adapters.drivers.hooks.claude_code_hook_adapter import (
            handle_pre_tool_use,
        )

        # Mock stdin with the input data
        with patch("sys.stdin", StringIO(stdin_data)):
            # Mock stdout to capture output
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                # Call the handler directly
                exit_code = handle_pre_tool_use()
                stdout = mock_stdout.getvalue()

        # No stderr in direct calls (only in subprocess)
        stderr = ""

        return exit_code, stdout, stderr

    return invoke_hook
