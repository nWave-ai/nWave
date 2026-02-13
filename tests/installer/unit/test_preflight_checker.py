"""
Unit tests for preflight_checker module.

CRITICAL: Tests follow hexagonal architecture - domain classes use real objects.
These tests validate virtual environment detection and preflight check orchestration.
"""

import sys
from unittest.mock import patch

from scripts.install.error_codes import ENV_NO_VENV
from scripts.install.preflight_checker import (
    CheckResult,
    PreflightChecker,
    VirtualEnvironmentCheck,
    is_virtual_environment,
)


class TestIsVirtualEnvironment:
    """Test virtual environment detection function."""

    def test_is_virtual_environment_returns_true_when_in_venv(self):
        """
        GIVEN: sys.prefix differs from sys.base_prefix (venv active)
        WHEN: is_virtual_environment() is called
        THEN: Returns True
        """
        # ARRANGE
        with patch.object(sys, "prefix", "/path/to/venv"):
            with patch.object(sys, "base_prefix", "/usr/local/python"):
                # ACT
                result = is_virtual_environment()

                # ASSERT
                assert result is True

    def test_is_virtual_environment_returns_false_when_not_in_venv(self):
        """
        GIVEN: sys.prefix equals sys.base_prefix (no venv)
        WHEN: is_virtual_environment() is called
        THEN: Returns False
        """
        # ARRANGE
        same_path = "/usr/local/python"
        with patch.object(sys, "prefix", same_path):
            with patch.object(sys, "base_prefix", same_path):
                # ACT
                result = is_virtual_environment()

                # ASSERT
                assert result is False


class TestCheckResult:
    """Test CheckResult dataclass."""

    def test_check_result_success_has_no_error_code(self):
        """
        GIVEN: A successful check
        WHEN: CheckResult is created
        THEN: passed is True, error_code is None, remediation is None
        """
        # ACT
        result = CheckResult(
            passed=True,
            error_code=None,
            message="Check passed successfully.",
            remediation=None,
        )

        # ASSERT
        assert result.passed is True
        assert result.error_code is None
        assert result.message == "Check passed successfully."
        assert result.remediation is None

    def test_check_result_failure_has_error_code_and_remediation(self):
        """
        GIVEN: A failed check
        WHEN: CheckResult is created with error details
        THEN: passed is False, error_code and remediation are set
        """
        # ACT
        result = CheckResult(
            passed=False,
            error_code=ENV_NO_VENV,
            message="Not in virtual environment.",
            remediation="Create a virtual environment first.",
        )

        # ASSERT
        assert result.passed is False
        assert result.error_code == ENV_NO_VENV
        assert result.message == "Not in virtual environment."
        assert result.remediation == "Create a virtual environment first."


class TestVirtualEnvironmentCheck:
    """Test VirtualEnvironmentCheck class."""

    def test_virtual_environment_check_passes_when_in_venv(self):
        """
        GIVEN: Running inside a virtual environment
        WHEN: VirtualEnvironmentCheck.run() is called
        THEN: Returns CheckResult with passed=True
        """
        # ARRANGE
        check = VirtualEnvironmentCheck()

        with patch.object(sys, "prefix", "/path/to/venv"):
            with patch.object(sys, "base_prefix", "/usr/local/python"):
                # ACT
                result = check.run()

                # ASSERT
                assert result.passed is True
                assert result.error_code is None
                assert "detected" in result.message.lower()
                assert result.remediation is None

    def test_virtual_environment_check_fails_when_not_in_venv(self):
        """
        GIVEN: Running outside a virtual environment
        WHEN: VirtualEnvironmentCheck.run() is called
        THEN: Returns CheckResult with passed=False and ENV_NO_VENV error
        """
        # ARRANGE
        check = VirtualEnvironmentCheck()
        same_path = "/usr/local/python"

        with patch.object(sys, "prefix", same_path):
            with patch.object(sys, "base_prefix", same_path):
                # ACT
                result = check.run()

                # ASSERT
                assert result.passed is False
                assert result.error_code == ENV_NO_VENV
                assert "not running in a virtual environment" in result.message.lower()
                assert result.remediation is not None
                assert "venv" in result.remediation.lower()


