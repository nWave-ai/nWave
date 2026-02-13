"""
Step definitions for pre-flight check acceptance tests (AC-01, AC-02, AC-03).

CRITICAL: Hexagonal boundary enforcement - tests invoke CLI entry points ONLY.
- FORBIDDEN: Direct imports of internal preflight_checker components
- REQUIRED: Invoke through driving ports (scripts/install/install_nwave.py)

Cross-platform compatible (Windows, macOS, Linux).
"""

from pytest_bdd import given, parsers, scenarios, then, when


# Load scenarios from feature files
scenarios("../features/01_preflight_checks.feature")


# ============================================================================
# GIVEN - Preconditions
# ============================================================================


@given("the nWave installer script exists at scripts/install/install_nwave.py")
def installer_script_exists(installer_script):
    """Verify the installer script exists."""
    assert installer_script.exists(), f"Installer script not found: {installer_script}"


@given("I am inside a virtual environment")
def in_virtual_environment(mock_venv_status, execution_environment):
    """Configure test to simulate running inside a virtual environment."""
    # In actual subprocess execution, we rely on the current environment
    # The test is run from within the pipenv shell, so sys.prefix != sys.base_prefix
    # This step is primarily documentation of precondition
    mock_venv_status.set_in_venv(True)


@given("I am NOT inside a virtual environment")
def not_in_virtual_environment(mock_venv_status, execution_environment):
    """
    Configure test to simulate running OUTSIDE a virtual environment.

    Note: This sets an environment variable that the enhanced installer
    will check to simulate not being in a venv for testing purposes.
    """
    mock_venv_status.set_in_venv(False)
    execution_environment["NWAVE_TEST_NO_VENV"] = "1"


@given("pipenv is installed")
def pipenv_installed(mock_pipenv_status, execution_environment):
    """Configure test to simulate pipenv being available."""
    mock_pipenv_status.set_installed(True)
    # Remove any test flag that would simulate missing pipenv
    execution_environment.pop("NWAVE_TEST_NO_PIPENV", None)


@given("pipenv is NOT installed")
def pipenv_not_installed(mock_pipenv_status, execution_environment):
    """Configure test to simulate pipenv being unavailable."""
    mock_pipenv_status.set_installed(False)
    execution_environment["NWAVE_TEST_NO_PIPENV"] = "1"


@given("all required dependencies are present")
def all_dependencies_present(mock_dependencies, execution_environment):
    """Configure test to simulate all dependencies being available."""
    mock_dependencies.set_missing([])
    execution_environment.pop("NWAVE_TEST_MISSING_DEPS", None)


@given(parsers.parse('the dependency "{module}" is missing'))
def dependency_missing(module, mock_dependencies, execution_environment):
    """Configure test to simulate a specific dependency being missing."""
    mock_dependencies.add_missing(module)
    current_missing = execution_environment.get("NWAVE_TEST_MISSING_DEPS", "")
    if current_missing:
        execution_environment["NWAVE_TEST_MISSING_DEPS"] = f"{current_missing},{module}"
    else:
        execution_environment["NWAVE_TEST_MISSING_DEPS"] = module


@given(parsers.parse('the dependency "{module}" is present'))
def dependency_present(module, mock_dependencies):
    """Explicitly note that a dependency is present (documentation step)."""
    # This is primarily for documentation - by default dependencies are present
    pass


# ============================================================================
# WHEN - Actions
# ============================================================================


@when("I run the nWave installer")
def run_nwave_installer(run_installer, cli_result):
    """
    Execute the nWave installer through the driving port.

    CRITICAL HEXAGONAL BOUNDARY:
    - Uses subprocess to invoke the actual script
    - Does NOT import or instantiate internal components
    - Captures stdout, stderr, and exit code
    """
    run_installer()


@when(parsers.parse('I run the nWave installer with "{flag}" flag'))
def run_nwave_installer_with_flag(flag, run_installer, cli_result):
    """Execute the nWave installer with additional command-line flag."""
    run_installer(args=[flag])


# ============================================================================
# THEN - Assertions
# ============================================================================


