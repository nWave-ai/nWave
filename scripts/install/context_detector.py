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
import shutil
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


class TargetPlatform(Enum):
    """Target AI coding platforms for nWave installation.

    CLAUDE_CODE: Anthropic's Claude Code CLI
    OPENCODE: OpenCode AI coding assistant (Charm Bracelet, ~/.config/opencode/)
    CODEX: OpenAI Codex CLI (Rust, ~/.codex/)
    CURSOR: Cursor IDE / agent (hooks under ~/.cursor/)
    COPILOT_CLI: GitHub Copilot CLI (@github/copilot, ~/.copilot/)
    OMP: oh-my-pi (omp, ~/.omp/)
    """

    CLAUDE_CODE = "claude_code"
    OPENCODE = "opencode"
    CODEX = "codex"
    CURSOR = "cursor"
    COPILOT_CLI = "copilot"
    OMP = "omp"
    DEVIN = "devin"


def _detect_claude_code() -> bool:
    """Detect if Claude Code is available for installation.

    Checks two signals:
    - the resolved Claude config directory exists
    - CLAUDE_CODE environment variable is set

    The directory is resolved through ``PathUtils.get_claude_config_dir()`` --
    the SAME resolver the installer writes through, so it honors
    ``CLAUDE_CONFIG_DIR`` (the documented multi-profile setup). Deciding here on
    the hardcoded ``~/.claude`` instead keys on the DESIGNATION rather than on
    the property "a Claude config directory exists where we would install":
    with ``CLAUDE_CONFIG_DIR`` set and no ``~/.claude``, writer and detector
    disagreed, and the installer announced a target it never wrote into while
    still reporting success.

    Returns:
        True if any Claude Code signal is detected.
    """
    try:
        from scripts.install.install_utils import PathUtils
    except ImportError:  # installed layout: scripts/install/ is on sys.path
        from install_utils import PathUtils  # type: ignore[no-redef]

    claude_dir_exists = PathUtils.get_claude_config_dir().is_dir()
    claude_env_set = bool(os.environ.get("CLAUDE_CODE", ""))
    return claude_dir_exists or claude_env_set


def _detect_opencode() -> bool:
    """Detect if OpenCode is available for installation.

    Checks two signals:
    - `opencode` binary in PATH (via shutil.which)
    - ~/.config/opencode/ directory exists

    Returns:
        True if any OpenCode signal is detected.
    """
    opencode_binary = shutil.which("opencode") is not None
    opencode_config_exists = (Path.home() / ".config" / "opencode").is_dir()
    return opencode_binary or opencode_config_exists


def _detect_codex() -> bool:
    """Detect if Codex CLI is available for installation.

    Checks three signals:
    - `codex` binary in PATH (via shutil.which)
    - CODEX_HOME environment variable (if set)
    - ~/.codex/ directory exists

    Returns:
        True if any Codex CLI signal is detected.
    """
    codex_binary = shutil.which("codex") is not None
    codex_config_override = os.environ.get("CODEX_HOME")
    codex_config_exists = (
        Path(codex_config_override).is_dir()
        if codex_config_override
        else (Path.home() / ".codex").is_dir()
    )
    return codex_binary or codex_config_exists


def _detect_cursor() -> bool:
    """Detect if Cursor is available for installation.

    Checks three signals:
    - `cursor` binary in PATH (via shutil.which)
    - CURSOR_HOME environment variable (if set)
    - ~/.cursor/ directory exists

    Returns:
        True if any Cursor signal is detected.
    """
    cursor_binary = shutil.which("cursor") is not None
    cursor_config_override = os.environ.get("CURSOR_HOME")
    cursor_config_exists = (
        Path(cursor_config_override).is_dir()
        if cursor_config_override
        else (Path.home() / ".cursor").is_dir()
    )
    return cursor_binary or cursor_config_exists


