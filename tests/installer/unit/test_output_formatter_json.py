"""Unit tests for ClaudeCodeFormatter JSON output.

Tests validate JSON error formatting for Claude Code context with required
fields: error_code, message, remediation, recoverable, timestamp.
"""

import json
from datetime import datetime

import pytest


class TestClaudeCodeJsonErrorStructure:
    """Verify JSON error output includes all required fields."""

    def test_format_json_error_structure(self):
        """JSON error output must include all required fields."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import ClaudeCodeFormatter

        formatter = ClaudeCodeFormatter()
        result = formatter.format_json_error(
            error_code=ENV_NO_VENV,
            message="No virtual environment detected",
            remediation="Run 'pipenv shell' to activate the virtual environment",
            recoverable=True,
        )

        # Result should be valid JSON
        parsed = json.loads(result)

        # Verify all required fields are present
        assert "error_code" in parsed
        assert "message" in parsed
        assert "remediation" in parsed
        assert "recoverable" in parsed
        assert "timestamp" in parsed

    def test_format_json_all_required_fields(self):
        """JSON output must have correct field types and values."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import ClaudeCodeFormatter

        formatter = ClaudeCodeFormatter()
        result = formatter.format_json_error(
            error_code=ENV_NO_VENV,
            message="No virtual environment detected",
            remediation="Run 'pipenv shell'",
            recoverable=True,
        )

        parsed = json.loads(result)

        # Verify field types
        assert isinstance(parsed["error_code"], str)
        assert isinstance(parsed["message"], str)
        assert isinstance(parsed["remediation"], str)
        assert isinstance(parsed["recoverable"], bool)
        assert isinstance(parsed["timestamp"], str)

        # Verify specific values
        assert parsed["error_code"] == ENV_NO_VENV
        assert parsed["message"] == "No virtual environment detected"
        assert parsed["remediation"] == "Run 'pipenv shell'"
        assert parsed["recoverable"] is True

    def test_format_json_timestamp_iso8601(self):
        """JSON timestamp must be in ISO 8601 format."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import ClaudeCodeFormatter

        formatter = ClaudeCodeFormatter()
        result = formatter.format_json_error(
            error_code=ENV_NO_VENV,
            message="Test message",
            remediation="Test remediation",
            recoverable=True,
        )

        parsed = json.loads(result)
        timestamp = parsed["timestamp"]

        # Verify ISO 8601 format by parsing it
        # ISO 8601 example: "2025-01-29T12:34:56.789012"
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            pytest.fail(f"Timestamp '{timestamp}' is not valid ISO 8601 format")


class TestClaudeCodeContextOutputsJsonError:
    """Verify Claude Code context outputs JSON for various error types."""

    def test_claude_code_context_outputs_json_error_for_missing_venv(self):
        """Claude Code context must output JSON error for missing venv."""
        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import ClaudeCodeFormatter

        formatter = ClaudeCodeFormatter()
        result = formatter.format_venv_error()

        # Result should be valid JSON
        parsed = json.loads(result)

        # Verify error code is correct
        assert parsed["error_code"] == ENV_NO_VENV
        assert "virtual environment" in parsed["message"].lower()
        assert "pipenv" in parsed["remediation"].lower()
        assert parsed["recoverable"] is True

    def test_claude_code_context_outputs_json_error_for_missing_pipenv(self):
        """Claude Code context must output JSON error for missing pipenv."""
        from scripts.install.error_codes import ENV_NO_PIPENV
        from scripts.install.output_formatter import ClaudeCodeFormatter

        formatter = ClaudeCodeFormatter()
        result = formatter.format_pipenv_error()

        # Result should be valid JSON
        parsed = json.loads(result)

        # Verify error code is correct
        assert parsed["error_code"] == ENV_NO_PIPENV
        assert "pipenv" in parsed["message"].lower()
        assert parsed["recoverable"] is True

    def test_claude_code_context_outputs_json_error_for_missing_dependency(self):
        """Claude Code context must output JSON error for missing dependency."""
        from scripts.install.error_codes import DEP_MISSING
        from scripts.install.output_formatter import ClaudeCodeFormatter

        formatter = ClaudeCodeFormatter()
        result = formatter.format_dependency_error(
            module_name="yaml",
            package_name="PyYAML",
        )

        # Result should be valid JSON
        parsed = json.loads(result)

        # Verify error code is correct
        assert parsed["error_code"] == DEP_MISSING
        assert "yaml" in parsed["message"].lower()
        assert "pyyaml" in parsed["remediation"].lower()
        assert parsed["recoverable"] is True

    def test_claude_code_json_includes_all_required_error_fields(self):
        """Every JSON error must include all five required fields."""
        from scripts.install.output_formatter import ClaudeCodeFormatter

        formatter = ClaudeCodeFormatter()

        # Test all error types
        errors = [
            formatter.format_venv_error(),
            formatter.format_pipenv_error(),
            formatter.format_dependency_error("yaml", "PyYAML"),
        ]

        required_fields = {
            "error_code",
            "message",
            "remediation",
            "recoverable",
            "timestamp",
        }

        for error_json in errors:
            parsed = json.loads(error_json)
            assert set(parsed.keys()) == required_fields, (
                f"Missing or extra fields in JSON: {set(parsed.keys())} vs {required_fields}"
            )


class TestFormatErrorModeSelection:
    """Verify format_error selects correct output mode based on context."""

    def test_format_error_selects_mode(self):
        """format_error should use context detector to select output mode."""
        from unittest.mock import patch

        from scripts.install.error_codes import ENV_NO_VENV
        from scripts.install.output_formatter import format_error

        # Test Claude Code context
        with patch(
            "scripts.install.output_formatter.is_claude_code_context", return_value=True
        ):
            result = format_error(
                error_code=ENV_NO_VENV,
                message="No virtual environment detected",
                remediation="Run 'pipenv shell'",
                recoverable=True,
            )

            # Should be valid JSON
            parsed = json.loads(result)
            assert "error_code" in parsed

        # Test Terminal context (must mock both is_claude_code_context AND is_ci_environment)
        with (
            patch(
                "scripts.install.output_formatter.is_claude_code_context",
                return_value=False,
            ),
            patch(
                "scripts.install.output_formatter.is_ci_environment",
                return_value=False,
            ),
        ):
            result = format_error(
                error_code=ENV_NO_VENV,
                message="No virtual environment detected",
                remediation="Run 'pipenv shell'",
                recoverable=True,
            )

            # Should be terminal format with [ERROR] prefix
            assert "[ERROR]" in result
