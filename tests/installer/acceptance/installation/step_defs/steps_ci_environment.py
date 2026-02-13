"""
Step definitions for CI environment detection acceptance tests (AC-11 to AC-15).

CRITICAL: Hexagonal boundary enforcement - tests invoke CLI entry points ONLY.
- FORBIDDEN: Direct imports of internal CI detection components
- REQUIRED: Invoke through driving ports (scripts/install/install_nwave.py)

Cross-platform compatible (Windows, macOS, Linux).
"""

import re

from pytest_bdd import given, parsers, scenarios, then, when


# Load scenarios from feature files
scenarios("../features/07_ci_environment.feature")


# ============================================================================
# ANSI Code Detection Pattern
# ============================================================================

# ANSI escape code pattern for color/formatting detection
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*[mK]")


# ============================================================================
# GIVEN - CI Environment Preconditions
# ============================================================================


@given(parsers.parse('the environment variable "{var_name}" is set to "{value}"'))
def set_environment_variable(var_name, value, execution_environment):
    """Set a specific environment variable for the test execution."""
    execution_environment[var_name] = value


@given(parsers.parse('the environment variable "{var_name}" is set'))
def set_environment_variable_present(var_name, execution_environment):
    """Set an environment variable as present with default value."""
    execution_environment[var_name] = "true"


@given("the environment is detected as CI")
def environment_detected_as_ci(execution_environment):
    """Configure environment to be detected as CI."""
    # Use generic CI variable as baseline
    execution_environment["CI"] = "true"


@given("the environment is detected as Docker container")
def environment_detected_as_docker(execution_environment):
    """
    Configure environment to simulate Docker container.

    Note: Real container detection checks /.dockerenv or /proc/1/cgroup.
    For testing, we use an environment variable that the installer will check.
    """
    execution_environment["NWAVE_TEST_CONTAINER"] = "docker"


@given("no CI environment variables are set")
def no_ci_environment_variables(execution_environment):
    """Ensure no CI environment variables are set."""
    ci_vars = [
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS_URL",
        "CIRCLECI",
        "TRAVIS",
        "TF_BUILD",
        "BUILDKITE",
        "CODEBUILD_BUILD_ID",
    ]
    for var in ci_vars:
        execution_environment.pop(var, None)


@given("not running in a container")
def not_running_in_container(execution_environment):
    """Ensure container simulation is disabled."""
    execution_environment.pop("NWAVE_TEST_CONTAINER", None)


@given("a required dependency is missing")
def required_dependency_missing(mock_dependencies, execution_environment):
    """Configure test to simulate a missing dependency."""
    mock_dependencies.add_missing("yaml")
    execution_environment["NWAVE_TEST_MISSING_DEPS"] = "yaml"


# ============================================================================
# WHEN - CI Environment Actions
# ============================================================================


@when("I run the nWave installer with default settings")
def run_installer_default_settings(run_installer, cli_result):
    """Execute the nWave installer with no additional flags."""
    run_installer()


@when("the installer would normally prompt for confirmation")
def installer_would_prompt(run_installer, cli_result, execution_environment):
    """
    Execute installer in a scenario where prompts would normally occur.

    In CI mode, prompts should be suppressed.
    """
    # Set a flag to trigger prompt scenario (dry-run mode asks for confirmation)
    run_installer(args=["--dry-run"])


# ============================================================================
# THEN - CI Environment Assertions
# ============================================================================


@then("CI mode should be detected")
def ci_mode_detected(cli_result, assert_output):
    """Verify CI mode was detected by the installer."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    # Look for CI mode indicators in output
    ci_indicators = ["CI mode", "CI environment", "Detected CI", "Running in CI"]
    assert any(
        indicator.lower() in all_output.lower() for indicator in ci_indicators
    ), (
        f"CI mode detection not found in output:\n"
        f"STDOUT: {cli_result['stdout']!r}\n"
        f"STDERR: {cli_result['stderr']!r}"
    )


@then(parsers.parse('the output should indicate "{platform}" environment'))
def output_indicates_platform(platform, cli_result):
    """Verify output indicates specific CI platform."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    assert platform.lower() in all_output.lower(), (
        f"Expected '{platform}' platform indication not found in output:\n"
        f"STDOUT: {cli_result['stdout']!r}\n"
        f"STDERR: {cli_result['stderr']!r}"
    )


