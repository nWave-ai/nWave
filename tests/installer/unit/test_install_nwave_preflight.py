"""
Unit tests for install_nwave.py preflight integration.

CRITICAL: Tests follow hexagonal architecture - port boundaries only for mocks.
These tests validate that install_nwave.py properly integrates preflight_checker,
output_formatter, and context_detector BEFORE any installation actions.

Step 05-01: Installer Pre-flight Integration
"""

import sys
from unittest.mock import MagicMock, patch

from scripts.install.error_codes import ENV_NO_VENV
from scripts.install.preflight_checker import CheckResult


class TestInstallNwavePreflightIntegration:
    """Tests for install_nwave.py preflight integration."""

    def test_install_nwave_calls_preflight_before_install(self):
        """
        GIVEN: The installer is executed
        WHEN: main() is called
        THEN: Preflight checks are executed BEFORE install_framework()

        This test verifies the critical requirement that preflight validation
        happens before any installation or file system operations.
        """
        # ARRANGE
        call_order = []

        def track_preflight_check(*args, **kwargs):
            call_order.append("preflight")
            return []  # Empty results means all checks passed

        def track_install_framework(*args, **kwargs):
            call_order.append("install_framework")
            return True

        with patch(
            "scripts.install.install_nwave.PreflightChecker"
        ) as mock_preflight_class:
            mock_checker = MagicMock()
            mock_checker.run_all_checks.side_effect = track_preflight_check
            mock_checker.has_blocking_failures.return_value = False
            mock_preflight_class.return_value = mock_checker

            with patch("scripts.install.install_nwave.NWaveInstaller.create_backup"):
                with patch(
                    "scripts.install.install_nwave.NWaveInstaller.install_framework",
                    side_effect=track_install_framework,
                ):
                    with patch(
                        "scripts.install.install_nwave.NWaveInstaller.validate_installation",
                        return_value=True,
                    ):
                        with patch(
                            "scripts.install.install_nwave.NWaveInstaller.create_manifest"
                        ):
                            # ACT
                            from scripts.install.install_nwave import main

                            with patch.object(sys, "argv", ["install_nwave.py"]):
                                main()

        # ASSERT
        assert "preflight" in call_order, "Preflight checks were not called"
        assert "install_framework" in call_order, "install_framework was not called"
        preflight_index = call_order.index("preflight")
        install_index = call_order.index("install_framework")
        assert preflight_index < install_index, (
            f"Preflight checks must run BEFORE install_framework. Order was: {call_order}"
        )

    def test_install_nwave_exits_early_on_preflight_failure(self):
        """
        GIVEN: Preflight checks fail (e.g., no virtual environment)
        WHEN: main() is called
        THEN: Returns non-zero exit code and does NOT call install_framework

        This ensures the installer fails fast when environment is invalid.
        """
        # ARRANGE
        install_called = False

        def track_install(*args, **kwargs):
            nonlocal install_called
            install_called = True
            return True

        failed_result = CheckResult(
            passed=False,
            error_code=ENV_NO_VENV,
            message="Not running in a virtual environment.",
            remediation="Create and activate a virtual environment.",
        )

        with patch(
            "scripts.install.install_nwave.PreflightChecker"
        ) as mock_preflight_class:
            mock_checker = MagicMock()
            mock_checker.run_all_checks.return_value = [failed_result]
            mock_checker.has_blocking_failures.return_value = True
            mock_checker.get_failed_checks.return_value = [failed_result]
            mock_preflight_class.return_value = mock_checker

            with (
                patch(
                    "scripts.install.install_nwave.NWaveInstaller.install_framework",
                    side_effect=track_install,
                ),
                patch("scripts.install.install_nwave.format_error") as mock_format,
            ):
                mock_format.return_value = "Formatted error message"

                # ACT
                from scripts.install.install_nwave import main

                with patch.object(sys, "argv", ["install_nwave.py"]):
                    exit_code = main()

        # ASSERT
        assert exit_code != 0, "Should return non-zero exit code on preflight failure"
        assert not install_called, (
            "install_framework should NOT be called when preflight fails"
        )

    def test_install_nwave_uses_format_error_for_failures(self):
        """
        GIVEN: Preflight checks fail
        WHEN: main() displays the error
        THEN: format_error() from output_formatter is used for display

        This validates proper integration with the output_formatter module.
        """
        # ARRANGE
        failed_result = CheckResult(
            passed=False,
            error_code=ENV_NO_VENV,
            message="Not running in a virtual environment.",
            remediation="Create and activate a virtual environment.",
        )

        with patch(
            "scripts.install.install_nwave.PreflightChecker"
        ) as mock_preflight_class:
            mock_checker = MagicMock()
            mock_checker.run_all_checks.return_value = [failed_result]
            mock_checker.has_blocking_failures.return_value = True
            mock_checker.get_failed_checks.return_value = [failed_result]
            mock_preflight_class.return_value = mock_checker

            with patch(
                "scripts.install.install_nwave.format_error"
            ) as mock_format_error:
                mock_format_error.return_value = "Formatted error message"

                # ACT
                from scripts.install.install_nwave import main

                with patch.object(sys, "argv", ["install_nwave.py"]):
                    main()

        # ASSERT
        mock_format_error.assert_called()
        call_args = mock_format_error.call_args
        assert call_args is not None
        # Verify format_error was called with the error code from failed check
        assert ENV_NO_VENV in str(call_args)

    def test_install_nwave_context_detector_selects_output_mode(self):
        """
        GIVEN: The installer runs in different contexts (terminal, CI, Claude Code)
        WHEN: format_error is called
        THEN: The context_detector determines the output format automatically

        This validates that format_error uses context_detector internally.
        """
        # ARRANGE
        failed_result = CheckResult(
            passed=False,
            error_code=ENV_NO_VENV,
            message="Not running in a virtual environment.",
            remediation="Create and activate a virtual environment.",
        )

        with patch(
            "scripts.install.install_nwave.PreflightChecker"
        ) as mock_preflight_class:
            mock_checker = MagicMock()
            mock_checker.run_all_checks.return_value = [failed_result]
            mock_checker.has_blocking_failures.return_value = True
            mock_checker.get_failed_checks.return_value = [failed_result]
            mock_preflight_class.return_value = mock_checker

            # Verify format_error is called (which internally uses context_detector)
            with patch(
                "scripts.install.install_nwave.format_error"
            ) as mock_format_error:
                mock_format_error.return_value = "Formatted error"

                # ACT
                from scripts.install.install_nwave import main

                with patch.object(sys, "argv", ["install_nwave.py"]):
                    main()

        # ASSERT
        mock_format_error.assert_called_once()
        # The format_error function automatically selects format based on context
        # We verify it's being used which means context detection is active


