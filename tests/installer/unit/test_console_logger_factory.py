"""Unit tests for rich_console module.

Tests validate RichLogger, PlainLogger, SilentLogger, and ConsoleFactory behavior.
The tests verify correct logger selection based on context, output behavior,
file logging, and graceful fallback when Rich is unavailable.

Test cases follow hexagonal architecture principles - mocking only at port boundaries
(context detection, sys.stdout.isatty, file I/O).
"""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestRichLoggerBasicOutput:
    """Verify RichLogger info/warn/error/step methods output messages correctly."""

    def test_rich_logger_info_outputs_message(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify info() outputs message containing the given text."""
        from scripts.install.rich_console import RichLogger

        logger = RichLogger(log_file=None, silent=False)
        logger.info("Test info message")

        captured = capsys.readouterr()
        assert "INFO" in captured.out
        assert "Test info message" in captured.out

    def test_rich_logger_warn_outputs_message(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify warn() outputs message containing the given text."""
        from scripts.install.rich_console import RichLogger

        logger = RichLogger(log_file=None, silent=False)
        logger.warn("Test warning message")

        captured = capsys.readouterr()
        assert "WARN" in captured.out
        assert "Test warning message" in captured.out

    def test_rich_logger_error_outputs_message(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify error() outputs message containing the given text."""
        from scripts.install.rich_console import RichLogger

        logger = RichLogger(log_file=None, silent=False)
        logger.error("Test error message")

        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "Test error message" in captured.out

    def test_rich_logger_step_outputs_message(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify step() outputs message containing the given text."""
        from scripts.install.rich_console import RichLogger

        logger = RichLogger(log_file=None, silent=False)
        logger.step("Test step message")

        captured = capsys.readouterr()
        assert "STEP" in captured.out
        assert "Test step message" in captured.out


class TestRichLoggerSilentMode:
    """Verify silent mode suppresses console output."""

    def test_rich_logger_silent_mode_suppresses_output(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify silent=True suppresses all console output."""
        from scripts.install.rich_console import RichLogger

        logger = RichLogger(log_file=None, silent=True)
        logger.info("Silent info")
        logger.warn("Silent warning")
        logger.error("Silent error")
        logger.step("Silent step")

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_rich_logger_silent_mode_still_logs_to_file(self, tmp_path: Path) -> None:
        """Verify silent=True still writes to log file."""
        from scripts.install.rich_console import RichLogger

        log_file = tmp_path / "test.log"
        logger = RichLogger(log_file=log_file, silent=True)
        logger.info("Silent file log test")

        log_content = log_file.read_text()
        assert "INFO" in log_content
        assert "Silent file log test" in log_content


class TestRichLoggerFileLogging:
    """Verify RichLogger writes to log file correctly."""

    def test_rich_logger_logs_to_file(self, tmp_path: Path) -> None:
        """Verify messages are written to log file."""
        from scripts.install.rich_console import RichLogger

        log_file = tmp_path / "test.log"
        logger = RichLogger(log_file=log_file, silent=False)

        logger.info("Info message to file")
        logger.warn("Warn message to file")
        logger.error("Error message to file")
        logger.step("Step message to file")

        log_content = log_file.read_text()
        assert "INFO: Info message to file" in log_content
        assert "WARN: Warn message to file" in log_content
        assert "ERROR: Error message to file" in log_content
        assert "STEP: Step message to file" in log_content

    def test_rich_logger_log_file_includes_timestamps(self, tmp_path: Path) -> None:
        """Verify log file entries include timestamps."""
        from scripts.install.rich_console import RichLogger

        log_file = tmp_path / "test.log"
        logger = RichLogger(log_file=log_file, silent=False)
        logger.info("Timestamp test")

        log_content = log_file.read_text()
        # Timestamp format: [YYYY-MM-DD HH:MM:SS]
        assert "[20" in log_content  # Year 20XX


class TestConsoleFactoryContextDetection:
    """Verify ConsoleFactory returns appropriate logger based on context."""

    def test_console_factory_returns_rich_for_terminal(self) -> None:
        """Verify factory returns RichLogger for interactive terminal (TTY)."""
        from scripts.install.rich_console import ConsoleFactory, RichLogger

        # Mock at context_detector module level since it's imported dynamically
        with (
            patch(
                "scripts.install.context_detector.is_claude_code_context",
                return_value=False,
            ),
            patch(
                "scripts.install.context_detector.is_ci_environment", return_value=False
            ),
        ):
            logger = ConsoleFactory.create_logger()
            assert isinstance(logger, RichLogger)

    def test_console_factory_returns_plain_for_ci(self) -> None:
        """Verify factory returns PlainLogger for CI environment."""
        from scripts.install.rich_console import ConsoleFactory, PlainLogger

        # Mock at context_detector module level since it's imported dynamically
        with (
            patch(
                "scripts.install.context_detector.is_claude_code_context",
                return_value=False,
            ),
            patch(
                "scripts.install.context_detector.is_ci_environment", return_value=True
            ),
        ):
            logger = ConsoleFactory.create_logger()
            assert isinstance(logger, PlainLogger)

    def test_console_factory_returns_silent_for_claude(self) -> None:
        """Verify factory returns SilentLogger for Claude Code context."""
        from scripts.install.rich_console import ConsoleFactory, SilentLogger

        # Mock at context_detector module level since it's imported dynamically
        with patch(
            "scripts.install.context_detector.is_claude_code_context", return_value=True
        ):
            logger = ConsoleFactory.create_logger()
            assert isinstance(logger, SilentLogger)


class TestRichFallback:
    """Verify graceful fallback when Rich is unavailable."""

    def test_rich_logger_fallback_when_rich_unavailable(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify RichLogger falls back to ANSI colors when Rich unavailable."""
        from scripts.install import rich_console

        # Save original state
        original_rich_available = rich_console.RICH_AVAILABLE

        try:
            # Simulate Rich being unavailable
            rich_console.RICH_AVAILABLE = False

            # Create a new logger instance that will use the fallback
            logger = rich_console.RichLogger(log_file=None, silent=False)
            logger.console = None  # Force fallback path

            logger.info("Fallback test message")

            captured = capsys.readouterr()
            # Should still output the message (with or without ANSI codes)
            assert "INFO" in captured.out
            assert "Fallback test message" in captured.out
        finally:
            # Restore original state
            rich_console.RICH_AVAILABLE = original_rich_available

    def test_console_factory_is_rich_available(self) -> None:
        """Verify ConsoleFactory.is_rich_available() returns boolean."""
        from scripts.install.rich_console import ConsoleFactory

        result = ConsoleFactory.is_rich_available()
        assert isinstance(result, bool)


class TestPlainLoggerOutput:
    """Verify PlainLogger outputs without ANSI codes in CI environments."""

    def test_plain_logger_outputs_without_ansi_in_ci(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify PlainLogger has no ANSI escape codes in output."""
        from scripts.install.rich_console import PlainLogger

        logger = PlainLogger(log_file=None, silent=False)
        logger.info("Plain info message")
        logger.warn("Plain warning message")
        logger.error("Plain error message")

        captured = capsys.readouterr()
        # PlainLogger should not contain ANSI escape sequences
        assert "\033[" not in captured.out
        # But should contain the messages
        assert "INFO" in captured.out
        assert "WARN" in captured.out
        assert "ERROR" in captured.out

    def test_plain_logger_includes_timestamps(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify PlainLogger includes timestamps in output."""
        from scripts.install.rich_console import PlainLogger

        logger = PlainLogger(log_file=None, silent=False)
        logger.info("Timestamp test")

        captured = capsys.readouterr()
        # Timestamp format: [YYYY-MM-DD HH:MM:SS]
        assert "[20" in captured.out


class TestSilentLoggerBehavior:
    """Verify SilentLogger produces no console output."""

    def test_silent_logger_no_console_output(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify SilentLogger doesn't print to console."""
        from scripts.install.rich_console import SilentLogger

        logger = SilentLogger(log_file=None)
        logger.info("Should not appear")
        logger.warn("Should not appear")
        logger.error("Should not appear")
        logger.step("Should not appear")

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_silent_logger_table_produces_no_output(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify SilentLogger.table() produces no output."""
        from scripts.install.rich_console import SilentLogger

        logger = SilentLogger(log_file=None)
        logger.table(["Col1", "Col2"], [["a", "b"], ["c", "d"]], title="Test")

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_silent_logger_panel_produces_no_output(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify SilentLogger.panel() produces no output."""
        from scripts.install.rich_console import SilentLogger

        logger = SilentLogger(log_file=None)
        logger.panel("Panel content", title="Panel Title")

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_silent_logger_writes_to_file(self, tmp_path: Path) -> None:
        """Verify SilentLogger writes to log file when specified."""
        from scripts.install.rich_console import SilentLogger

        log_file = tmp_path / "silent.log"
        logger = SilentLogger(log_file=log_file)

        logger.info("Silent file test")
        logger.error("Silent error test")

        log_content = log_file.read_text()
        assert "INFO: Silent file test" in log_content
        assert "ERROR: Silent error test" in log_content


class TestRichLoggerProgressSpinner:
    """Verify progress spinner context manager behavior."""

    def test_progress_spinner_executes_block(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify progress_spinner context manager executes the code block."""
        from scripts.install.rich_console import RichLogger

        logger = RichLogger(log_file=None, silent=False)
        executed = False

        with logger.progress_spinner("Processing..."):
            executed = True

        assert executed is True

    def test_progress_spinner_in_silent_mode(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify progress_spinner works in silent mode without error."""
        from scripts.install.rich_console import RichLogger

        logger = RichLogger(log_file=None, silent=True)
        executed = False

        with logger.progress_spinner("Silent spinner"):
            executed = True

        assert executed is True
        captured = capsys.readouterr()
        assert captured.out == ""


class TestRichLoggerTableAndPanel:
    """Verify table and panel output methods."""

    def test_table_outputs_headers_and_rows(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Verify table() outputs headers and row data."""
        from scripts.install.rich_console import RichLogger

        logger = RichLogger(log_file=None, silent=False)
        logger.table(
            headers=["Name", "Status"],
            rows=[["Item1", "OK"], ["Item2", "FAIL"]],
            title="Test Table",
        )

        captured = capsys.readouterr()
        assert "Name" in captured.out
        assert "Status" in captured.out
        assert "Item1" in captured.out
        assert "OK" in captured.out

    def test_panel_outputs_content(self, capsys: pytest.CaptureFixture) -> None:
        """Verify panel() outputs content."""
        from scripts.install.rich_console import RichLogger

        logger = RichLogger(log_file=None, silent=False)
        logger.panel("Panel content here", title="Test Panel")

        captured = capsys.readouterr()
        assert "Panel content here" in captured.out

    def test_table_silent_mode(self, capsys: pytest.CaptureFixture) -> None:
        """Verify table() produces no output in silent mode."""
        from scripts.install.rich_console import RichLogger

        logger = RichLogger(log_file=None, silent=True)
        logger.table(
            headers=["A", "B"],
            rows=[["1", "2"]],
        )

        captured = capsys.readouterr()
        assert captured.out == ""


class TestPlainLoggerTableAndPanel:
    """Verify PlainLogger table and panel output."""

    def test_plain_logger_table_output(self, capsys: pytest.CaptureFixture) -> None:
        """Verify PlainLogger.table() outputs plain text table."""
        from scripts.install.rich_console import PlainLogger

        logger = PlainLogger(log_file=None, silent=False)
        logger.table(headers=["Col1", "Col2"], rows=[["a", "b"]], title="Plain Table")

        captured = capsys.readouterr()
        assert "Col1" in captured.out
        assert "Col2" in captured.out
        assert "a" in captured.out

    def test_plain_logger_panel_output(self, capsys: pytest.CaptureFixture) -> None:
        """Verify PlainLogger.panel() outputs plain text box."""
        from scripts.install.rich_console import PlainLogger

        logger = PlainLogger(log_file=None, silent=False)
        logger.panel("Box content", title="Box Title")

        captured = capsys.readouterr()
        assert "Box content" in captured.out
        assert "+" in captured.out  # Box border character


class TestPrintRichConvenienceFunction:
    """Verify the print_rich convenience function."""

    def test_print_rich_outputs_text(self, capsys: pytest.CaptureFixture) -> None:
        """Verify print_rich() outputs the given text."""
        from scripts.install.rich_console import print_rich

        print_rich("Convenience function test", style="green")

        captured = capsys.readouterr()
        assert "Convenience function test" in captured.out
