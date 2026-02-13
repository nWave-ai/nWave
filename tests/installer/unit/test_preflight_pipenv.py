"""
Unit tests for PipenvCheck in preflight_checker module.

CRITICAL: Tests follow hexagonal architecture - domain classes use real objects.
shutil.which is a PORT BOUNDARY and may be mocked per test_doubles_policy.

These tests validate pipenv availability detection and error messaging.
Error messages must ONLY reference pipenv - NO mentions of pip, poetry, or conda.
"""

from unittest.mock import patch

from scripts.install.error_codes import ENV_NO_PIPENV
from scripts.install.preflight_checker import PipenvCheck


class TestPipenvCheck:
    """Test PipenvCheck class for pipenv availability detection."""

    def test_check_pipenv_available_when_installed(self):
        """
        GIVEN: pipenv is installed and available on PATH
        WHEN: PipenvCheck.run() is called
        THEN: Returns CheckResult with passed=True
        """
        # ARRANGE
        check = PipenvCheck()

        # Mock shutil.which at PORT BOUNDARY (allowed per test_doubles_policy)
        with patch("scripts.install.preflight_checker.shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/pipenv"

            # ACT
            result = check.run()

            # ASSERT
            assert result.passed is True
            assert result.error_code is None
            assert "pipenv" in result.message.lower()
            assert result.remediation is None

    def test_check_pipenv_available_when_not_installed(self):
        """
        GIVEN: pipenv is NOT installed (shutil.which returns None)
        WHEN: PipenvCheck.run() is called
        THEN: Returns CheckResult with passed=False and ENV_NO_PIPENV error
        """
        # ARRANGE
        check = PipenvCheck()

        # Mock shutil.which at PORT BOUNDARY (allowed per test_doubles_policy)
        with patch("scripts.install.preflight_checker.shutil.which") as mock_which:
            mock_which.return_value = None

            # ACT
            result = check.run()

            # ASSERT
            assert result.passed is False
            assert result.error_code == ENV_NO_PIPENV
            assert "pipenv" in result.message.lower()
            assert result.remediation is not None

    def test_pipenv_error_message_no_pip_mention(self):
        """
        GIVEN: pipenv is NOT installed
        WHEN: PipenvCheck.run() returns failure
        THEN: Error message and remediation do NOT mention pip

        CRITICAL: nWave enforces pipenv-only policy. Error messages must not
        suggest pip as an alternative to avoid user confusion.
        """
        # ARRANGE
        check = PipenvCheck()

        with patch("scripts.install.preflight_checker.shutil.which") as mock_which:
            mock_which.return_value = None

            # ACT
            result = check.run()

            # ASSERT
            error_text = (result.message + " " + (result.remediation or "")).lower()
            # "pip " with space to avoid matching "pipenv"
            assert "pip " not in error_text
            assert "pip install" not in error_text

    def test_pipenv_error_message_no_poetry_mention(self):
        """
        GIVEN: pipenv is NOT installed
        WHEN: PipenvCheck.run() returns failure
        THEN: Error message and remediation do NOT mention poetry

        CRITICAL: nWave enforces pipenv-only policy. Error messages must not
        suggest poetry as an alternative.
        """
        # ARRANGE
        check = PipenvCheck()

        with patch("scripts.install.preflight_checker.shutil.which") as mock_which:
            mock_which.return_value = None

            # ACT
            result = check.run()

            # ASSERT
            error_text = (result.message + " " + (result.remediation or "")).lower()
            assert "poetry" not in error_text

    def test_pipenv_installation_guidance(self):
        """
        GIVEN: pipenv is NOT installed
        WHEN: PipenvCheck.run() returns failure
        THEN: Remediation provides actionable pipenv installation guidance

        The guidance must include:
        - How to install pipenv
        - Reference to pipenv official documentation
        """
        # ARRANGE
        check = PipenvCheck()

        with patch("scripts.install.preflight_checker.shutil.which") as mock_which:
            mock_which.return_value = None

            # ACT
            result = check.run()

            # ASSERT
            assert result.remediation is not None
            remediation_lower = result.remediation.lower()
            # Must provide pipenv installation command
            assert "pipenv" in remediation_lower
            # Must provide installation method
            assert "install" in remediation_lower