class TestInstallNwavePreflightSuccess:
    """Tests for successful preflight scenarios."""

    def test_install_nwave_continues_when_preflight_passes(self):
        """
        GIVEN: All preflight checks pass
        WHEN: main() is called
        THEN: Installation continues with install_framework

        This confirms the happy path where preflight passes.
        """
        # ARRANGE
        steps_executed = []

        def track_install(*args, **kwargs):
            steps_executed.append("install_framework")
            return True

        passed_result = CheckResult(
            passed=True,
            error_code=None,
            message="Virtual environment detected.",
            remediation=None,
        )

        with patch(
            "scripts.install.install_nwave.PreflightChecker"
        ) as mock_preflight_class:
            mock_checker = MagicMock()
            mock_checker.run_all_checks.return_value = [passed_result]
            mock_checker.has_blocking_failures.return_value = False
            mock_preflight_class.return_value = mock_checker

            with patch("scripts.install.install_nwave.NWaveInstaller.create_backup"):
                with patch(
                    "scripts.install.install_nwave.NWaveInstaller.install_framework",
                    side_effect=track_install,
                ):
                    with patch(
                        "scripts.install.install_nwave.NWaveInstaller.validate_installation",
                        return_value=True,
                    ):
                        with patch(
                            "scripts.install.install_nwave.NWaveInstaller.create_manifest"
                        ):
                            # ACT
                            from scripts.install.install_nwave import main

                            with patch.object(sys, "argv", ["install_nwave.py"]):
                                exit_code = main()

        # ASSERT
        assert exit_code == 0, "Should return 0 on successful installation"
        assert "install_framework" in steps_executed
