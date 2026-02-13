"""Error formatting for the nWave installer system.

This module provides error output formatting for both terminal (human-readable)
and Claude Code (JSON machine-parseable) contexts. The appropriate format is
selected based on the execution context.

Terminal Format:
    The [ERROR]/[FIX]/[THEN] structure provides human-readable error messages:
    - [ERROR]: Clear description of what went wrong
    - [FIX]: Actionable step to resolve the issue
    - [THEN]: Next step after applying the fix

    When Rich is available and use_colors=True, errors are displayed in styled
    panels with visible borders. Otherwise, ANSI color codes are used.

Claude Code Format:
    JSON output with fields for machine parsing:
    - error_code: Machine-readable error identifier
    - message: Human-readable error description
    - remediation: Action to resolve the error
    - recoverable: Whether the error can be automatically recovered
    - timestamp: ISO 8601 timestamp of when the error occurred

Usage:
    from scripts.install.output_formatter import format_error

    # Automatically selects format based on context
    message = format_error(
        error_code="ENV_NO_VENV",
        message="No virtual environment detected",
        remediation="Run 'pipenv shell' to activate the virtual environment",
        recoverable=True,
    )
    print(message)

    # Or use specific formatters directly
    from scripts.install.output_formatter import TerminalFormatter, ClaudeCodeFormatter

    terminal_formatter = TerminalFormatter(use_colors=True)
    json_formatter = ClaudeCodeFormatter()
"""

import io
import json
import sys
from datetime import datetime


try:
    from scripts.install.context_detector import (
        is_ci_environment,
        is_claude_code_context,
    )
    from scripts.install.error_codes import DEP_MISSING, ENV_NO_PIPENV, ENV_NO_VENV
except ImportError:
    from context_detector import is_ci_environment, is_claude_code_context
    from error_codes import DEP_MISSING, ENV_NO_PIPENV, ENV_NO_VENV

# Try to import Rich for enhanced terminal output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore
    Panel = None  # type: ignore
    Text = None  # type: ignore


# ANSI color codes for terminal output (fallback when Rich unavailable)
_ANSI_RED = "\033[0;31m"
_ANSI_GREEN = "\033[0;32m"
_ANSI_YELLOW = "\033[1;33m"
_ANSI_NC = "\033[0m"  # No Color


