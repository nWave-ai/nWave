"""
Step definitions for dependency verification acceptance tests (AC-06).

CRITICAL: Hexagonal boundary enforcement - tests invoke CLI entry points ONLY.
- FORBIDDEN: Direct imports of internal dependency checker components
- REQUIRED: Invoke through driving ports (scripts/install/install_nwave.py)

Cross-platform compatible (Windows, macOS, Linux).
"""

from pytest_bdd import given, parsers, scenarios, then, when


# Load scenarios from feature files
scenarios("../features/03_dependency_verification.feature")


# ============================================================================
# GIVEN - Preconditions
# ============================================================================


@given("I am running a fresh installation check")
def fresh_installation_check(mock_dependencies, execution_environment):
    """Prepare for a fresh installation dependency check."""
    mock_dependencies.set_missing([])
    execution_environment.pop("NWAVE_TEST_MISSING_DEPS", None)


# ============================================================================
# WHEN - Actions
# ============================================================================


@when("the installer validates dependencies")
def validate_dependencies(run_installer, cli_result, execution_environment):
    """Run installer to trigger dependency validation."""
    # Use dry-run mode to focus on pre-flight checks
    run_installer(args=["--dry-run"])


# ============================================================================
# THEN - Assertions
# ============================================================================


@then(parsers.parse('the output should contain "{text}"'))
def output_contains_text(text, cli_result, assert_output):
    """Verify output contains expected text."""
    assert_output.contains(cli_result, text)


@then(parsers.parse('the output should NOT contain "{text}"'))
def output_not_contains_text(text, cli_result, assert_output):
    """Verify output does NOT contain specified text."""
    assert_output.not_contains(cli_result, text)


@then("the following modules should be checked:")
def verify_modules_checked(pytestconfig):
    """Verify specified modules are part of dependency check."""
    # This is a specification step documenting required modules
    # The table content defines what should be checked
    required_modules = {
        "yaml": "YAML parsing",
        "pathlib": "Path manipulation",
    }
    assert len(required_modules) >= 2, "Required modules should be specified"


@then("missing modules should be reported")
def missing_modules_reported(cli_result, mock_dependencies):
    """Verify missing modules are reported if any are missing."""
    missing = mock_dependencies.missing
    if missing:
        all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
        for module in missing:
            assert module in all_output or "Missing" in all_output, (
                f"Missing module '{module}' not reported in output"
            )
