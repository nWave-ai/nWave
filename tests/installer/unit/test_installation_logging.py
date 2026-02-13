"""
Unit tests for Installation Logging (Step 05-02).

CRITICAL: Tests follow hexagonal architecture - port boundaries only for mocks.
These tests validate comprehensive logging integration into installer and verifier:
- Log file is created at standard location (~/.claude/nwave-install.log)
- Successful actions are logged with timestamp
- Errors are logged with detail
- Preflight check results are logged
- Log persists across installation attempts (append mode)
- Log format is parseable

Step 05-02: Installation Logging
"""

import re
from datetime import datetime


class TestLogFileLocation:
    """Test log file creation at standard location."""

    def test_log_file_is_created_at_standard_location(self, tmp_path):
        """
        GIVEN: The Logger is initialized with a log file path
        WHEN: A log message is written
        THEN: The log file is created at the specified location

        Acceptance Criteria: Log file is created at standard location
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / ".claude" / "nwave-install.log"

        # ACT
        logger = Logger(log_file=log_file)
        logger.info("Test message")

        # ASSERT
        assert log_file.exists(), "Log file should be created at the specified location"

    def test_log_file_parent_directory_created_automatically(self, tmp_path):
        """
        GIVEN: The log file path has non-existent parent directories
        WHEN: Logger is initialized
        THEN: Parent directories are created automatically
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / ".claude" / "nested" / "nwave-install.log"
        assert not log_file.parent.exists()

        # ACT
        logger = Logger(log_file=log_file)
        logger.info("Test message")

        # ASSERT
        assert log_file.parent.exists(), "Parent directories should be created"
        assert log_file.exists(), "Log file should be created"


class TestLogTimestampFormat:
    """Test successful actions are logged with timestamp."""

    def test_successful_actions_are_logged_with_timestamp(self, tmp_path):
        """
        GIVEN: A Logger with a log file
        WHEN: An info message is logged
        THEN: The log entry includes a timestamp in ISO format

        Acceptance Criteria: Successful actions are logged with timestamp
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file)

        # ACT
        logger.info("Installation started")

        # ASSERT
        log_content = log_file.read_text()
        # Timestamp pattern: [YYYY-MM-DD HH:MM:SS]
        timestamp_pattern = r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]"
        assert re.search(timestamp_pattern, log_content), (
            f"Log should contain timestamp. Content: {log_content}"
        )

    def test_log_timestamp_is_current_time(self, tmp_path):
        """
        GIVEN: A Logger with a log file
        WHEN: A message is logged
        THEN: The timestamp reflects the current time (within 2 second tolerance)
        """
        from datetime import timedelta

        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file)
        before_time = datetime.now()

        # ACT
        logger.info("Test message")

        # ASSERT
        log_content = log_file.read_text()
        # Extract timestamp from log
        match = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", log_content)
        assert match, "Log should contain timestamp"
        log_time = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
        after_time = datetime.now()
        # Allow 2 second tolerance due to second truncation in log format
        tolerance = timedelta(seconds=2)
        assert (before_time - tolerance) <= log_time <= (after_time + tolerance), (
            f"Timestamp should be current. before={before_time}, log={log_time}, after={after_time}"
        )


class TestLogLevelInfo:
    """Test INFO level logging."""

    def test_info_level_logged_correctly(self, tmp_path):
        """
        GIVEN: A Logger with a log file
        WHEN: logger.info() is called
        THEN: The log entry shows INFO level
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file)

        # ACT
        logger.info("Build completed successfully")

        # ASSERT
        log_content = log_file.read_text()
        assert "INFO" in log_content, "Log should contain INFO level"
        assert "Build completed successfully" in log_content


