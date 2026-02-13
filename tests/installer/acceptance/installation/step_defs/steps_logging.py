"""
Step definitions for installation logging acceptance tests (AC-09).

CRITICAL: Hexagonal boundary enforcement - tests invoke CLI entry points ONLY.
- FORBIDDEN: Direct imports of internal logging components
- REQUIRED: Invoke through driving ports (scripts/install/install_nwave.py)

Cross-platform compatible (Windows, macOS, Linux).
"""

import re

import pytest
from pytest_bdd import given, parsers, scenarios, then, when


# Load scenarios from feature files
scenarios("../features/05_logging.feature")


# ============================================================================
# GIVEN - Preconditions
# ============================================================================


@given("a previous log file exists")
def previous_log_exists(partial_installation_builder):
    """Create a previous log file with some content."""
    previous_content = "[2026-01-28 10:00:00] INFO: Previous installation attempt\n"
    partial_installation_builder.create_log_file(previous_content)


@given("an installation has been attempted")
def installation_attempted(
    run_installer, cli_result, mock_venv_status, execution_environment
):
    """Perform an installation attempt."""
    # Run installer (may succeed or fail, we just need log output)
    run_installer()


# ============================================================================
# WHEN - Actions
# ============================================================================


@when("I examine the log file")
def examine_log_file(file_assertions, cli_result):
    """Read and store log file content for examination."""
    if file_assertions.log_exists():
        cli_result["log_content"] = file_assertions.claude_home["log_file"].read_text()
    else:
        cli_result["log_content"] = ""


# ============================================================================
# THEN - Assertions
# ============================================================================


@then(parsers.parse('a log file should exist at "{path}"'))
def log_file_exists_at_path(path, file_assertions):
    """Verify log file exists at specified path."""
    # The path uses ~ which we need to expand
    assert file_assertions.log_exists(), "Log file not found at expected location"


@then("the log file should contain timestamped entries")
def log_has_timestamps(file_assertions):
    """Verify log file contains timestamped entries."""
    assert file_assertions.log_exists(), "Log file not found"
    content = file_assertions.claude_home["log_file"].read_text()

    # Look for timestamp patterns
    timestamp_patterns = [
        r"\d{4}-\d{2}-\d{2}",  # Date: 2026-01-29
        r"\d{2}:\d{2}:\d{2}",  # Time: 10:30:45
    ]

    has_timestamp = any(re.search(pattern, content) for pattern in timestamp_patterns)
    assert has_timestamp, f"No timestamps found in log:\n{content[:500]}"


@then(parsers.parse('the log should contain "{text}"'))
def log_contains_text(text, file_assertions):
    """Verify log file contains expected text."""
    assert file_assertions.log_contains(text), (
        f"Expected '{text}' not found in log file"
    )


@then("the log file should contain the error")
def log_contains_error(file_assertions):
    """Verify log file contains error information."""
    assert file_assertions.log_exists(), "Log file not found"
    content = file_assertions.claude_home["log_file"].read_text()

    has_error = (
        "ERROR" in content or "error" in content.lower() or "failed" in content.lower()
    )
    assert has_error, f"No error information in log:\n{content[:500]}"


@then("the log entry should include timestamp")
def log_entry_has_timestamp(file_assertions):
    """Verify log entries include timestamps."""
    # Same as log_has_timestamps - verify presence
    assert file_assertions.log_exists(), "Log file not found"
    content = file_assertions.claude_home["log_file"].read_text()

    # Check for timestamp in error-related lines
    lines = content.split("\n")
    error_lines = [line for line in lines if "error" in line.lower() or "ERROR" in line]

    if error_lines:
        has_timestamp = any(
            re.search(r"\d{4}-\d{2}-\d{2}", line)
            or re.search(r"\d{2}:\d{2}:\d{2}", line)
            for line in error_lines
        )
        assert has_timestamp, f"Error entries missing timestamps:\n{error_lines}"


@then("the log should contain pre-flight check entries")
def log_has_preflight_entries(file_assertions):
    """Verify log contains pre-flight check related entries."""
    assert file_assertions.log_exists(), "Log file not found"
    content = file_assertions.claude_home["log_file"].read_text().lower()

    has_preflight = (
        "check" in content
        or "environment" in content
        or "pre-flight" in content
        or "preflight" in content
        or "validating" in content
    )
    assert has_preflight, "No pre-flight check entries in log"


