"""E2E tests for TestPyPI validation script.

These tests validate that the testpypi_validation.py script works correctly
for CI/CD pipeline integration. Tests that require actual TestPyPI access
are skipped when not running in CI environment.
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Path to the validation script
SCRIPT_PATH = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "testpypi_validation.py"
)


class TestTestPyPIValidationScript:
    """Tests for the testpypi_validation.py script."""

    def test_script_exists(self) -> None:
        """Test that the validation script exists."""
        assert SCRIPT_PATH.exists(), f"Script not found at {SCRIPT_PATH}"

    def test_script_is_executable(self) -> None:
        """Test that the script is executable."""
        assert os.access(SCRIPT_PATH, os.X_OK), "Script is not executable"

    def test_script_has_valid_python_syntax(self) -> None:
        """Test that the script has valid Python syntax."""
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_script_shows_help(self) -> None:
        """Test that the script shows help when --help is passed."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--version" in result.stdout
        assert "--expected-agents" in result.stdout
        assert "--expected-commands" in result.stdout
        assert "--expected-templates" in result.stdout

    def test_script_requires_version_argument(self) -> None:
        """Test that the script requires --version argument."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "version" in result.stderr.lower()

    def test_script_accepts_version_flag(self) -> None:
        """Test that the script accepts --version flag format."""
        # This test verifies the argument parsing works
        # It will fail on actual installation since we're not in CI
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--version",
                "1.3.0.dev20260201001",
            ],
            capture_output=True,
            text=True,
            timeout=30,  # Allow time for subprocess startup + pip on Windows
        )
        # Should either work or fail on installation (not argument parsing)
        # If it fails on argument parsing, returncode would be 2
        assert result.returncode != 2, f"Argument parsing failed: {result.stderr}"

    def test_script_accepts_all_expected_flags(self) -> None:
        """Test that the script accepts all expected component count flags."""
        # Verify argument parsing for all flags
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--version",
                "1.3.0.dev20260201001",
                "--expected-agents",
                "47",
                "--expected-commands",
                "23",
                "--expected-templates",
                "12",
            ],
            capture_output=True,
            text=True,
            timeout=30,  # Allow time for subprocess startup + pip on Windows
        )
        # Should not fail on argument parsing
        assert result.returncode != 2, f"Argument parsing failed: {result.stderr}"


class TestTestPyPIValidatorUnit:
    """Unit tests for TestPyPIValidator class."""

    def test_validator_initialization(self) -> None:
        """Test that TestPyPIValidator initializes correctly."""
        # Import the validator class
        sys.path.insert(0, str(SCRIPT_PATH.parent))
        from testpypi_validation import TestPyPIValidator

        validator = TestPyPIValidator(
            version="1.3.0.dev20260201001",
            expected_agents=47,
            expected_commands=23,
            expected_templates=12,
        )

        assert validator.version == "1.3.0.dev20260201001"
        assert validator.expected_agents == 47
        assert validator.expected_commands == 23
        assert validator.expected_templates == 12
        assert validator.package_name == "nwave"

    def test_validator_default_values(self) -> None:
        """Test that TestPyPIValidator has correct default values."""
        sys.path.insert(0, str(SCRIPT_PATH.parent))
        from testpypi_validation import TestPyPIValidator

        validator = TestPyPIValidator(version="1.0.0")

        assert validator.expected_agents == 0
        assert validator.expected_commands == 0
        assert validator.expected_templates == 0
        assert validator.package_name == "nwave"

    def test_validation_result_dataclass(self) -> None:
        """Test that ValidationResult dataclass works correctly."""
        sys.path.insert(0, str(SCRIPT_PATH.parent))
        from testpypi_validation import ValidationResult

        result = ValidationResult(
            success=True,
            check_name="Test Check",
            expected="expected value",
            actual="actual value",
            message="Test message",
        )

        assert result.success is True
        assert result.check_name == "Test Check"
        assert result.expected == "expected value"
        assert result.actual == "actual value"
        assert result.message == "Test message"


class TestTestPyPIValidationCIIntegration:
    """Integration tests that require CI environment."""

    @pytest.mark.skipif(
        os.getenv("CI") is None,
        reason="Skipping TestPyPI integration test - not running in CI environment",
    )
    def test_full_testpypi_validation(self) -> None:
        """Test full TestPyPI validation in CI environment.

        This test only runs in CI where TestPyPI package is available.
        """
        version = os.getenv("TESTPYPI_VERSION")
        if not version:
            pytest.skip("TESTPYPI_VERSION environment variable not set")

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--version",
                version,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        assert result.returncode == 0, (
            f"TestPyPI validation failed: {result.stdout}\n{result.stderr}"
        )

    @pytest.mark.skipif(
        os.getenv("CI") is None,
        reason="Skipping TestPyPI integration test - not running in CI environment",
    )
    def test_testpypi_validation_with_component_counts(self) -> None:
        """Test TestPyPI validation with expected component counts.

        This test only runs in CI where TestPyPI package is available.
        """
        version = os.getenv("TESTPYPI_VERSION")
        expected_agents = os.getenv("EXPECTED_AGENTS", "0")
        expected_commands = os.getenv("EXPECTED_COMMANDS", "0")
        expected_templates = os.getenv("EXPECTED_TEMPLATES", "0")

        if not version:
            pytest.skip("TESTPYPI_VERSION environment variable not set")

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--version",
                version,
                "--expected-agents",
                expected_agents,
                "--expected-commands",
                expected_commands,
                "--expected-templates",
                expected_templates,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        assert result.returncode == 0, (
            f"TestPyPI validation failed: {result.stdout}\n{result.stderr}"
        )


class TestTestPyPIValidatorMocked:
    """Mocked tests for TestPyPIValidator to test logic without actual installation."""

    def test_version_verification_success(self) -> None:
        """Test version verification logic with mocked subprocess."""
        sys.path.insert(0, str(SCRIPT_PATH.parent))
        from testpypi_validation import TestPyPIValidator

        validator = TestPyPIValidator(version="1.3.0.dev20260201001")

        with patch.object(validator, "run_command") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="nwave 1.3.0.dev20260201001\n",
                stderr="",
            )

            result = validator.verify_version()

            assert result.success is True
            assert "1.3.0.dev20260201001" in result.actual

    def test_version_verification_mismatch(self) -> None:
        """Test version verification fails on mismatch."""
        sys.path.insert(0, str(SCRIPT_PATH.parent))
        from testpypi_validation import TestPyPIValidator

        validator = TestPyPIValidator(version="1.3.0.dev20260201001")

        with patch.object(validator, "run_command") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="nwave 1.2.0\n",
                stderr="",
            )

            result = validator.verify_version()

            assert result.success is False
            assert "mismatch" in result.message.lower()

    def test_health_check_healthy_status(self) -> None:
        """Test health check detection of HEALTHY status."""
        sys.path.insert(0, str(SCRIPT_PATH.parent))
        from testpypi_validation import TestPyPIValidator

        validator = TestPyPIValidator(version="1.3.0.dev20260201001")

        with patch.object(validator, "run_command") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Status: HEALTHY\nAll checks passed.",
                stderr="",
            )

            result = validator.run_health_checks()

            assert result.success is True
            assert (
                "HEALTHY" in result.actual.upper()
                or "healthy" in result.message.lower()
            )

    def test_component_counts_skip_when_zero(self) -> None:
        """Test that component count verification is skipped when expectations are 0."""
        sys.path.insert(0, str(SCRIPT_PATH.parent))
        from testpypi_validation import TestPyPIValidator

        validator = TestPyPIValidator(
            version="1.3.0.dev20260201001",
            expected_agents=0,
            expected_commands=0,
            expected_templates=0,
        )

        result = validator.verify_component_counts()

        assert result.success is True
        assert "skipped" in result.actual.lower()

    def test_install_command_format(self) -> None:
        """Test that install command uses correct TestPyPI URLs."""
        sys.path.insert(0, str(SCRIPT_PATH.parent))
        from testpypi_validation import TestPyPIValidator

        validator = TestPyPIValidator(version="1.3.0.dev20260201001")

        # Verify the URLs are correctly defined
        assert "test.pypi.org" in validator.TESTPYPI_INDEX_URL
        assert "pypi.org" in validator.PYPI_INDEX_URL