class TestLogLevelError:
    """Test ERROR level logging."""

    def test_errors_are_logged_with_detail(self, tmp_path):
        """
        GIVEN: A Logger with a log file
        WHEN: logger.error() is called with an error message
        THEN: The log entry shows ERROR level and includes the detail

        Acceptance Criteria: Errors are logged with detail
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file)
        error_message = "Build failed: Missing dependency xyz"

        # ACT
        logger.error(error_message)

        # ASSERT
        log_content = log_file.read_text()
        assert "ERROR" in log_content, "Log should contain ERROR level"
        assert error_message in log_content, "Log should contain error detail"

    def test_warn_level_logged_correctly(self, tmp_path):
        """
        GIVEN: A Logger with a log file
        WHEN: logger.warn() is called
        THEN: The log entry shows WARN level
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file)

        # ACT
        logger.warn("Expected 10+ agents, found 8")

        # ASSERT
        log_content = log_file.read_text()
        assert "WARN" in log_content, "Log should contain WARN level"


class TestLogPreflightResults:
    """Test preflight check results logging."""

    def test_preflight_check_results_are_logged(self, tmp_path, capsys):
        """
        GIVEN: The installer runs preflight checks
        WHEN: Preflight checks complete
        THEN: Results are logged (pass/fail status for each check)

        Acceptance Criteria: Pre-flight check results are logged
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file)

        # ACT - Simulate logging preflight results
        logger.info("Preflight check: Virtual environment - PASSED")
        logger.info("Preflight check: Python version - PASSED")
        logger.warn("Preflight check: Optional dependency - SKIPPED")

        # ASSERT
        log_content = log_file.read_text()
        assert "Preflight check" in log_content
        assert "Virtual environment" in log_content or "PASSED" in log_content


class TestLogPersistence:
    """Test log persistence across installation attempts."""

    def test_log_persists_across_installation_attempts(self, tmp_path):
        """
        GIVEN: A log file with existing content
        WHEN: Logger writes new messages
        THEN: New messages are appended, existing content preserved

        Acceptance Criteria: Log persists across installation attempts
        """
        from scripts.install.install_utils import Logger

        # ARRANGE - Create initial log content
        log_file = tmp_path / "test.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("[2025-01-28 10:00:00] INFO: First installation attempt\n")

        # ACT - Create new logger and write
        logger = Logger(log_file=log_file)
        logger.info("Second installation attempt")

        # ASSERT
        log_content = log_file.read_text()
        assert "First installation attempt" in log_content, (
            "Old log should be preserved"
        )
        assert "Second installation attempt" in log_content, (
            "New log should be appended"
        )

    def test_multiple_log_entries_preserved(self, tmp_path):
        """
        GIVEN: Multiple installation attempts
        WHEN: Each attempt logs messages
        THEN: All log entries are preserved in chronological order
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"

        # ACT - Simulate multiple installation attempts
        for i in range(3):
            logger = Logger(log_file=log_file)
            logger.info(f"Installation attempt {i + 1}")

        # ASSERT
        log_content = log_file.read_text()
        assert "Installation attempt 1" in log_content
        assert "Installation attempt 2" in log_content
        assert "Installation attempt 3" in log_content


class TestLogFormatParseable:
    """Test log format is parseable."""

    def test_log_format_is_parseable(self, tmp_path):
        """
        GIVEN: A log file with multiple entries
        WHEN: The log content is parsed
        THEN: Each line follows the format: [TIMESTAMP] LEVEL: MESSAGE

        Acceptance Criteria: Log format is parseable
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file)

        # ACT
        logger.info("Test info message")
        logger.warn("Test warning message")
        logger.error("Test error message")

        # ASSERT
        log_content = log_file.read_text()
        lines = log_content.strip().split("\n")

        # Pattern: [YYYY-MM-DD HH:MM:SS] LEVEL: MESSAGE
        log_pattern = (
            r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] (INFO|WARN|ERROR|STEP): .+$"
        )

        for line in lines:
            assert re.match(log_pattern, line), (
                f"Log line does not match expected format: {line}"
            )

    def test_log_entries_can_be_parsed_into_components(self, tmp_path):
        """
        GIVEN: A log file with entries
        WHEN: Log content is parsed programmatically
        THEN: Timestamp, level, and message can be extracted separately
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file)
        logger.info("Test message for parsing")

        # ACT
        log_content = log_file.read_text().strip()
        # Parse format: [YYYY-MM-DD HH:MM:SS] LEVEL: MESSAGE
        match = re.match(
            r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (\w+): (.+)$", log_content
        )

        # ASSERT
        assert match is not None, "Log entry should be parseable"
        timestamp, level, message = match.groups()
        assert timestamp, "Timestamp should be extracted"
        assert level == "INFO", "Level should be INFO"
        assert message == "Test message for parsing", "Message should be extracted"