class TerminalFormatter:
    """Formats error messages for terminal output with [ERROR]/[FIX]/[THEN] structure.

    The formatter provides human-readable error messages with Rich panel support
    when available, falling back to ANSI colors otherwise.

    When Rich is available and use_colors=True:
    - Errors are displayed in styled panels with visible borders
    - Colors match error severity (red/yellow/green)

    When Rich is unavailable or use_colors=False:
    - Falls back to ANSI color codes or plain text

    Attributes:
        use_colors: Whether to include styling in output.
        _use_rich: Internal flag indicating if Rich should be used.
    """

    def __init__(self, use_colors: bool = True):
        """Initialize the TerminalFormatter.

        Args:
            use_colors: If True, include styling in output (Rich or ANSI).
                       Defaults to True for interactive terminals.
        """
        self.use_colors = use_colors
        # Use Rich only if: available, colors enabled, and stdout is a TTY
        self._use_rich = RICH_AVAILABLE and use_colors and sys.stdout.isatty()

    def _color(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled.

        When Rich is available and use_colors=True, returns Rich markup.
        Otherwise falls back to ANSI codes when use_colors=True,
        or plain text when use_colors=False.

        Args:
            text: The text to colorize.
            color: The ANSI color code to apply (or Rich style via mapping).

        Returns:
            Styled text appropriate for the current context.
        """
        if not self.use_colors:
            return text

        if self._use_rich:
            # Map ANSI codes to Rich styles
            style_map = {
                _ANSI_RED: "bold red",
                _ANSI_YELLOW: "bold yellow",
                _ANSI_GREEN: "bold green",
            }
            style = style_map.get(color, "")
            return f"[{style}]{text}[/{style}]" if style else text

        # Fallback to ANSI codes
        return f"{color}{text}{_ANSI_NC}"

    def _format_with_rich_panel(
        self,
        error_message: str,
        fix_action: str,
        then_action: str,
    ) -> str:
        """Format error as a Rich panel string.

        Creates a styled panel with the [ERROR]/[FIX]/[THEN] structure
        and returns it as a string for consistent return type.

        Args:
            error_message: Human-readable description of the error.
            fix_action: Actionable step to resolve the error.
            then_action: What to do after applying the fix.

        Returns:
            String representation of the Rich panel output.
        """
        # Create styled text content for the panel
        content = Text()
        content.append("[ERROR]", style="bold red")
        content.append(f" {error_message}\n\n")
        content.append("[FIX]", style="bold yellow")
        content.append(f" {fix_action}\n\n")
        content.append("[THEN]", style="bold green")
        content.append(f" {then_action}")

        # Create panel with red border for errors
        panel = Panel(
            content,
            border_style="red",
            padding=(0, 1),
        )

        # Capture panel output as string
        string_io = io.StringIO()
        console = Console(file=string_io, force_terminal=True, width=80)
        console.print(panel)
        return string_io.getvalue().rstrip()

    def format_terminal_error(
        self,
        error_code: str,
        error_message: str,
        fix_action: str,
        then_action: str,
    ) -> str:
        """Format an error message with [ERROR]/[FIX]/[THEN] structure.

        Creates a human-readable error message with clear sections for
        the error description, remediation action, and next steps.

        When Rich is available and colors are enabled, displays the error
        in a styled panel with visible borders. Otherwise falls back to
        ANSI-colored or plain text output.

        Args:
            error_code: The error code identifier (e.g., ENV_NO_VENV).
            error_message: Human-readable description of the error.
            fix_action: Actionable step to resolve the error.
            then_action: What to do after applying the fix.

        Returns:
            Formatted error message string with [ERROR]/[FIX]/[THEN] sections.
        """
        # Use Rich panel when available for styled output
        if self._use_rich:
            return self._format_with_rich_panel(error_message, fix_action, then_action)

        # Fallback to ANSI or plain text
        error_prefix = self._color("[ERROR]", _ANSI_RED)
        fix_prefix = self._color("[FIX]", _ANSI_YELLOW)
        then_prefix = self._color("[THEN]", _ANSI_GREEN)

        lines = [
            f"{error_prefix} {error_message}",
            f"{fix_prefix} {fix_action}",
            f"{then_prefix} {then_action}",
        ]

        return "\n".join(lines)

    def format_dependency_error(
        self,
        module_name: str,
        package_name: str,
    ) -> str:
        """Format a missing dependency error message.

        Creates a human-readable error message for missing Python dependencies
        with clear installation instructions.

        Args:
            module_name: The Python module name that failed to import.
            package_name: The pip package name to install.

        Returns:
            Formatted error message with installation instructions.
        """
        return self.format_terminal_error(
            error_code="DEP_MISSING",
            error_message=f"Required module '{module_name}' is not installed",
            fix_action=f"Run 'pipenv install {package_name}' to install the dependency",
            then_action="Re-run the installer script",
        )

    def format_permission_error(
        self,
        path: str,
        operation: str,
    ) -> str:
        """Format a permission error message.

        Creates a human-readable error message for permission-related issues
        with guidance on resolving access problems.

        Args:
            path: The file or directory path where permission was denied.
            operation: The operation that failed (read, write, execute).

        Returns:
            Formatted error message with permission fix guidance.
        """
        return self.format_terminal_error(
            error_code="PERMISSION_DENIED",
            error_message=f"Permission denied: Cannot {operation} to '{path}'",
            fix_action=f"Check permissions with 'ls -la {path}' and fix with chmod or chown",
            then_action="Re-run the installer script with correct permissions",
        )

    def format_venv_error(self) -> str:
        """Format a virtual environment error message.

        Creates a human-readable error message when no virtual environment
        is detected, with instructions to activate or create one.

        Returns:
            Formatted error message with virtual environment guidance.
        """
        return self.format_terminal_error(
            error_code="ENV_NO_VENV",
            error_message="No virtual environment detected",
            fix_action="Run 'pipenv shell' to activate the virtual environment",
            then_action="Re-run the installer script inside the virtual environment",
        )

    def format_preflight_error_panel(
        self,
        title: str,
        errors: list,
    ) -> str:
        """Format preflight check errors in a styled panel.

        Creates a Rich panel (when available) containing multiple preflight
        check failures with clear visual hierarchy. Falls back to plain text
        formatting when Rich is unavailable or colors are disabled.

        Args:
            title: The panel title (e.g., "Preflight Check Failed").
            errors: List of error dictionaries with 'error', 'fix', and 'then' keys.
                   Each dict should contain:
                   - error: The error description
                   - fix: The remediation action
                   - then: The next step after fixing

        Returns:
            Formatted string containing all preflight errors in a panel.

        Example:
            errors = [
                {
                    "error": "No virtual environment detected",
                    "fix": "Run 'pipenv shell'",
                    "then": "Re-run the installer"
                },
                {
                    "error": "Missing dependency: yaml",
                    "fix": "Run 'pipenv install PyYAML'",
                    "then": "Re-run the installer"
                }
            ]
            result = formatter.format_preflight_error_panel("Preflight Check Failed", errors)
        """
        if not errors:
            return ""

        if self._use_rich:
            # Create Rich panel with multiple errors
            content = Text()

            for i, err in enumerate(errors):
                if i > 0:
                    content.append("\n" + "-" * 40 + "\n\n")

                content.append("[ERROR]", style="bold red")
                content.append(f" {err.get('error', 'Unknown error')}\n\n")
                content.append("[FIX]", style="bold yellow")
                content.append(f" {err.get('fix', 'No fix available')}\n\n")
                content.append("[THEN]", style="bold green")
                content.append(f" {err.get('then', 'Re-run the installer')}")

            panel = Panel(
                content,
                title=title,
                border_style="red",
                padding=(0, 1),
            )

            # Capture panel output as string
            string_io = io.StringIO()
            console = Console(file=string_io, force_terminal=True, width=80)
            console.print(panel)
            return string_io.getvalue().rstrip()

        # Fallback to plain text formatting
        lines = [f"=== {title} ===", ""]

        for i, err in enumerate(errors):
            if i > 0:
                lines.append("-" * 40)
                lines.append("")

            error_prefix = self._color("[ERROR]", _ANSI_RED)
            fix_prefix = self._color("[FIX]", _ANSI_YELLOW)
            then_prefix = self._color("[THEN]", _ANSI_GREEN)

            lines.append(f"{error_prefix} {err.get('error', 'Unknown error')}")
            lines.append(f"{fix_prefix} {err.get('fix', 'No fix available')}")
            lines.append(f"{then_prefix} {err.get('then', 'Re-run the installer')}")
            lines.append("")

        return "\n".join(lines).rstrip()


class ClaudeCodeFormatter:
    """Formats error messages as JSON for Claude Code context.

    The formatter outputs machine-parseable JSON with standardized fields
    that enable Claude Code to provide automated error handling and
    remediation suggestions.

    JSON output includes:
    - error_code: Machine-readable error identifier (from error_codes.py)
    - message: Human-readable error description
    - remediation: Action to resolve the error
    - recoverable: Boolean indicating if error can be automatically recovered
    - timestamp: ISO 8601 timestamp of when the error occurred
    """

    def format_json_error(
        self,
        error_code: str,
        message: str,
        remediation: str,
        recoverable: bool,
    ) -> str:
        """Format an error as JSON for Claude Code parsing.

        Creates a machine-parseable JSON error with all required fields
        for automated error handling.

        Args:
            error_code: The error code identifier (e.g., ENV_NO_VENV).
            message: Human-readable description of the error.
            remediation: Actionable step to resolve the error.
            recoverable: Whether the error can be automatically recovered.

        Returns:
            JSON string with error_code, message, remediation, recoverable,
            and timestamp fields.
        """
        error_data = {
            "error_code": error_code,
            "message": message,
            "remediation": remediation,
            "recoverable": recoverable,
            "timestamp": datetime.now().isoformat(),
        }
        return json.dumps(error_data)

    def format_venv_error(self) -> str:
        """Format a virtual environment error as JSON.

        Creates a JSON error message when no virtual environment
        is detected, with remediation instructions.

        Returns:
            JSON error string with virtual environment guidance.
        """
        return self.format_json_error(
            error_code=ENV_NO_VENV,
            message="No virtual environment detected",
            remediation="Run 'pipenv shell' to activate the virtual environment",
            recoverable=True,
        )

    def format_pipenv_error(self) -> str:
        """Format a missing pipenv error as JSON.

        Creates a JSON error message when pipenv is not available,
        with installation instructions.

        Returns:
            JSON error string with pipenv installation guidance.
        """
        return self.format_json_error(
            error_code=ENV_NO_PIPENV,
            message="Pipenv is not available",
            remediation="Install pipenv with 'pip install pipenv' or 'brew install pipenv'",
            recoverable=True,
        )

    def format_dependency_error(
        self,
        module_name: str,
        package_name: str,
    ) -> str:
        """Format a missing dependency error as JSON.

        Creates a JSON error message for missing Python dependencies
        with installation instructions.

        Args:
            module_name: The Python module name that failed to import.
            package_name: The pip package name to install.

        Returns:
            JSON error string with installation instructions.
        """
        return self.format_json_error(
            error_code=DEP_MISSING,
            message=f"Required module '{module_name}' is not installed",
            remediation=f"Run 'pipenv install {package_name}' to install the dependency",
            recoverable=True,
        )


class CIFormatter:
    """Formats error messages for CI (Continuous Integration) environments.

    CI environments require specific output formatting:
    - No ANSI color codes (breaks log parsing)
    - Verbose output by default (for pipeline debugging)
    - No interactive prompts (non-TTY environment)
    - Proper exit codes for pipeline status reporting

    The formatter outputs plain text with timestamps for log correlation
    and includes all error details for debugging.

    Attributes:
        verbose: Whether to include verbose details (always True for CI).
        interactive: Whether interactive prompts are enabled (always False for CI).
    """

    def __init__(self):
        """Initialize the CIFormatter with CI-appropriate defaults.

        Sets verbose=True and interactive=False for CI environments.
        """
        self.verbose = True
        self.interactive = False

    def is_interactive(self) -> bool:
        """Check if interactive prompts are enabled.

        Returns:
            Always False for CI environments.
        """
        return self.interactive

    def format_ci_error(
        self,
        error_code: str,
        message: str,
        remediation: str,
    ) -> str:
        """Format an error message for CI environment output.

        Creates a plain text error message without ANSI colors, with
        timestamps for log correlation and all details for verbose output.

        Args:
            error_code: The error code identifier (e.g., ENV_NO_VENV).
            message: Human-readable description of the error.
            remediation: Actionable step to resolve the error.

        Returns:
            Plain text error string suitable for CI logs.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"[{timestamp}] ERROR: {message}",
            f"  Error Code: {error_code}",
            f"  Remediation: {remediation}",
            "  Exit Status: Non-zero (failure)",
        ]

        return "\n".join(lines)

    def get_exit_code(self, success: bool) -> int:
        """Get the appropriate exit code for CI pipeline status.

        Args:
            success: Whether the operation was successful.

        Returns:
            0 for success, 1 for failure.
        """
        return 0 if success else 1

    def confirm_action(self, prompt: str, default: bool) -> bool:
        """Handle confirmation without interactive prompt.

        In CI environments, interactive prompts are disabled.
        This method returns the default value without any user interaction.

        Args:
            prompt: The confirmation prompt text (ignored in CI mode).
            default: The default value to return.

        Returns:
            The default value without any prompt.
        """
        return default

    def format_venv_error(self) -> str:
        """Format a virtual environment error for CI output.

        Returns:
            Plain text error string for missing virtual environment.
        """
        return self.format_ci_error(
            error_code=ENV_NO_VENV,
            message="No virtual environment detected",
            remediation="Run 'pipenv shell' to activate the virtual environment",
        )

    def format_dependency_error(
        self,
        module_name: str,
        package_name: str,
    ) -> str:
        """Format a missing dependency error for CI output.

        Args:
            module_name: The Python module name that failed to import.
            package_name: The pip package name to install.

        Returns:
            Plain text error string with installation instructions.
        """
        return self.format_ci_error(
            error_code=DEP_MISSING,
            message=f"Required module '{module_name}' is not installed",
            remediation=f"Run 'pipenv install {package_name}' to install the dependency",
        )


