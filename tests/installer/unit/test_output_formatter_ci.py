"""Unit tests for CIFormatter CI output formatting.

Tests validate CI mode output formatting with:
- No ANSI color codes (breaks log parsing)
- Verbose output by default
- No interactive prompts
- Proper exit codes (0 for success, non-zero for failure)

CI environments require clean output for log parsing and proper exit codes
for pipeline status reporting.
"""

import json
from unittest.mock import patch


class TestCIFormatterDisablesANSIColors:
    """Verify CI mode disables ANSI color codes in output."""

    def test_ci_mode_disables_ansi_color_codes_in_output(self):
        """CI mode output must NOT contain ANSI escape sequences."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()
        result = formatter.format_ci_error(
            error_code=ENV_NO_VENV,
            message="No virtual environment detected",
            remediation="Run 'pipenv shell' to activate",
        )

        # CI output must never contain ANSI escape codes
        assert "\033[" not in result, "CI output must not contain ANSI escape codes"
        assert "\x1b[" not in result, "CI output must not contain ANSI escape codes"

    def test_ci_formatter_format_error_excludes_colors(self):
        """CIFormatter.format_ci_error must produce colorless output."""
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()
        result = formatter.format_ci_error(
            error_code="TEST_ERROR",
            message="Test error message",
            remediation="Fix the test",
        )

        # Verify no color escape sequences
        assert "\033[0m" not in result  # Reset code
        assert "\033[31m" not in result  # Red
        assert "\033[33m" not in result  # Yellow
        assert "\033[32m" not in result  # Green

    def test_ci_formatter_error_structure_readable_without_colors(self):
        """CI error output must be human-readable plain text."""
        from scripts.install.error_codes import DEP_MISSING
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()
        result = formatter.format_ci_error(
            error_code=DEP_MISSING,
            message="Required module 'yaml' is not installed",
            remediation="Run 'pipenv install PyYAML'",
        )

        # Should contain clear text markers for CI logs
        assert "ERROR" in result
        assert "yaml" in result
        assert "pipenv install" in result.lower() or "pip install" in result.lower()


class TestCIFormatterVerboseOutputByDefault:
    """Verify CI mode enables verbose output by default."""

    def test_ci_mode_enables_verbose_output_by_default(self):
        """CI mode must include verbose error details by default."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()
        result = formatter.format_ci_error(
            error_code=ENV_NO_VENV,
            message="No virtual environment detected",
            remediation="Run 'pipenv shell' to activate",
        )

        # Verbose output should include error code
        assert ENV_NO_VENV in result, (
            "CI output must include error code for verbose logs"
        )
        # Should include message
        assert "No virtual environment detected" in result
        # Should include remediation
        assert "pipenv shell" in result

    def test_ci_formatter_verbose_includes_timestamp(self):
        """CI verbose output should include timestamp for log correlation."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()
        result = formatter.format_ci_error(
            error_code=ENV_NO_VENV,
            message="Test message",
            remediation="Test fix",
        )

        # Should include timestamp for CI log correlation
        # Timestamp format: YYYY-MM-DD or ISO 8601
        import re

        # Check for date pattern in output
        has_timestamp = bool(re.search(r"\d{4}-\d{2}-\d{2}", result))
        assert has_timestamp, "CI output should include timestamp for log correlation"

    def test_ci_formatter_verbose_attribute_defaults_true(self):
        """CIFormatter.verbose should default to True."""
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()
        assert formatter.verbose is True, "CI formatter should be verbose by default"


class TestCIFormatterDisablesInteractivePrompts:
    """Verify CI mode disables interactive prompts."""

    def test_ci_mode_disables_interactive_prompts(self):
        """CI mode must set interactive to False."""
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()

        # CI formatter should explicitly disable interactive mode
        assert formatter.interactive is False, (
            "CI mode must disable interactive prompts"
        )

    def test_ci_formatter_is_not_interactive(self):
        """CIFormatter.is_interactive() must return False."""
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()

        # Explicit method check
        assert formatter.is_interactive() is False, (
            "CI formatter must never be interactive"
        )

    def test_ci_formatter_confirm_action_returns_default_without_prompt(self):
        """CI mode confirm_action must return default without prompting."""
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()

        # Should return default value without any prompt
        result = formatter.confirm_action(
            prompt="Continue with installation?",
            default=True,
        )
        assert result is True, "CI confirm_action should return default=True"

        result = formatter.confirm_action(
            prompt="Continue with installation?",
            default=False,
        )
        assert result is False, "CI confirm_action should return default=False"


class TestCIFormatterExitCodes:
    """Verify CI mode returns proper exit codes."""

    def test_ci_mode_returns_non_zero_exit_code_on_failure(self):
        """CI mode must return non-zero exit code for errors."""
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()
        exit_code = formatter.get_exit_code(success=False)

        assert exit_code != 0, "CI mode must return non-zero exit code on failure"
        assert exit_code == 1, "CI mode should return exit code 1 for general failure"

    def test_ci_mode_returns_zero_exit_code_on_success(self):
        """CI mode must return exit code 0 for success."""
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()
        exit_code = formatter.get_exit_code(success=True)

        assert exit_code == 0, "CI mode must return exit code 0 on success"

    def test_ci_formatter_error_includes_exit_code_in_output(self):
        """CI error output should include exit code for pipeline clarity."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import CIFormatter

        formatter = CIFormatter()
        result = formatter.format_ci_error(
            error_code=ENV_NO_VENV,
            message="No virtual environment detected",
            remediation="Run 'pipenv shell'",
        )

        # Should mention exit status for CI pipeline clarity
        assert (
            "exit" in result.lower()
            or "status" in result.lower()
            or "code" in result.lower()
        ), "CI error output should reference exit status/code for pipeline clarity"


class TestCIFormatterIntegrationWithContextDetector:
    """Verify CIFormatter integration with context_detector."""

    def test_format_error_uses_ci_formatter_in_ci_environment(self):
        """format_error should use CI formatting when in CI environment."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import format_error

        with (
            patch(
                "scripts.install.output_formatter.is_claude_code_context",
                return_value=False,
            ),
            patch(
                "scripts.install.output_formatter.is_ci_environment", return_value=True
            ),
        ):
            result = format_error(
                error_code=ENV_NO_VENV,
                message="No virtual environment detected",
                remediation="Run 'pipenv shell'",
                recoverable=True,
            )

            # Should be CI format (no ANSI colors)
            assert "\033[" not in result, "CI context should produce colorless output"
            # Should include error details
            assert "virtual environment" in result.lower()

    def test_format_error_priority_claude_code_over_ci(self):
        """Claude Code context should take priority over CI context."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import format_error

        with (
            patch(
                "scripts.install.output_formatter.is_claude_code_context",
                return_value=True,
            ),
            patch(
                "scripts.install.output_formatter.is_ci_environment", return_value=True
            ),
        ):
            result = format_error(
                error_code=ENV_NO_VENV,
                message="No virtual environment detected",
                remediation="Run 'pipenv shell'",
                recoverable=True,
            )

            # Claude Code format should take priority (JSON output)
            parsed = json.loads(result)
            assert "error_code" in parsed