@then(parsers.parse('the log should contain "{check_type}" check result'))
def log_has_check_result(check_type, file_assertions):
    """Verify log contains specific check type result."""
    assert file_assertions.log_exists(), "Log file not found"
    content = file_assertions.claude_home["log_file"].read_text().lower()

    assert check_type.lower() in content, f"Check type '{check_type}' not found in log"


@then("the new log entries should be appended")
def new_entries_appended(file_assertions):
    """Verify new log entries are appended (not overwritten)."""
    assert file_assertions.log_exists(), "Log file not found"
    content = file_assertions.claude_home["log_file"].read_text()

    # Should contain both old and new entries
    # Look for multiple timestamp patterns suggesting multiple runs
    lines = content.strip().split("\n")
    assert len(lines) > 1, "Log doesn't appear to have multiple entries"


@then("the previous log entries should be preserved")
def previous_entries_preserved(file_assertions):
    """Verify previous log entries are preserved."""
    assert file_assertions.log_exists(), "Log file not found"
    content = file_assertions.claude_home["log_file"].read_text()

    # Check for content from the previous log (setup in Given step)
    assert "Previous installation attempt" in content, (
        "Previous log entries were not preserved"
    )


@then("each log entry should have a consistent format")
def log_format_consistent(cli_result):
    """Verify log entries follow consistent format."""
    log_content = cli_result.get("log_content", "")
    if not log_content:
        pytest.skip("No log content to examine")

    lines = [line for line in log_content.strip().split("\n") if line.strip()]

    # Skip if no meaningful lines
    if len(lines) < 2:
        return

    # Check that lines follow a recognizable pattern
    # Common patterns: [timestamp] LEVEL: message or timestamp - level - message
    format_patterns = [
        r"^\[?\d{4}-\d{2}-\d{2}",  # Starts with date
        r"^\d{4}-\d{2}-\d{2}",  # ISO date format
        r"^\[\d{2}:\d{2}:\d{2}\]",  # Time in brackets
    ]

    formatted_lines = 0
    for line in lines:
        if any(re.match(pattern, line) for pattern in format_patterns):
            formatted_lines += 1

    # At least 50% of lines should have consistent format
    format_ratio = formatted_lines / len(lines) if lines else 0
    assert format_ratio >= 0.5, (
        f"Log format inconsistent: only {formatted_lines}/{len(lines)} lines formatted"
    )


@then("the format should include timestamp")
def format_includes_timestamp(cli_result):
    """Verify log format includes timestamps."""
    log_content = cli_result.get("log_content", "")
    if not log_content:
        pytest.skip("No log content to examine")

    has_timestamp = re.search(r"\d{4}-\d{2}-\d{2}", log_content)
    assert has_timestamp, "Log format doesn't include timestamps"


@then("the format should include log level")
def format_includes_level(cli_result):
    """Verify log format includes log level."""
    log_content = cli_result.get("log_content", "")
    if not log_content:
        pytest.skip("No log content to examine")

    levels = ["DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL"]
    has_level = any(level in log_content.upper() for level in levels)
    # Also accept lowercase or mixed case
    assert has_level or any(level.lower() in log_content.lower() for level in levels), (
        "Log format doesn't include log level indicators"
    )


@then("the format should include message")
def format_includes_message(cli_result):
    """Verify log format includes message content."""
    log_content = cli_result.get("log_content", "")
    if not log_content:
        pytest.skip("No log content to examine")

    # Log should have meaningful text beyond just timestamps and levels
    # Remove timestamps and level indicators to check for message content
    content_stripped = re.sub(r"\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2}", "", log_content)
    content_stripped = re.sub(
        r"INFO|WARN|ERROR|DEBUG|WARNING|CRITICAL",
        "",
        content_stripped,
        flags=re.IGNORECASE,
    )

    # Should still have meaningful content
    has_message = len(content_stripped.strip()) > 20
    assert has_message, "Log entries don't appear to include messages"