def format_error(
    error_code: str,
    message: str,
    remediation: str,
    recoverable: bool,
) -> str:
    """Format an error using the appropriate formatter for the current context.

    Automatically selects between JSON output (for Claude Code), CI output
    (for continuous integration environments), and terminal output (for
    interactive terminals) based on the execution context detected by
    context_detector.

    Context priority:
    1. Claude Code (JSON output for machine parsing)
    2. CI environment (plain text without colors for log parsing)
    3. Terminal (human-readable with colors)

    Args:
        error_code: The error code identifier (e.g., ENV_NO_VENV).
        message: Human-readable description of the error.
        remediation: Actionable step to resolve the error.
        recoverable: Whether the error can be automatically recovered.

    Returns:
        Formatted error string (JSON for Claude Code, plain text for CI,
        colored terminal format otherwise).
    """
    if is_claude_code_context():
        formatter = ClaudeCodeFormatter()
        return formatter.format_json_error(
            error_code=error_code,
            message=message,
            remediation=remediation,
            recoverable=recoverable,
        )
    elif is_ci_environment():
        formatter = CIFormatter()
        return formatter.format_ci_error(
            error_code=error_code,
            message=message,
            remediation=remediation,
        )
    else:
        formatter = TerminalFormatter(use_colors=True)
        return formatter.format_terminal_error(
            error_code=error_code,
            error_message=message,
            fix_action=remediation,
            then_action="Re-run the installer script",
        )
