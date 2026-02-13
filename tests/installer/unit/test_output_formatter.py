"""Unit tests for output_formatter module.

Tests validate terminal error formatting with [ERROR]/[FIX]/[THEN] structure,
ANSI color support, and human-readable error messages for various error types.
"""


class TestTerminalErrorStructure:
    """Verify terminal error format uses [ERROR]/[FIX]/[THEN] structure."""

    def test_terminal_error_format_uses_error_fix_then_structure(self):
        """Terminal error output must use [ERROR]/[FIX]/[THEN] prefix structure."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_terminal_error(
            error_code=ENV_NO_VENV,
            error_message="No virtual environment detected",
            fix_action="Create a virtual environment using pipenv",
            then_action="Run the installer again",
        )

        # Verify the structure contains all three prefixes
        assert "[ERROR]" in result
        assert "[FIX]" in result
        assert "[THEN]" in result

    def test_terminal_error_format_includes_error_message(self):
        """Terminal error output must include the error message after [ERROR]."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_terminal_error(
            error_code=ENV_NO_VENV,
            error_message="No virtual environment detected",
            fix_action="Create a virtual environment",
            then_action="Run the installer",
        )

        assert "No virtual environment detected" in result

    def test_terminal_error_format_includes_fix_action(self):
        """Terminal error output must include the fix action after [FIX]."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_terminal_error(
            error_code=ENV_NO_VENV,
            error_message="No virtual environment detected",
            fix_action="Create a virtual environment using pipenv",
            then_action="Run the installer",
        )

        assert "Create a virtual environment using pipenv" in result

    def test_terminal_error_format_includes_then_action(self):
        """Terminal error output must include the then action after [THEN]."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_terminal_error(
            error_code=ENV_NO_VENV,
            error_message="No virtual environment detected",
            fix_action="Create a virtual environment",
            then_action="Run the installer again",
        )

        assert "Run the installer again" in result


class TestTerminalErrorWithColors:
    """Verify terminal error format supports ANSI colors."""

    def test_format_terminal_error_with_colors_enabled(self):
        """Terminal error output includes ANSI color codes when colors enabled."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import TerminalFormatter

        # No patching needed - output_formatter now uses module-level ANSI constants
        formatter = TerminalFormatter(use_colors=True)
        result = formatter.format_terminal_error(
            error_code=ENV_NO_VENV,
            error_message="No virtual environment detected",
            fix_action="Create a virtual environment",
            then_action="Run the installer",
        )

        # Should contain ANSI escape codes
        assert "\033[" in result

    def test_format_terminal_error_without_colors(self):
        """Terminal error output excludes ANSI color codes when colors disabled."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter(use_colors=False)
        result = formatter.format_terminal_error(
            error_code=ENV_NO_VENV,
            error_message="No virtual environment detected",
            fix_action="Create a virtual environment",
            then_action="Run the installer",
        )

        # Should NOT contain ANSI escape codes
        assert "\033[" not in result


class TestMissingDependencyError:
    """Verify missing dependency error shows module name in terminal."""

    def test_missing_dependency_error_shows_module_name_in_terminal(self):
        """Missing dependency error must include the module name."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_dependency_error(
            module_name="yaml",
            package_name="PyYAML",
        )

        # Should include module name and suggest installation
        assert "yaml" in result
        assert "[ERROR]" in result
        assert "[FIX]" in result
        assert "[THEN]" in result

    def test_missing_dependency_error_includes_package_name(self):
        """Missing dependency error must include the pip package name."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_dependency_error(
            module_name="yaml",
            package_name="PyYAML",
        )

        assert "PyYAML" in result

    def test_missing_dependency_error_suggests_pip_install(self):
        """Missing dependency error should suggest pip install command."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_dependency_error(
            module_name="yaml",
            package_name="PyYAML",
        )

        # Should suggest installation command
        assert "pip install" in result.lower() or "pipenv install" in result.lower()


class TestPermissionError:
    """Verify permission error provides clear terminal guidance."""

    def test_permission_error_provides_clear_terminal_guidance(self):
        """Permission error must provide clear guidance for resolving access issues."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_permission_error(
            path="/home/user/.claude",
            operation="write",
        )

        assert "[ERROR]" in result
        assert "[FIX]" in result
        assert "[THEN]" in result
        assert "/home/user/.claude" in result

    def test_permission_error_includes_operation_type(self):
        """Permission error should mention the failed operation type."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_permission_error(
            path="/home/user/.claude",
            operation="write",
        )

        assert "write" in result.lower()

    def test_permission_error_suggests_chmod_or_ownership(self):
        """Permission error should suggest chmod or ownership changes."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_permission_error(
            path="/home/user/.claude",
            operation="write",
        )

        # Should suggest permission or ownership fix
        assert "chmod" in result.lower() or "permission" in result.lower()


class TestVenvError:
    """Verify virtual environment error formatting."""

    def test_format_venv_error_includes_error_fix_then_structure(self):
        """Venv error must use [ERROR]/[FIX]/[THEN] structure."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_venv_error()

        assert "[ERROR]" in result
        assert "[FIX]" in result
        assert "[THEN]" in result

    def test_format_venv_error_suggests_pipenv_shell(self):
        """Venv error should suggest pipenv shell command."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter()
        result = formatter.format_venv_error()

        assert "pipenv" in result.lower()