class TestPreflightChecker:
    """Test PreflightChecker orchestration class."""

    def test_run_preflight_checks_returns_results_list(self):
        """
        GIVEN: A PreflightChecker instance
        WHEN: run_all_checks() is called
        THEN: Returns a list of CheckResult objects
        """
        # ARRANGE
        checker = PreflightChecker()

        with patch.object(sys, "prefix", "/path/to/venv"):
            with patch.object(sys, "base_prefix", "/usr/local/python"):
                # ACT
                results = checker.run_all_checks()

                # ASSERT
                assert isinstance(results, list)
                assert len(results) > 0
                assert all(isinstance(r, CheckResult) for r in results)

    def test_skip_checks_flag_does_not_bypass_venv_check(self):
        """
        GIVEN: Running outside a virtual environment with skip_checks=True
        WHEN: run_all_checks(skip_checks=True) is called
        THEN: Virtual environment check still runs and fails

        NOTE: This is a CRITICAL test. Virtual environment check is a hard
        requirement that CANNOT be bypassed. This is a safety measure to
        prevent system Python pollution.
        """
        # ARRANGE
        checker = PreflightChecker()
        same_path = "/usr/local/python"

        with patch.object(sys, "prefix", same_path):
            with patch.object(sys, "base_prefix", same_path):
                # ACT
                results = checker.run_all_checks(skip_checks=True)

                # ASSERT
                assert len(results) > 0
                venv_result = results[0]  # Virtual env check is always first
                assert venv_result.passed is False
                assert venv_result.error_code == ENV_NO_VENV

    def test_has_blocking_failures_returns_true_when_check_fails(self):
        """
        GIVEN: A list of results with at least one failure
        WHEN: has_blocking_failures() is called
        THEN: Returns True
        """
        # ARRANGE
        checker = PreflightChecker()
        results = [
            CheckResult(passed=True, error_code=None, message="OK", remediation=None),
            CheckResult(
                passed=False,
                error_code=ENV_NO_VENV,
                message="Failed",
                remediation="Fix it",
            ),
        ]

        # ACT
        has_failures = checker.has_blocking_failures(results)

        # ASSERT
        assert has_failures is True

    def test_has_blocking_failures_returns_false_when_all_pass(self):
        """
        GIVEN: A list of results where all checks passed
        WHEN: has_blocking_failures() is called
        THEN: Returns False
        """
        # ARRANGE
        checker = PreflightChecker()
        results = [
            CheckResult(passed=True, error_code=None, message="OK", remediation=None),
            CheckResult(passed=True, error_code=None, message="OK", remediation=None),
        ]

        # ACT
        has_failures = checker.has_blocking_failures(results)

        # ASSERT
        assert has_failures is False

    def test_get_failed_checks_returns_only_failures(self):
        """
        GIVEN: A list of mixed pass/fail results
        WHEN: get_failed_checks() is called
        THEN: Returns only the failed CheckResult objects
        """
        # ARRANGE
        checker = PreflightChecker()
        passed_result = CheckResult(
            passed=True, error_code=None, message="OK", remediation=None
        )
        failed_result = CheckResult(
            passed=False,
            error_code=ENV_NO_VENV,
            message="Failed",
            remediation="Fix it",
        )
        results = [passed_result, failed_result]

        # ACT
        failed = checker.get_failed_checks(results)

        # ASSERT
        assert len(failed) == 1
        assert failed[0] is failed_result
        assert failed[0].passed is False

    def test_run_all_checks_orchestration_in_venv(self):
        """
        GIVEN: Running inside a virtual environment
        WHEN: run_all_checks() is called
        THEN: All checks pass and has_blocking_failures returns False
        """
        # ARRANGE
        checker = PreflightChecker()

        with patch.object(sys, "prefix", "/path/to/venv"):
            with patch.object(sys, "base_prefix", "/usr/local/python"):
                # ACT
                results = checker.run_all_checks()

                # ASSERT
                assert checker.has_blocking_failures(results) is False
                assert len(checker.get_failed_checks(results)) == 0

    def test_run_all_checks_orchestration_not_in_venv(self):
        """
        GIVEN: Running outside a virtual environment
        WHEN: run_all_checks() is called
        THEN: Virtual environment check fails and has_blocking_failures returns True
        """
        # ARRANGE
        checker = PreflightChecker()
        same_path = "/usr/local/python"

        with patch.object(sys, "prefix", same_path):
            with patch.object(sys, "base_prefix", same_path):
                # ACT
                results = checker.run_all_checks()

                # ASSERT
                assert checker.has_blocking_failures(results) is True
                failed = checker.get_failed_checks(results)
                assert len(failed) == 1
                assert failed[0].error_code == ENV_NO_VENV
