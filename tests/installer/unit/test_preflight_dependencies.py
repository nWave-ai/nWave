"""
Unit tests for DependencyCheck in preflight_checker module.

CRITICAL: Tests follow hexagonal architecture - domain classes use real objects.
importlib.util.find_spec is a PORT BOUNDARY and may be mocked per test_doubles_policy.

These tests validate dependency verification before build phase begins.
The check must report ALL missing modules, not just the first one found.
"""

from unittest.mock import MagicMock, patch

from scripts.install.error_codes import DEP_MISSING
from scripts.install.preflight_checker import REQUIRED_MODULES, DependencyCheck


class TestDependencyCheck:
    """Test DependencyCheck class for required module verification."""

    def test_all_dependencies_present_passes(self):
        """
        GIVEN: All required Python modules are installed
        WHEN: DependencyCheck.run() is called
        THEN: Returns CheckResult with passed=True

        AC: All dependencies present allows check to pass
        """
        # ARRANGE
        check = DependencyCheck()

        # Mock importlib.util.find_spec at PORT BOUNDARY (allowed per test_doubles_policy)
        with patch(
            "scripts.install.preflight_checker.importlib.util.find_spec"
        ) as mock_find_spec:
            # All modules found - return a spec object (not None)
            mock_find_spec.return_value = MagicMock()

            # ACT
            result = check.run()

            # ASSERT
            assert result.passed is True
            assert result.error_code is None
            assert "dependencies" in result.message.lower()
            assert result.remediation is None

    def test_single_missing_dependency_shows_module_name(self):
        """
        GIVEN: One required module is missing (yaml)
        WHEN: DependencyCheck.run() is called
        THEN: Returns CheckResult with passed=False showing module name

        AC: Single missing dependency shows module name
        """
        # ARRANGE
        check = DependencyCheck()

        def find_spec_side_effect(module_name):
            if module_name == "yaml":
                return None
            return MagicMock()

        with patch(
            "scripts.install.preflight_checker.importlib.util.find_spec"
        ) as mock_find_spec:
            mock_find_spec.side_effect = find_spec_side_effect

            # ACT
            result = check.run()

            # ASSERT
            assert result.passed is False
            assert result.error_code == DEP_MISSING
            assert "yaml" in result.message.lower()

    def test_multiple_missing_dependencies_lists_all(self):
        """
        GIVEN: Multiple required modules are missing (yaml and pathlib)
        WHEN: DependencyCheck.run() is called
        THEN: Returns CheckResult listing ALL missing modules

        AC: Multiple missing dependencies lists all modules
        CRITICAL: Must report ALL missing, not just the first one found
        """
        # ARRANGE
        check = DependencyCheck()
        missing_modules = {"yaml", "pathlib"}

        def find_spec_side_effect(module_name):
            if module_name in missing_modules:
                return None
            return MagicMock()

        with patch(
            "scripts.install.preflight_checker.importlib.util.find_spec"
        ) as mock_find_spec:
            mock_find_spec.side_effect = find_spec_side_effect

            # ACT
            result = check.run()

            # ASSERT
            assert result.passed is False
            assert result.error_code == DEP_MISSING
            message_lower = result.message.lower()
            # Both missing modules must be mentioned
            assert "yaml" in message_lower
            assert "pathlib" in message_lower

    def test_dependency_check_runs_before_build(self):
        """
        GIVEN: PreflightChecker is configured with checks
        WHEN: Examining the check order
        THEN: DependencyCheck is included in preflight checks (runs before build)

        AC: Dependency check runs before build attempt
        """
        # ARRANGE
        from scripts.install.preflight_checker import PreflightChecker

        checker = PreflightChecker()

        # ACT - verify DependencyCheck is in the preflight chain
        check_types = [type(check).__name__ for check in checker._checks]

        # ASSERT - DependencyCheck must be present in preflight checks
        assert "DependencyCheck" in check_types

    def test_required_dependencies_list_is_comprehensive(self):
        """
        GIVEN: The REQUIRED_MODULES constant is defined
        WHEN: Examining its contents
        THEN: It includes all modules needed by nWave installer

        AC: Required dependencies list is comprehensive
        """
        # ARRANGE & ACT
        required = REQUIRED_MODULES

        # ASSERT - minimum required modules for nWave
        assert "yaml" in required  # For config file parsing
        assert "pathlib" in required  # For path handling (stdlib)
        assert len(required) >= 2  # At least yaml and pathlib

    def test_dependency_error_provides_complete_remediation(self):
        """
        GIVEN: Required modules are missing
        WHEN: DependencyCheck.run() returns failure
        THEN: Remediation provides actionable installation guidance

        AC: Dependency error provides complete remediation
        """
        # ARRANGE
        check = DependencyCheck()

        with patch(
            "scripts.install.preflight_checker.importlib.util.find_spec"
        ) as mock_find_spec:
            mock_find_spec.return_value = None  # All modules missing

            # ACT
            result = check.run()

            # ASSERT
            assert result.remediation is not None
            remediation_lower = result.remediation.lower()
            # Must provide installation instructions
            assert "pipenv" in remediation_lower or "install" in remediation_lower
            # Must mention how to fix
            assert "install" in remediation_lower

    def test_dependency_check_uses_importlib_for_detection(self):
        """
        GIVEN: DependencyCheck needs to verify module availability
        WHEN: DependencyCheck.run() is called
        THEN: It uses importlib.util.find_spec for detection

        Technical requirement: Use importlib for module detection
        """
        # ARRANGE
        check = DependencyCheck()

        with patch(
            "scripts.install.preflight_checker.importlib.util.find_spec"
        ) as mock_find_spec:
            mock_find_spec.return_value = MagicMock()

            # ACT
            check.run()

            # ASSERT - find_spec was called for each required module
            assert mock_find_spec.call_count >= len(REQUIRED_MODULES)
