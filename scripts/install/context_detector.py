"""Execution context detection for the nWave installer system.

This module provides context detection capabilities to determine the
execution environment (interactive terminal vs Claude Code). The detection
enables the output_formatter module to choose appropriate output formats:
- Human-readable text with colors/emojis for interactive terminals
- JSON structured output for Claude Code machine parsing

The detection uses multiple signals:
1. TTY detection: sys.stdout.isatty() for terminal interactivity
2. CLAUDE_CODE environment variable: explicit Claude Code context marker
3. CI environment variables: GITHUB_ACTIONS, GITLAB_CI, CI, JENKINS_URL
4. Container markers: /.dockerenv file, KUBERNETES_SERVICE_HOST env var

Usage:
    from scripts.install.context_detector import (
        ExecutionContext,
        get_execution_context,
        is_interactive,
        is_ci_environment,
        get_ci_platform,
        is_container_environment,
    )

    context = get_execution_context()
    if context == ExecutionContext.CLAUDE_CODE:
        # Use JSON output
        pass
    elif is_ci_environment():
        # CI context: verbose output without colors
        platform = get_ci_platform()
        pass
    elif is_container_environment():
        # Container context: may warn about non-persistent installations
        pass
    elif is_interactive():
        # Use rich terminal output with prompts
        pass
"""

import os
import sys
from enum import Enum
from pathlib import Path


# CI platform environment variable mappings
CI_PLATFORM_ENV_VARS = {
    "github_actions": "GITHUB_ACTIONS",
    "gitlab_ci": "GITLAB_CI",
    "jenkins": "JENKINS_URL",
    "generic": "CI",
}


class ExecutionContext(Enum):
    """Enumeration of possible execution contexts.

    TERMINAL: Running in an interactive terminal (human user)
    CLAUDE_CODE: Running within Claude Code environment (machine parsing)
    """

    TERMINAL = "terminal"
    CLAUDE_CODE = "claude_code"


def is_tty() -> bool:
    """Detect if stdout is connected to a TTY (terminal).

    Returns:
        True if stdout is a TTY, False otherwise.

    Note:
        This indicates whether the output stream supports terminal
        features like colors and cursor control.
    """
    return sys.stdout.isatty()


def is_claude_code_context() -> bool:
    """Detect if running within Claude Code environment.

    Checks for the presence and non-empty value of the CLAUDE_CODE
    environment variable, which Claude Code sets when executing
    installer scripts.

    Returns:
        True if CLAUDE_CODE environment variable is set to a non-empty
        value, False otherwise.
    """
    claude_code_value = os.environ.get("CLAUDE_CODE", "")
    return bool(claude_code_value)


def is_interactive() -> bool:
    """Determine if the execution context supports interactive prompts.

    An interactive context requires:
    1. stdout to be a TTY (terminal)
    2. NOT running within Claude Code context

    This function is used to decide whether to show interactive
    prompts, progress bars, and other terminal-specific features
    that require human interaction.

    Returns:
        True if running in an interactive terminal context where
        user prompts and terminal features are appropriate,
        False otherwise.
    """
    return is_tty() and not is_claude_code_context()


def get_execution_context() -> ExecutionContext:
    """Get the current execution context.

    Determines whether the installer is running in Claude Code
    context (requiring JSON output) or in a standard terminal
    context (supporting human-readable output).

    Returns:
        ExecutionContext.CLAUDE_CODE if in Claude Code environment,
        ExecutionContext.TERMINAL otherwise.

    Note:
        This is the primary function for output format decisions.
        Claude Code context takes precedence over terminal detection
        since Claude Code may still have a TTY but requires JSON output.
    """
    if is_claude_code_context():
        return ExecutionContext.CLAUDE_CODE
    return ExecutionContext.TERMINAL


def is_ci_environment() -> bool:
    """Detect if running in a CI (Continuous Integration) environment.

    Checks for presence of common CI environment variables:
    - GITHUB_ACTIONS: GitHub Actions
    - GITLAB_CI: GitLab CI/CD
    - JENKINS_URL: Jenkins
    - CI: Generic CI indicator (used by many CI systems)

    Returns:
        True if any CI environment variable is set to a non-empty value,
        False otherwise.

    Note:
        CI environments typically require verbose output without colors
        and should not prompt for user input.
    """
    ci_env_vars = ["GITHUB_ACTIONS", "GITLAB_CI", "CI", "JENKINS_URL"]
    return any(bool(os.environ.get(var, "")) for var in ci_env_vars)


def get_ci_platform() -> str | None:
    """Get the specific CI platform if running in a CI environment.

    Identifies the CI platform based on environment variables in order
    of specificity (most specific first):
    1. GITHUB_ACTIONS -> "github_actions"
    2. GITLAB_CI -> "gitlab_ci"
    3. JENKINS_URL -> "jenkins"
    4. CI (generic) -> "generic"

    Returns:
        The CI platform name as a string if in a CI environment,
        None if not in any CI environment.

    Note:
        More specific platforms are checked first, so if both
        GITHUB_ACTIONS and CI are set, "github_actions" is returned.
    """
    # Check in order of specificity (most specific first)
    if os.environ.get("GITHUB_ACTIONS", ""):
        return "github_actions"
    if os.environ.get("GITLAB_CI", ""):
        return "gitlab_ci"
    if os.environ.get("JENKINS_URL", ""):
        return "jenkins"
    if os.environ.get("CI", ""):
        return "generic"
    return None


def is_container_environment() -> bool:
    """Detect if running inside a container environment.

    Checks for container indicators:
    - /.dockerenv file existence: Docker container marker
    - KUBERNETES_SERVICE_HOST env var: Kubernetes pod indicator

    Returns:
        True if running in a Docker or Kubernetes container,
        False otherwise.

    Note:
        Container environments may need warnings about non-persistent
        installations since container filesystems are ephemeral by default.
    """
    # Check for Docker container marker file
    dockerenv_exists = Path("/.dockerenv").exists()

    # Check for Kubernetes environment variable
    kubernetes_host = bool(os.environ.get("KUBERNETES_SERVICE_HOST", ""))

    return dockerenv_exists or kubernetes_host
