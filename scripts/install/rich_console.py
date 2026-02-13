#!/usr/bin/env python3
"""Rich console integration for enhanced terminal output.

This module provides Rich-based console output for the nWave installer system.
It replaces the legacy Colors class with Rich console features while maintaining
backward compatibility with existing Logger API.

Classes:
    RichLogger: Logger with Rich console styling (info/warn/error/step methods)
    PlainLogger: Plain text logger without colors (for CI environments)
    SilentLogger: Logger that only writes to file (for Claude Code context)
    ConsoleFactory: Factory that creates appropriate logger based on context

Usage:
    from scripts.install.rich_console import ConsoleFactory

    # Automatically select appropriate logger based on context
    logger = ConsoleFactory.create_logger()
    logger.info("Installation started")
    logger.warn("Warning message")
    logger.error("Error message")
    logger.step("Processing step")

    # Or use RichLogger directly for explicit Rich formatting
    from scripts.install.rich_console import RichLogger
    logger = RichLogger()
    with logger.progress_spinner("Installing..."):
        # long operation
        pass
"""

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


# Try to import Rich, but gracefully handle if not available
try:
    from rich import print as rprint
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore
    Panel = None  # type: ignore
    Table = None  # type: ignore
    Text = None  # type: ignore
    rprint = print  # type: ignore


class RichLogger:
    """Logger with Rich console styling.

    Provides colorful, styled output using the Rich library. Falls back to
    plain ANSI colors if Rich is not available.

    Attributes:
        log_file: Optional path to log file for persistent logging.
        silent: If True, suppress all console output.
        console: Rich Console instance for styled output.
    """

    # ANSI color codes as fallback when Rich is unavailable
    _ANSI_GREEN = "\033[0;32m"
    _ANSI_YELLOW = "\033[1;33m"
    _ANSI_RED = "\033[0;31m"
    _ANSI_BLUE = "\033[0;34m"
    _ANSI_CYAN = "\033[0;36m"
    _ANSI_NC = "\033[0m"

    def __init__(self, log_file: Path | None = None, silent: bool = False):
        """Initialize RichLogger.

        Args:
            log_file: Path to log file. If None, only console logging is enabled.
            silent: If True, suppress console output (log to file only).
        """
        self.log_file = log_file
        self.silent = silent

        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize Rich console if available
        if RICH_AVAILABLE:
            self.console = Console(force_terminal=not silent)
        else:
            self.console = None

    def _write_to_file(self, level: str, message: str) -> None:
        """Write log message to file."""
        if not self.log_file:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {level}: {message}"

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
        except Exception:
            pass  # Ignore log file errors

    def _print_rich(self, message: str, style: str) -> None:
        """Print using Rich console with style."""
        if self.silent:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.console and RICH_AVAILABLE:
            styled_text = Text()
            styled_text.append(f"[{timestamp}] ", style="dim")
            styled_text.append(message, style=style)
            self.console.print(styled_text)
        else:
            # Fallback to ANSI colors
            color_map = {
                "green": self._ANSI_GREEN,
                "yellow": self._ANSI_YELLOW,
                "red": self._ANSI_RED,
                "blue": self._ANSI_BLUE,
                "cyan": self._ANSI_CYAN,
                "bold green": self._ANSI_GREEN,
                "bold yellow": self._ANSI_YELLOW,
                "bold red": self._ANSI_RED,
                "bold blue": self._ANSI_BLUE,
            }
            color = color_map.get(style, self._ANSI_NC)
            print(f"{color}[{timestamp}] {message}{self._ANSI_NC}")

    def info(self, message: str) -> None:
        """Log info message in green."""
        self._print_rich(f"INFO: {message}", "green")
        self._write_to_file("INFO", message)

    def warn(self, message: str) -> None:
        """Log warning message in yellow."""
        self._print_rich(f"WARN: {message}", "yellow")
        self._write_to_file("WARN", message)

    def error(self, message: str) -> None:
        """Log error message in red."""
        self._print_rich(f"ERROR: {message}", "bold red")
        self._write_to_file("ERROR", message)

    def step(self, message: str) -> None:
        """Log step message in blue."""
        self._print_rich(f"STEP: {message}", "blue")
        self._write_to_file("STEP", message)

    @contextmanager
    def progress_spinner(self, message: str, spinner_style: str = "dots12"):
        """Context manager for showing a spinner during long operations.

        Args:
            message: Message to display alongside the spinner.
            spinner_style: Rich spinner style name (e.g. dots, line, moon, earth,
                dots12, aesthetic). Defaults to "dots12".

        Yields:
            None

        Example:
            with logger.progress_spinner("Installing..."):
                # long operation
                pass
        """
        if self.silent or not RICH_AVAILABLE or not self.console:
            # No spinner in silent mode or without Rich
            self.step(message)
            yield
            return

        try:
            from rich.status import Status

            self._write_to_file("STEP", message)
            with Status(message, console=self.console, spinner=spinner_style):
                yield
        except ImportError:
            # Fallback if Status not available
            self.step(message)
            yield

    def table(
        self, headers: list[str], rows: list[list[str]], title: str | None = None
    ) -> None:
        """Print a Rich table.

        Args:
            headers: List of column header strings.
            rows: List of rows, where each row is a list of cell values.
            title: Optional table title.
        """
        if self.silent:
            return

        if RICH_AVAILABLE and self.console and Table:
            table = Table(title=title)
            for header in headers:
                table.add_column(header)
            for row in rows:
                table.add_row(*row)
            self.console.print(table)
        else:
            # Fallback to plain text table
            if title:
                print(f"\n{title}")
                print("=" * len(title))

            # Print headers
            header_line = " | ".join(headers)
            print(header_line)
            print("-" * len(header_line))

            # Print rows
            for row in rows:
                print(" | ".join(str(cell) for cell in row))
            print()

    def panel(
        self, content: str, title: str | None = None, style: str = "blue"
    ) -> None:
        """Print a Rich panel.

        Args:
            content: Content to display inside the panel.
            title: Optional panel title.
            style: Panel border style color.
        """
        if self.silent:
            return

        if RICH_AVAILABLE and self.console and Panel:
            panel = Panel(content, title=title, border_style=style)
            self.console.print(panel)
        else:
            # Fallback to plain text box
            width = max(len(line) for line in content.split("\n")) + 4
            if title:
                width = max(width, len(title) + 4)

            print("+" + "-" * (width - 2) + "+")
            if title:
                print(f"| {title.center(width - 4)} |")
                print("+" + "-" * (width - 2) + "+")

            for line in content.split("\n"):
                print(f"| {line.ljust(width - 4)} |")
            print("+" + "-" * (width - 2) + "+")

    def print_styled(self, text: str, style: str = "") -> None:
        """Print text with Rich styling or plain fallback.

        Args:
            text: Text to print.
            style: Rich style string (e.g., "bold green", "red").
        """
        if self.silent:
            return

        if RICH_AVAILABLE and self.console:
            self.console.print(text, style=style)
        else:
            print(text)