class TestPreflightErrorPanel:
    """Verify preflight error panel formatting."""

    def test_preflight_panel_empty_errors_returns_empty_string(self):
        """Empty errors list should return empty string."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter(use_colors=False)
        result = formatter.format_preflight_error_panel("Test Title", [])

        assert result == ""

    def test_preflight_panel_single_error_includes_structure(self):
        """Single error should include [ERROR]/[FIX]/[THEN] structure."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter(use_colors=False)
        errors = [
            {
                "error": "No virtual environment detected",
                "fix": "Run 'pipenv shell'",
                "then": "Re-run the installer",
            }
        ]
        result = formatter.format_preflight_error_panel(
            "Preflight Check Failed", errors
        )

        assert "[ERROR]" in result
        assert "[FIX]" in result
        assert "[THEN]" in result
        assert "No virtual environment detected" in result

    def test_preflight_panel_multiple_errors_separated(self):
        """Multiple errors should be visually separated."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter(use_colors=False)
        errors = [
            {"error": "Error 1", "fix": "Fix 1", "then": "Then 1"},
            {"error": "Error 2", "fix": "Fix 2", "then": "Then 2"},
        ]
        result = formatter.format_preflight_error_panel("Test Title", errors)

        assert "Error 1" in result
        assert "Error 2" in result
        assert "Fix 1" in result
        assert "Fix 2" in result

    def test_preflight_panel_includes_title(self):
        """Preflight panel should include the title."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter(use_colors=False)
        errors = [{"error": "Test error", "fix": "Test fix", "then": "Test then"}]
        result = formatter.format_preflight_error_panel(
            "Preflight Check Failed", errors
        )

        assert "Preflight Check Failed" in result

    def test_preflight_panel_handles_missing_keys(self):
        """Preflight panel should handle errors with missing keys gracefully."""
        from scripts.install.output_formatter import TerminalFormatter

        formatter = TerminalFormatter(use_colors=False)
        errors = [{"error": "Only error key"}]  # Missing fix and then
        result = formatter.format_preflight_error_panel("Test Title", errors)

        assert "Only error key" in result
        assert "[ERROR]" in result
        assert "[FIX]" in result  # Should still have prefix
        assert "[THEN]" in result  # Should still have prefix


class TestColorMethodRichMapping:
    """Verify _color method properly maps ANSI codes to Rich styles."""

    def test_color_method_returns_plain_text_when_colors_disabled(self):
        """_color should return plain text when use_colors=False."""
        from scripts.install.output_formatter import _ANSI_RED, TerminalFormatter

        formatter = TerminalFormatter(use_colors=False)
        result = formatter._color("[ERROR]", _ANSI_RED)

        assert result == "[ERROR]"
        assert "\033[" not in result

    def test_color_method_returns_ansi_when_rich_not_available(self):
        """_color should return ANSI codes when Rich not available or not TTY."""
        from scripts.install.output_formatter import _ANSI_RED, TerminalFormatter

        # use_colors=True but _use_rich will be False in non-TTY test environment
        formatter = TerminalFormatter(use_colors=True)

        # In test environment (non-TTY), _use_rich should be False
        if not formatter._use_rich:
            result = formatter._color("[ERROR]", _ANSI_RED)
            assert "\033[" in result or result == "[ERROR]"


class TestClaudeCodeFormatterUnchanged:
    """Verify ClaudeCodeFormatter remains unchanged (no Rich formatting)."""

    def test_claude_code_formatter_returns_valid_json(self):
        """ClaudeCodeFormatter must return valid JSON."""
        import json

        from scripts.install.output_formatter import ClaudeCodeFormatter

        formatter = ClaudeCodeFormatter()
        result = formatter.format_json_error(
            error_code="TEST_ERROR",
            message="Test message",
            remediation="Test remediation",
            recoverable=True,
        )

        # Should be valid JSON
        parsed = json.loads(result)
        assert "error_code" in parsed
        assert "message" in parsed
        assert "remediation" in parsed
        assert "recoverable" in parsed
        assert "timestamp" in parsed

    def test_claude_code_formatter_no_ansi_codes(self):
        """ClaudeCodeFormatter output must not contain ANSI codes."""
        from scripts.install.output_formatter import ClaudeCodeFormatter

        formatter = ClaudeCodeFormatter()
        result = formatter.format_json_error(
            error_code="TEST_ERROR",
            message="Test message",
            remediation="Test remediation",
            recoverable=True,
        )

        assert "\033[" not in result

    def test_claude_code_formatter_no_rich_markup(self):
        """ClaudeCodeFormatter output must not contain Rich markup."""
        from scripts.install.output_formatter import ClaudeCodeFormatter

        formatter = ClaudeCodeFormatter()
        result = formatter.format_json_error(
            error_code="TEST_ERROR",
            message="Test message",
            remediation="Test remediation",
            recoverable=True,
        )

        # Rich markup patterns like [bold red] should not appear
        assert "[bold" not in result
        assert "[/bold" not in result