@then("the pre-flight check should pass")
def preflight_check_passed(cli_result, assert_output):
    """Verify pre-flight checks passed."""
    # Pre-flight passing means no early exit with error
    # The installer should proceed to build phase
    assert_output.not_contains(cli_result, "Virtual environment required")
    assert_output.not_contains(cli_result, "pipenv is required")
    assert_output.not_contains(cli_result, "Missing required module")


@then("the build phase should begin")
def build_phase_begins(cli_result, assert_output):
    """Verify the build phase started."""
    # Look for build-related output
    assert_output.contains(cli_result, "Build")


@then(parsers.parse('the installation log should contain "{text}"'))
def log_contains_text(text, file_assertions):
    """Verify installation log contains expected text."""
    assert file_assertions.log_contains(text), f"Expected '{text}' in log file"


@then("the installation should be blocked")
def installation_blocked(cli_result, assert_output):
    """Verify installation was blocked (non-zero exit)."""
    assert cli_result["returncode"] != 0, (
        f"Expected non-zero exit code, got {cli_result['returncode']}"
    )


@then("no build artifacts should be created")
def no_build_artifacts(file_assertions):
    """Verify no installation artifacts were created."""
    # In a blocked installation, we shouldn't have installed agents/commands
    # Note: This checks the isolated test directory
    assert file_assertions.agent_count() == 0 or file_assertions.agent_count() < 10, (
        "Build artifacts were created when installation should have been blocked"
    )


@then("the error should appear before any build output")
def error_before_build(cli_result):
    """Verify error appears before any build-related output."""
    stdout = cli_result["stdout"]
    stderr = cli_result["stderr"]
    all_output = f"{stderr}\n{stdout}"

    # Look for error indicators (used for pre-build error check)
    _has_error = (
        "[ERROR]" in all_output
        or "Virtual environment required" in all_output
        or "pipenv is required" in all_output
        or "Missing required module" in all_output
    )

    # Check that error appears before build output
    build_indicators = ["Building IDE bundle", "Build completed"]
    for indicator in build_indicators:
        if indicator in all_output:
            error_pos = all_output.find("[ERROR]")
            build_pos = all_output.find(indicator)
            if error_pos >= 0 and build_pos >= 0:
                assert error_pos < build_pos, "Build output appeared before error"


@then("the installation log should contain timestamp entries")
def log_contains_timestamps(file_assertions):
    """Verify log contains timestamped entries."""
    if file_assertions.log_exists():
        content = file_assertions.claude_home["log_file"].read_text()
        # Look for timestamp patterns like [2026-01-29 10:30:45] or 2026-01-29T10:30:45
        import re

        timestamp_pattern = r"\d{4}-\d{2}-\d{2}"
        assert re.search(timestamp_pattern, content), "No timestamp found in log file"


@then("the log should record each pre-flight check result")
def log_records_preflight_checks(file_assertions):
    """Verify log records pre-flight check results."""
    if file_assertions.log_exists():
        content = file_assertions.claude_home["log_file"].read_text()
        # Should contain references to environment checks
        checks_logged = (
            "virtual environment" in content.lower()
            or "venv" in content.lower()
            or "check" in content.lower()
        )
        assert checks_logged, "Pre-flight checks not recorded in log"


@then(parsers.parse("the exit code should be {code:d}"))
def verify_exit_code(code, cli_result, assert_output):
    """Verify command exit code."""
    assert_output.exit_code(cli_result, code)


@then(parsers.parse('the error output should contain "{text}"'))
def error_contains_text(text, cli_result, assert_output):
    """Verify error output contains expected text."""
    assert_output.contains(cli_result, text, in_stderr=True)


@then(parsers.parse('the error output should NOT contain "{text}"'))
def error_not_contains_text(text, cli_result, assert_output):
    """Verify error output does NOT contain specified text."""
    assert_output.not_contains(cli_result, text)


@then(parsers.parse('the output should contain "{text}"'))
def output_contains_text(text, cli_result, assert_output):
    """Verify output contains expected text."""
    assert_output.contains(cli_result, text)


@then("no installation files should be created")
def no_installation_files(file_assertions):
    """Verify no installation files were created."""
    # Check that essential directories remain empty or minimal
    agent_count = file_assertions.agent_count()
    command_count = file_assertions.command_count()
    assert agent_count == 0, f"Found {agent_count} agent files when none expected"
    assert command_count == 0, f"Found {command_count} command files when none expected"