def _detect_copilot() -> bool:
    """Detect if GitHub Copilot CLI is available for installation.

    Checks the spike-validated signals (copilot-cli-prereq-spike-2026-05-28 §4):
    - COPILOT_CLI env set (the binary exports COPILOT_CLI=1 into hook subprocesses)
    - $COPILOT_HOME (or ~/.copilot) directory exists (created on first launch)
    - `copilot` binary in PATH (via shutil.which)

    Returns:
        True if any Copilot CLI signal is detected.
    """
    copilot_env = bool(os.environ.get("COPILOT_CLI", ""))
    copilot_home_override = os.environ.get("COPILOT_HOME")
    copilot_home = (
        Path(copilot_home_override)
        if copilot_home_override
        else Path.home() / ".copilot"
    )
    copilot_config_exists = copilot_home.is_dir()
    copilot_binary = shutil.which("copilot") is not None
    return copilot_env or copilot_config_exists or copilot_binary


def _detect_omp() -> bool:
    """Detect if OMP (oh-my-pi) is available for installation.

    Checks two signals, mirroring the Codex/OpenCode detectors:
    - `omp` binary in PATH (via shutil.which)
    - the OMP native agent directory exists

    The directory is the config-root agent dir, ``$HOME/.omp/agent`` by
    default. OMP's documented ``PI_CONFIG_DIR`` override renames the config
    root under home, so detection resolves through ``omp_agent_dir()`` -- the
    SAME resolver the omp installer plugins write through. Deciding on a
    hardcoded ``~/.omp`` instead would key on the designation rather than on
    the property "an OMP agent dir exists where we would install".

    Returns:
        True if any OMP signal is detected.
    """
    try:
        from scripts.shared.install_paths import omp_agent_dir
    except ImportError:  # installed layout: scripts/ is on sys.path
        from shared.install_paths import omp_agent_dir  # type: ignore[no-redef]

    omp_binary = shutil.which("omp") is not None
    omp_config_exists = omp_agent_dir().is_dir()
    return omp_binary or omp_config_exists


def _detect_devin() -> bool:
    """Detect if Devin CLI is available for installation.

    Checks two signals:
    - `devin` binary in PATH (via shutil.which)
    - ~/.config/devin/ directory exists (created on first Devin CLI launch)

    DEVIN_CONFIG_DIR may override the config root for test isolation.

    Returns:
        True if any Devin CLI signal is detected.
    """
    try:
        from scripts.shared.install_paths import devin_config_dir
    except ImportError:  # installed layout: scripts/ is on sys.path
        from shared.install_paths import devin_config_dir  # type: ignore[no-redef]

    devin_binary = shutil.which("devin") is not None
    devin_config_exists = devin_config_dir().is_dir()
    return devin_binary or devin_config_exists


def detect_target_platforms() -> set[TargetPlatform]:
    """Auto-detect which AI coding platforms are available for installation.

    Detection signals:
    - Claude Code: ~/.claude/ directory exists OR CLAUDE_CODE env var set
    - OpenCode: `opencode` binary in PATH (shutil.which) OR ~/.config/opencode/ exists
    - Codex CLI: `codex` binary in PATH OR `CODEX_HOME` OR ~/.codex/ exists
    - Cursor: `cursor` binary in PATH OR `CURSOR_HOME` OR ~/.cursor/ exists
    - Copilot CLI: COPILOT_CLI env set OR $COPILOT_HOME/~/.copilot/ exists OR
      `copilot` binary in PATH
    - OMP: `omp` binary in PATH OR the OMP native agent directory exists
    - Devin CLI: `devin` binary in PATH OR ~/.config/devin/ directory exists

    Returns:
        Set of detected platforms, which is empty when no supported host is
        discoverable. The command entry point refuses that ambiguous case and
        tells the operator to select one explicitly with ``--platform``.
    """
    platforms: set[TargetPlatform] = set()

    if _detect_claude_code():
        platforms.add(TargetPlatform.CLAUDE_CODE)

    if _detect_opencode():
        platforms.add(TargetPlatform.OPENCODE)

    if _detect_codex():
        platforms.add(TargetPlatform.CODEX)

    if _detect_cursor():
        platforms.add(TargetPlatform.CURSOR)

    if _detect_copilot():
        platforms.add(TargetPlatform.COPILOT_CLI)

    if _detect_omp():
        platforms.add(TargetPlatform.OMP)

    if _detect_devin():
        platforms.add(TargetPlatform.DEVIN)

    return platforms
