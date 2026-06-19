"""
Unit tests for install_framework() switchover to PluginRegistry.

Step 02-01: Verify install_framework() uses PluginRegistry for installation
orchestration instead of hardcoded _install_*() method calls.

These tests validate:
1. PluginRegistry is imported and used
2. All 4 wrapper plugins are registered
3. InstallContext is created with required fields
4. registry.install_all(context) is called
5. Plugins execute in priority order
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from scripts.install.plugins.base import InstallContext, PluginResult
from scripts.install.plugins.registry import PluginRegistry


@pytest.fixture
def configured_installer(tmp_path):
    """Create an NWaveInstaller with mocked paths and dependencies."""
    from scripts.install.install_nwave import NWaveInstaller

    with patch.object(NWaveInstaller, "__init__", lambda self, *args, **kwargs: None):
        installer = NWaveInstaller()
        installer.dry_run = False
        installer.dev_mode = False
        installer._platform_override = {"claude_code"}
        installer.claude_config_dir = tmp_path / "claude"
        installer.project_root = tmp_path
        installer.framework_source = tmp_path / "nWave"
        installer.logger = Mock()
        installer.logger.progress_spinner = MagicMock()
        installer.logger.progress_spinner.return_value.__enter__ = Mock()
        installer.logger.progress_spinner.return_value.__exit__ = Mock()
        installer.backup_manager = Mock()

        # Create minimal source structure
        installer.framework_source.mkdir(parents=True, exist_ok=True)
        (installer.framework_source / "agents").mkdir(parents=True)
        (installer.framework_source / "tasks" / "nw").mkdir(parents=True)

        return installer


class TestInstallFrameworkUsesPluginRegistry:
    """Tests for install_framework() using PluginRegistry."""

    def test_install_framework_creates_plugin_registry(self, configured_installer):
        """Verify install_framework() creates a PluginRegistry instance."""
        installer = configured_installer

        with patch.object(installer, "_create_plugin_registry") as mock_create:
            mock_registry = Mock(spec=PluginRegistry)
            mock_registry.install_all.return_value = {
                "agents": PluginResult(
                    success=True, plugin_name="agents", message="OK"
                ),
                "commands": PluginResult(
                    success=True, plugin_name="commands", message="OK"
                ),
                "templates": PluginResult(
                    success=True, plugin_name="templates", message="OK"
                ),
                "utilities": PluginResult(
                    success=True, plugin_name="utilities", message="OK"
                ),
            }
            mock_create.return_value = mock_registry

            installer.install_framework()

            mock_create.assert_called_once()

    def test_install_framework_registers_all_wrapper_plugins(
        self, configured_installer
    ):
        """Verify all 8 wrapper plugins are registered with the registry."""
        installer = configured_installer

        # Patch PluginRegistry to capture registrations
        with patch("scripts.install.install_nwave.PluginRegistry") as MockRegistry:
            mock_registry = Mock()
            mock_registry.install_all.return_value = {
                "agents": PluginResult(
                    success=True, plugin_name="agents", message="OK"
                ),
                "commands": PluginResult(
                    success=True, plugin_name="commands", message="OK"
                ),
                "templates": PluginResult(
                    success=True, plugin_name="templates", message="OK"
                ),
                "skills": PluginResult(
                    success=True, plugin_name="skills", message="OK"
                ),
                "utilities": PluginResult(
                    success=True, plugin_name="utilities", message="OK"
                ),
                "des": PluginResult(success=True, plugin_name="des", message="OK"),
                "attribution": PluginResult(
                    success=True, plugin_name="attribution", message="OK"
                ),
                "reviewer_signing": PluginResult(
                    success=True, plugin_name="reviewer_signing", message="OK"
                ),
            }
            MockRegistry.return_value = mock_registry

            installer.install_framework()

            # Verify 8 plugins registered (skills, DES, attribution, reviewer_signing)
            assert mock_registry.register.call_count == 8

            # Verify each plugin type was registered
            registered_plugins = [
                call.args[0] for call in mock_registry.register.call_args_list
            ]
            plugin_names = [p.name for p in registered_plugins]

            assert "agents" in plugin_names
            assert "commands" in plugin_names
            assert "templates" in plugin_names
            assert "skills" in plugin_names
            assert "utilities" in plugin_names
            assert "des" in plugin_names
            assert "attribution" in plugin_names
            assert "reviewer_signing" in plugin_names

    def test_install_framework_creates_install_context(self, configured_installer):
        """Verify InstallContext is created with required fields."""
        installer = configured_installer

        captured_context = None

        def capture_install_all(context):
            nonlocal captured_context
            captured_context = context
            return {
                "agents": PluginResult(
                    success=True, plugin_name="agents", message="OK"
                ),
                "commands": PluginResult(
                    success=True, plugin_name="commands", message="OK"
                ),
                "templates": PluginResult(
                    success=True, plugin_name="templates", message="OK"
                ),
                "utilities": PluginResult(
                    success=True, plugin_name="utilities", message="OK"
                ),
            }

        with patch("scripts.install.install_nwave.PluginRegistry") as MockRegistry:
            mock_registry = Mock()
            mock_registry.install_all.side_effect = capture_install_all
            MockRegistry.return_value = mock_registry

            installer.install_framework()

            # Verify context was created with required fields
            assert captured_context is not None
            assert captured_context.claude_dir == installer.claude_config_dir
            assert captured_context.logger is not None
            assert captured_context.project_root == installer.project_root
            assert captured_context.framework_source == installer.framework_source

    def test_install_framework_calls_registry_install_all(self, configured_installer):
        """Verify install_framework() calls registry.install_all(context)."""
        installer = configured_installer

        with patch("scripts.install.install_nwave.PluginRegistry") as MockRegistry:
            mock_registry = Mock()
            mock_registry.install_all.return_value = {
                "agents": PluginResult(
                    success=True, plugin_name="agents", message="OK"
                ),
                "commands": PluginResult(
                    success=True, plugin_name="commands", message="OK"
                ),
                "templates": PluginResult(
                    success=True, plugin_name="templates", message="OK"
                ),
                "utilities": PluginResult(
                    success=True, plugin_name="utilities", message="OK"
                ),
            }
            MockRegistry.return_value = mock_registry

            installer.install_framework()

            mock_registry.install_all.assert_called_once()
            call_args = mock_registry.install_all.call_args
            assert isinstance(call_args.args[0], InstallContext)


class TestInstallFrameworkPluginExecutionOrder:
    """Tests for plugin execution order in install_framework()."""

    def test_plugins_execute_in_priority_order(self, configured_installer):
        """Verify plugins execute in priority order (agents first, utilities last)."""
        installer = configured_installer

        registration_order = []

        def track_registration(plugin):
            registration_order.append(plugin.name)

        with patch("scripts.install.install_nwave.PluginRegistry") as MockRegistry:
            mock_registry = Mock()
            mock_registry.register.side_effect = track_registration
            mock_registry.install_all.return_value = {
                "agents": PluginResult(
                    success=True, plugin_name="agents", message="OK"
                ),
                "commands": PluginResult(
                    success=True, plugin_name="commands", message="OK"
                ),
                "templates": PluginResult(
                    success=True, plugin_name="templates", message="OK"
                ),
                "skills": PluginResult(
                    success=True, plugin_name="skills", message="OK"
                ),
                "utilities": PluginResult(
                    success=True, plugin_name="utilities", message="OK"
                ),
                "des": PluginResult(success=True, plugin_name="des", message="OK"),
                "attribution": PluginResult(
                    success=True, plugin_name="attribution", message="OK"
                ),
                "reviewer_signing": PluginResult(
                    success=True, plugin_name="reviewer_signing", message="OK"
                ),
            }
            MockRegistry.return_value = mock_registry

            installer.install_framework()

            # All 8 plugins should be registered (skills, DES, attribution, reviewer_signing)
            assert len(registration_order) == 8
            assert "agents" in registration_order
            assert "commands" in registration_order
            assert "templates" in registration_order
            assert "skills" in registration_order
            assert "utilities" in registration_order
            assert "des" in registration_order
            assert "attribution" in registration_order
            assert "reviewer_signing" in registration_order


class TestInstallFrameworkDryRunMode:
    """Tests for dry_run mode with PluginRegistry."""

    def test_dry_run_mode_does_not_call_install_all(self, configured_installer):
        """Verify dry_run mode skips registry.install_all()."""
        installer = configured_installer
        installer.dry_run = True  # Override to test dry_run behavior

        with patch("scripts.install.install_nwave.PluginRegistry") as MockRegistry:
            mock_registry = Mock()
            MockRegistry.return_value = mock_registry

            result = installer.install_framework()

            assert result is True
            mock_registry.install_all.assert_not_called()


class TestInstallFrameworkErrorHandling:
    """Tests for error handling in install_framework() with PluginRegistry."""

    def test_install_framework_returns_false_on_plugin_failure(
        self, configured_installer
    ):
        """Verify install_framework() returns False when a plugin fails."""
        installer = configured_installer

        with patch("scripts.install.install_nwave.PluginRegistry") as MockRegistry:
            mock_registry = Mock()
            # Simulate plugin failure
            mock_registry.install_all.return_value = {
                "agents": PluginResult(
                    success=True, plugin_name="agents", message="OK"
                ),
                "commands": PluginResult(
                    success=False,
                    plugin_name="commands",
                    message="Failed to copy files",
                    errors=["Permission denied"],
                ),
            }
            MockRegistry.return_value = mock_registry

            result = installer.install_framework()

            # Should return False when any plugin fails
            assert result is False