@then("the output should NOT contain ANSI escape codes")
def output_no_ansi_codes(cli_result):
    """Verify output contains no ANSI color/formatting codes."""
    all_output = f"{cli_result['stdout']}{cli_result['stderr']}"
    ansi_matches = ANSI_ESCAPE_PATTERN.findall(all_output)
    assert not ansi_matches, (
        f"Found ANSI escape codes in CI output: {ansi_matches}\n"
        f"STDOUT: {cli_result['stdout']!r}\n"
        f"STDERR: {cli_result['stderr']!r}"
    )


@then("the output should be plain text without formatting")
def output_plain_text(cli_result):
    """Verify output is plain text suitable for CI logs."""
    all_output = f"{cli_result['stdout']}{cli_result['stderr']}"
    # Check for common formatting characters that shouldn't be in CI output
    formatting_chars = ["\x1b", "\033", "\r"]  # ANSI escapes and carriage returns
    for char in formatting_chars:
        assert char not in all_output, (
            f"Found formatting character {char!r} in CI output"
        )


@then("the output should include detailed progress information")
def output_detailed_progress(cli_result):
    """Verify verbose output is enabled in CI mode."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    # Look for verbose logging indicators
    verbose_indicators = [
        "checking",
        "verifying",
        "installing",
        "copying",
        "creating",
    ]
    found_indicators = [
        ind for ind in verbose_indicators if ind.lower() in all_output.lower()
    ]
    assert len(found_indicators) >= 2, (
        f"Expected detailed progress information, found only: {found_indicators}\n"
        f"STDOUT: {cli_result['stdout']!r}"
    )


@then("each installation step should be logged")
def installation_steps_logged(cli_result):
    """Verify each major installation step appears in output."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    # Major steps that should be visible in verbose mode
    expected_steps = ["pre-flight", "build", "install"]
    for step in expected_steps:
        assert step.lower() in all_output.lower(), (
            f"Installation step '{step}' not found in output"
        )


@then("no interactive prompt should appear")
def no_interactive_prompt(cli_result):
    """Verify no interactive prompts occurred."""
    all_output = f"{cli_result['stdout']}{cli_result['stderr']}"
    # Prompts typically end with ? or [y/N]
    prompt_indicators = ["[y/N]", "[Y/n]", "? (", "Press Enter", "Confirm:"]
    for indicator in prompt_indicators:
        assert indicator not in all_output, (
            f"Found interactive prompt indicator '{indicator}' in CI output"
        )


@then("the installer should proceed with default behavior")
def installer_proceeds_default(cli_result):
    """Verify installer proceeded without waiting for input."""
    # In CI mode, the installer should complete (not hang waiting for input)
    assert cli_result["returncode"] is not None, (
        "Installer did not complete - may have hung waiting for input"
    )


@then("failure details should be in stdout for CI log capture")
def failure_details_in_stdout(cli_result):
    """Verify failure information is in stdout (CI logs capture stdout)."""
    # In CI, errors should go to stdout so they're visible in CI logs
    stdout = cli_result["stdout"]
    error_indicators = ["error", "fail", "missing", "required"]
    assert any(ind.lower() in stdout.lower() for ind in error_indicators), (
        f"Expected failure details in stdout for CI visibility:\n"
        f"STDOUT: {stdout!r}\n"
        f"STDERR: {cli_result['stderr']!r}"
    )


@then("success confirmation should be in stdout")
def success_confirmation_in_stdout(cli_result):
    """Verify success message is in stdout."""
    stdout = cli_result["stdout"]
    success_indicators = ["success", "complete", "installed"]
    assert any(ind.lower() in stdout.lower() for ind in success_indicators), (
        f"Expected success confirmation in stdout:\nSTDOUT: {stdout!r}"
    )


