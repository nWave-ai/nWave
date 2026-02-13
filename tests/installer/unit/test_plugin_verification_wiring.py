"""Unit tests for plugin verification wiring in validate_installation().

Tests validate that:
- _create_plugin_registry(silent=True) suppresses logger on PluginRegistry
- _create_plugin_registry() default passes logger to PluginRegistry
- validate_installation() calls registry.verify_all() and handles results
- validate_installation() fails when plugin verification reports failures
- validate_installation() logs success when all plugins verified

CRITICAL: Tests follow hexagonal architecture - mocks only at port boundaries.
NWaveInstaller is the driving port; InstallationVerifier/PluginRegistry are driven ports.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.install.plugins.base import PluginResult


class TestCreatePluginRegistrySilentParameter:
    """Test _create_plugin_registry silent parameter controls logger injection."""

    @patch("scripts.install.install_nwave.PathUtils.get_claude_config_dir")
    @patch("scripts.install.install_nwave.PathUtils.get_project_root")
    def test_create_plugin_registry_silent_suppresses_logger(
        self, mock_get_root, mock_get_config
    ):
        """
        GIVEN: An NWaveInstaller instance
        WHEN: _create_plugin_registry(silent=True) is called
        THEN: The returned PluginRegistry has _logger set to None
        """
        # ARRANGE
        mock_get_root.return_value = Path("/fake/project")
        mock_get_config.return_value = Path("/fake/.claude")
        from scripts.install.install_nwave import NWaveInstaller

        installer = NWaveInstaller(dry_run=True)

        # ACT
        registry = installer._create_plugin_registry(silent=True)

        # ASSERT
        assert registry._logger is None

    @patch("scripts.install.install_nwave.PathUtils.get_claude_config_dir")
    @patch("scripts.install.install_nwave.PathUtils.get_project_root")
    def test_create_plugin_registry_default_has_logger(
        self, mock_get_root, mock_get_config
    ):
        """
        GIVEN: An NWaveInstaller instance
        WHEN: _create_plugin_registry() is called with default parameters
        THEN: The returned PluginRegistry has _logger set to the installer's logger
        """
        # ARRANGE
        mock_get_root.return_value = Path("/fake/project")
        mock_get_config.return_value = Path("/fake/.claude")
        from scripts.install.install_nwave import NWaveInstaller

        installer = NWaveInstaller(dry_run=True)

        # ACT
        registry = installer._create_plugin_registry()

        # ASSERT
        assert registry._logger is not None
        assert registry._logger is installer.logger


class TestValidateInstallationPluginVerification:
    """Test validate_installation() wires registry.verify_all() correctly."""

    def _build_installer_with_mocks(self, tmp_path):
        """Build an NWaveInstaller with filesystem and verifier mocked."""
        with (
            patch(
                "scripts.install.install_nwave.PathUtils.get_claude_config_dir"
            ) as mock_config,
            patch(
                "scripts.install.install_nwave.PathUtils.get_project_root"
            ) as mock_root,
        ):
            mock_config.return_value = tmp_path / ".claude"
            mock_root.return_value = tmp_path / "project"
            from scripts.install.install_nwave import NWaveInstaller

            installer = NWaveInstaller(dry_run=True)
        return installer

    def _mock_verification_result(self):
        """Create a passing VerificationResult mock."""
        result = MagicMock()
        result.success = True
        result.manifest_exists = True
        result.missing_essential_files = []
        return result

    def _all_success_plugin_results(self):
        """Return plugin results where all plugins pass verification."""
        return {
            "agents": PluginResult(success=True, plugin_name="agents", message="OK"),
            "commands": PluginResult(
                success=True, plugin_name="commands", message="OK"
            ),
            "templates": PluginResult(
                success=True, plugin_name="templates", message="OK"
            ),
            "skills": PluginResult(success=True, plugin_name="skills", message="OK"),
            "utilities": PluginResult(
                success=True, plugin_name="utilities", message="OK"
            ),
            "des": PluginResult(success=True, plugin_name="des", message="OK"),
        }

    def _failing_des_plugin_results(self):
        """Return plugin results where DES plugin fails verification."""
        results = self._all_success_plugin_results()
        results["des"] = PluginResult(
            success=False,
            plugin_name="des",
            message="DES plugin verification failed",
            errors=["Missing des/__init__.py", "Missing des/engine.py"],
        )
        return results

    def test_validate_installation_calls_verify_all(self, tmp_path):
        """
        GIVEN: An NWaveInstaller with all verifications passing
        WHEN: validate_installation() is called
        THEN: registry.verify_all() is invoked to check plugin health
        """
        # ARRANGE
        installer = self._build_installer_with_mocks(tmp_path)
        mock_registry = MagicMock()
        mock_registry.verify_all.return_value = self._all_success_plugin_results()

        with (
            patch.object(
                installer,
                "_create_plugin_registry",
                return_value=mock_registry,
            ),
            patch.object(
                type(installer),
                "_validate_schema_template",
                return_value=True,
            ),
            patch("scripts.install.install_nwave.InstallationVerifier") as MockVerifier,
        ):
            mock_verifier_instance = MockVerifier.return_value
            mock_verifier_instance.run_verification.return_value = (
                self._mock_verification_result()
            )

            # Ensure source dirs exist so file counting does not fail
            framework_src = installer.framework_source
            for subdir in [
                "agents/nw",
                "commands/nw",
                "templates",
                "scripts",
            ]:
                (framework_src / subdir).mkdir(parents=True, exist_ok=True)

            # ACT
            installer.validate_installation()

            # ASSERT
            mock_registry.verify_all.assert_called_once()

    def test_validate_installation_fails_on_plugin_verification_failure(self, tmp_path):
        """
        GIVEN: An NWaveInstaller where DES plugin verification fails
        WHEN: validate_installation() is called
        THEN: validate_installation() returns False
        """
        # ARRANGE
        installer = self._build_installer_with_mocks(tmp_path)
        mock_registry = MagicMock()
        mock_registry.verify_all.return_value = self._failing_des_plugin_results()

        with (
            patch.object(
                installer,
                "_create_plugin_registry",
                return_value=mock_registry,
            ),
            patch.object(
                type(installer),
                "_validate_schema_template",
                return_value=True,
            ),
            patch("scripts.install.install_nwave.InstallationVerifier") as MockVerifier,
        ):
            mock_verifier_instance = MockVerifier.return_value
            mock_verifier_instance.run_verification.return_value = (
                self._mock_verification_result()
            )

            framework_src = installer.framework_source
            for subdir in [
                "agents/nw",
                "commands/nw",
                "templates",
                "scripts",
            ]:
                (framework_src / subdir).mkdir(parents=True, exist_ok=True)

            # ACT
            result = installer.validate_installation()

            # ASSERT
            assert result is False

    def test_validate_installation_reports_all_plugins_verified_on_success(
        self, tmp_path
    ):
        """
        GIVEN: An NWaveInstaller where all plugin verifications pass
        WHEN: validate_installation() is called
        THEN: The log output contains 'All plugins verified'
        """
        # ARRANGE
        installer = self._build_installer_with_mocks(tmp_path)
        mock_registry = MagicMock()
        mock_registry.verify_all.return_value = self._all_success_plugin_results()

        log_messages = []
        original_info = installer.logger.info

        def capture_info(msg):
            log_messages.append(msg)
            original_info(msg)

        installer.logger.info = capture_info

        with (
            patch.object(
                installer,
                "_create_plugin_registry",
                return_value=mock_registry,
            ),
            patch.object(
                type(installer),
                "_validate_schema_template",
                return_value=True,
            ),
            patch("scripts.install.install_nwave.InstallationVerifier") as MockVerifier,
        ):
            mock_verifier_instance = MockVerifier.return_value
            mock_verifier_instance.run_verification.return_value = (
                self._mock_verification_result()
            )

            framework_src = installer.framework_source
            for subdir in [
                "agents/nw",
                "commands/nw",
                "templates",
                "scripts",
            ]:
                (framework_src / subdir).mkdir(parents=True, exist_ok=True)

            # ACT
            installer.validate_installation()

        # ASSERT
        all_log_text = " ".join(log_messages)
        assert "All plugins verified" in all_log_text