class PlainLogger:
    """Plain text logger without colors.

    Used for CI environments where ANSI colors may not be supported
    or may interfere with log parsing.

    Attributes:
        log_file: Optional path to log file for persistent logging.
        silent: If True, suppress all console output.
    """

    def __init__(self, log_file: Path | None = None, silent: bool = False):
        """Initialize PlainLogger.

        Args:
            log_file: Path to log file. If None, only console logging is enabled.
            silent: If True, suppress console output (log to file only).
        """
        self.log_file = log_file
        self.silent = silent

        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)

    def _log(self, level: str, message: str) -> None:
        """Internal logging method."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {level}: {message}"

        if not self.silent:
            print(log_msg)

        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_msg + "\n")
            except Exception:
                pass

    def info(self, message: str) -> None:
        """Log info message."""
        self._log("INFO", message)

    def warn(self, message: str) -> None:
        """Log warning message."""
        self._log("WARN", message)

    def error(self, message: str) -> None:
        """Log error message."""
        self._log("ERROR", message)

    def step(self, message: str) -> None:
        """Log step message."""
        self._log("STEP", message)

    @contextmanager
    def progress_spinner(self, message: str, spinner_style: str = "dots12"):
        """No-op spinner for plain logger.

        Args:
            message: Message to display.
            spinner_style: Ignored in PlainLogger (kept for interface consistency).
        """
        self.step(message)
        yield

    def table(
        self, headers: list[str], rows: list[list[str]], title: str | None = None
    ) -> None:
        """Print a plain text table."""
        if self.silent:
            return

        if title:
            print(f"\n{title}")
            print("=" * len(title))

        header_line = " | ".join(headers)
        print(header_line)
        print("-" * len(header_line))

        for row in rows:
            print(" | ".join(str(cell) for cell in row))
        print()

    def panel(self, content: str, title: str | None = None, style: str = "") -> None:
        """Print content in a plain text box."""
        if self.silent:
            return

        width = max(len(line) for line in content.split("\n")) + 4
        if title:
            width = max(width, len(title) + 4)

        print("+" + "-" * (width - 2) + "+")
        if title:
            print(f"| {title.center(width - 4)} |")
            print("+" + "-" * (width - 2) + "+")

        for line in content.split("\n"):
            print(f"| {line.ljust(width - 4)} |")
        print("+" + "-" * (width - 2) + "+")

    def print_styled(self, text: str, style: str = "") -> None:
        """Print text without styling."""
        if not self.silent:
            print(text)


class SilentLogger:
    """Logger that only writes to file, no console output.

    Used for Claude Code context where JSON output is required
    and console logging would interfere.

    Attributes:
        log_file: Optional path to log file for persistent logging.
    """

    def __init__(self, log_file: Path | None = None):
        """Initialize SilentLogger.

        Args:
            log_file: Path to log file. If None, logging is completely disabled.
        """
        self.log_file = log_file
        self.silent = True

        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)

    def _log(self, level: str, message: str) -> None:
        """Write to log file only."""
        if not self.log_file:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {level}: {message}"

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
        except Exception:
            pass

    def info(self, message: str) -> None:
        """Log info message to file."""
        self._log("INFO", message)

    def warn(self, message: str) -> None:
        """Log warning message to file."""
        self._log("WARN", message)

    def error(self, message: str) -> None:
        """Log error message to file."""
        self._log("ERROR", message)

    def step(self, message: str) -> None:
        """Log step message to file."""
        self._log("STEP", message)

    @contextmanager
    def progress_spinner(self, message: str, spinner_style: str = "dots12"):
        """No-op spinner for silent logger.

        Args:
            message: Message to display.
            spinner_style: Ignored in SilentLogger (kept for interface consistency).
        """
        self._log("STEP", message)
        yield

    def table(
        self, headers: list[str], rows: list[list[str]], title: str | None = None
    ) -> None:
        """No-op table for silent logger."""
        pass

    def panel(self, content: str, title: str | None = None, style: str = "") -> None:
        """No-op panel for silent logger."""
        pass

    def print_styled(self, text: str, style: str = "") -> None:
        """No-op print for silent logger."""
        pass


class ConsoleFactory:
    """Factory for creating appropriate logger based on execution context.

    Uses context_detector to determine the execution environment and
    returns the appropriate logger type:
    - Claude Code context: SilentLogger (JSON output required)
    - CI environment: PlainLogger (no colors, no spinners)
    - Interactive terminal: RichLogger (full Rich features)
    - Rich unavailable: Falls back to ANSI colors in RichLogger
    """

    @staticmethod
    def create_logger(log_file: Path | None = None) -> RichLogger:
        """Create appropriate logger based on execution context.

        Args:
            log_file: Optional path to log file for persistent logging.

        Returns:
            Logger instance appropriate for the current context:
            - SilentLogger for Claude Code context
            - PlainLogger for CI environment
            - RichLogger for interactive terminal
        """
        # Import context detector here to avoid circular imports
        try:
            from scripts.install.context_detector import (
                is_ci_environment,
                is_claude_code_context,
            )
        except ImportError:
            # Fallback for standalone execution
            try:
                from context_detector import is_ci_environment, is_claude_code_context
            except ImportError:
                # If context_detector not available, default to RichLogger
                return RichLogger(log_file=log_file, silent=False)

        # Check context and return appropriate logger
        if is_claude_code_context():
            return SilentLogger(log_file=log_file)  # type: ignore
        elif is_ci_environment():
            return PlainLogger(log_file=log_file, silent=False)  # type: ignore
        else:
            return RichLogger(log_file=log_file, silent=False)

    @staticmethod
    def is_rich_available() -> bool:
        """Check if Rich library is available.

        Returns:
            True if Rich is installed and importable, False otherwise.
        """
        return RICH_AVAILABLE


# Convenience function for styled printing
def print_rich(text: str, style: str = "") -> None:
    """Print text with Rich styling.

    This is a convenience function that uses RichLogger internally.

    Args:
        text: Text to print.
        style: Rich style string (e.g., "bold green", "red").
    """
    logger = RichLogger(silent=False)
    logger.print_styled(text, style)