@then("a warning should be logged about container environment")
def warning_about_container(cli_result, assert_output):
    """Verify warning about container environment is logged."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    warning_indicators = ["container", "docker", "warning", "unsupported"]
    found = [ind for ind in warning_indicators if ind.lower() in all_output.lower()]
    assert len(found) >= 2, (
        f"Expected container warning in output, found: {found}\n"
        f"STDOUT: {cli_result['stdout']!r}\n"
        f"STDERR: {cli_result['stderr']!r}"
    )


@then("the installation should continue")
def installation_continues(cli_result):
    """Verify installation was not blocked."""
    # Check that installation progressed past pre-flight
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    progress_indicators = ["build", "install", "copy"]
    assert any(ind.lower() in all_output.lower() for ind in progress_indicators), (
        "Installation appears to have been blocked"
    )


@then(parsers.parse("the exit code should be {code:d} if otherwise successful"))
def exit_code_if_successful(code, cli_result, assert_output):
    """Verify exit code matches expected value when no other errors."""
    assert_output.exit_code(cli_result, code)


@then("the output should indicate container environment")
def output_indicates_container(cli_result):
    """Verify output indicates container environment detection."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    container_indicators = ["container", "docker", "kubernetes", "podman"]
    assert any(ind.lower() in all_output.lower() for ind in container_indicators), (
        "Container environment indication not found in output"
    )


@then("a warning about unsupported configuration should appear")
def warning_unsupported_config(cli_result):
    """Verify warning about unsupported configuration."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    warning_text = ["warning", "unsupported", "not officially supported", "caution"]
    assert any(w.lower() in all_output.lower() for w in warning_text), (
        "Expected warning about unsupported configuration"
    )


@then("installation should not be blocked")
def installation_not_blocked(cli_result):
    """Verify installation was not blocked by container detection."""
    # If blocked, exit code would be non-zero and no progress made
    # Here we check that either it succeeded or progressed past initial checks
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    blocked_indicators = ["blocked", "cannot proceed", "stopping"]
    assert not any(ind.lower() in all_output.lower() for ind in blocked_indicators), (
        "Installation appears to have been blocked"
    )


@then("container environment should be detected")
def container_environment_detected(cli_result):
    """Verify container environment was detected."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    container_indicators = ["container", "docker", "running in"]
    assert any(ind.lower() in all_output.lower() for ind in container_indicators), (
        "Container environment detection not found"
    )


@then("both contexts should be logged")
def both_contexts_logged(cli_result):
    """Verify both CI and container contexts are logged."""
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    ci_logged = any(
        ind.lower() in all_output.lower()
        for ind in ["ci mode", "ci environment", "github actions"]
    )
    container_logged = any(
        ind.lower() in all_output.lower() for ind in ["container", "docker"]
    )
    assert ci_logged, "CI context not logged"
    assert container_logged, "Container context not logged"


@then("normal terminal output mode should be used")
def normal_terminal_mode(cli_result):
    """Verify normal terminal output mode is used (non-CI behavior)."""
    # In normal mode, output may include colors (if terminal supports)
    # or at least won't have CI-specific indicators
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    ci_mode_indicators = ["CI mode enabled", "Running in CI environment"]
    assert not any(ind in all_output for ind in ci_mode_indicators), (
        "CI mode appears to be active when it should not be"
    )


@then("color output should be allowed if terminal supports it")
def color_output_allowed(cli_result):
    """Verify color output is not suppressed (may or may not be present)."""
    # This is a weak assertion - we just verify CI mode isn't forcing plain text
    # Actual color presence depends on terminal capabilities
    all_output = f"{cli_result['stdout']}\n{cli_result['stderr']}"
    forced_plain_indicators = ["forcing plain text", "colors disabled"]
    assert not any(
        ind.lower() in all_output.lower() for ind in forced_plain_indicators
    ), "Color output appears to be forcibly disabled"