class TestNWaveInstallerLogging:
    """Test NWaveInstaller uses logging appropriately."""

    def test_installer_creates_log_file_at_config_directory(
        self, tmp_path, monkeypatch
    ):
        """
        GIVEN: NWaveInstaller is instantiated
        WHEN: Not in dry-run mode
        THEN: Logger is configured with log file in claude config directory
        """
        from scripts.install.install_nwave import NWaveInstaller
        from scripts.install.install_utils import PathUtils

        # ARRANGE - Mock the config directory
        def mock_get_claude_config_dir():
            return tmp_path / ".claude"

        monkeypatch.setattr(
            PathUtils, "get_claude_config_dir", mock_get_claude_config_dir
        )

        # ACT
        installer = NWaveInstaller(dry_run=False)

        # ASSERT
        assert installer.logger.log_file is not None
        expected_log_path = tmp_path / ".claude" / "nwave-install.log"
        assert installer.logger.log_file == expected_log_path

    def test_installer_dry_run_does_not_create_log_file(self, tmp_path, monkeypatch):
        """
        GIVEN: NWaveInstaller is instantiated in dry-run mode
        WHEN: Logging operations occur
        THEN: No log file is created (only console output)
        """
        from scripts.install.install_nwave import NWaveInstaller
        from scripts.install.install_utils import PathUtils

        # ARRANGE
        def mock_get_claude_config_dir():
            return tmp_path / ".claude"

        monkeypatch.setattr(
            PathUtils, "get_claude_config_dir", mock_get_claude_config_dir
        )

        # ACT
        installer = NWaveInstaller(dry_run=True)

        # ASSERT
        assert installer.logger.log_file is None


class TestVerifyNwaveLogging:
    """Test verify_nwave.py uses logging appropriately."""

    def test_verification_result_can_be_logged(self, tmp_path):
        """
        GIVEN: A verification result
        WHEN: Result is logged
        THEN: All verification details are captured in log
        """
        from scripts.install.install_utils import Logger
        from scripts.install.installation_verifier import VerificationResult

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file)

        result = VerificationResult(
            success=True,
            agent_file_count=41,
            command_file_count=25,
            manifest_exists=True,
            missing_essential_files=[],
            error_code=None,
            message="Verification completed successfully.",
        )

        # ACT - Log verification details
        logger.info(f"Verification result: success={result.success}")
        logger.info(f"Agent files: {result.agent_file_count}")
        logger.info(f"Command files: {result.command_file_count}")

        # ASSERT
        log_content = log_file.read_text()
        assert "success=True" in log_content
        assert "41" in log_content
        assert "25" in log_content

    def test_verify_nwave_logs_to_installation_log(self, tmp_path, monkeypatch):
        """
        GIVEN: verify_nwave.py is executed
        WHEN: Verification runs
        THEN: Results are logged to ~/.claude/nwave-install.log

        This ensures verification outcomes are captured in the shared log file.
        """
        from scripts.install.install_utils import PathUtils
        from scripts.install.verify_nwave import main

        # ARRANGE
        config_dir = tmp_path / ".claude"
        commands_dir = config_dir / "commands" / "nw"
        agents_dir = config_dir / "agents" / "nw"
        skills_dir = config_dir / "skills" / "nw" / "researcher"
        des_dir = config_dir / "lib" / "python" / "des"
        commands_dir.mkdir(parents=True)
        agents_dir.mkdir(parents=True)
        skills_dir.mkdir(parents=True)
        des_dir.mkdir(parents=True)

        # Create essential files
        essential_files = [
            "commit.md",
            "review.md",
            "devops.md",
            "discuss.md",
            "design.md",
            "distill.md",
            "deliver.md",
        ]
        for f in essential_files:
            (commands_dir / f).write_text(f"# {f}")

        # Create skills and DES files for verification
        (skills_dir / "research-methodology.md").write_text("# skill")
        (des_dir / "__init__.py").write_text("")

        # Create manifest
        (config_dir / "nwave-manifest.txt").write_text("Manifest")

        def mock_get_claude_config_dir():
            return config_dir

        monkeypatch.setattr(
            PathUtils, "get_claude_config_dir", mock_get_claude_config_dir
        )

        # ACT
        exit_code = main(args=["--verbose"], claude_config_dir=config_dir)

        # ASSERT
        log_file = config_dir / "nwave-install.log"
        assert exit_code == 0
        assert log_file.exists(), "Log file should be created during verification"
        log_content = log_file.read_text()
        assert "Verification" in log_content or "verification" in log_content.lower()


class TestLoggerStepMethod:
    """Test Logger step() method for tracking build steps."""

    def test_step_method_logs_with_step_level(self, tmp_path):
        """
        GIVEN: A Logger with a log file
        WHEN: logger.step() is called
        THEN: The log entry shows STEP level
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file)

        # ACT
        logger.step("Building IDE bundle")

        # ASSERT
        log_content = log_file.read_text()
        assert "STEP" in log_content
        assert "Building IDE bundle" in log_content


class TestLoggerWithoutFile:
    """Test Logger behavior when no file is specified."""

    def test_logger_without_file_only_prints_to_console(self, capsys):
        """
        GIVEN: A Logger without a log file
        WHEN: Messages are logged
        THEN: Output goes to console only
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        logger = Logger(log_file=None)

        # ACT
        logger.info("Console only message")

        # ASSERT
        captured = capsys.readouterr()
        assert "Console only message" in captured.out


class TestLoggerSilentMode:
    """Test Logger silent mode for JSON output compatibility."""

    def test_logger_silent_mode_logs_to_file_only(self, tmp_path, capsys):
        """
        GIVEN: A Logger in silent mode with a log file
        WHEN: Messages are logged
        THEN: Output goes to file only, not console
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file, silent=True)

        # ACT
        logger.info("Silent message")

        # ASSERT
        captured = capsys.readouterr()
        assert "Silent message" not in captured.out, "Console should be silent"
        assert log_file.exists(), "Log file should be created"
        assert "Silent message" in log_file.read_text(), "Message should be in log file"

    def test_logger_silent_mode_logs_all_levels_to_file(self, tmp_path, capsys):
        """
        GIVEN: A Logger in silent mode
        WHEN: Different log levels are used
        THEN: All levels are written to file, none to console
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file, silent=True)

        # ACT
        logger.info("Info message")
        logger.warn("Warning message")
        logger.error("Error message")
        logger.step("Step message")

        # ASSERT
        captured = capsys.readouterr()
        assert captured.out == "", "Console should have no output in silent mode"

        log_content = log_file.read_text()
        assert "INFO: Info message" in log_content
        assert "WARN: Warning message" in log_content
        assert "ERROR: Error message" in log_content
        assert "STEP: Step message" in log_content

    def test_logger_non_silent_mode_logs_to_both(self, tmp_path, capsys):
        """
        GIVEN: A Logger NOT in silent mode with a log file
        WHEN: Messages are logged
        THEN: Output goes to both console and file
        """
        from scripts.install.install_utils import Logger

        # ARRANGE
        log_file = tmp_path / "test.log"
        logger = Logger(log_file=log_file, silent=False)

        # ACT
        logger.info("Normal message")

        # ASSERT
        captured = capsys.readouterr()
        assert "Normal message" in captured.out, "Console should have output"
        assert "Normal message" in log_file.read_text(), "File should have message"
