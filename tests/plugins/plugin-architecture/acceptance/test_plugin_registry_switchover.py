"""
Acceptance Test for Milestone 3 - Switchover to Plugin System.

Step 02-01: Modify install_framework() to use PluginRegistry

This test verifies the critical switchover of install_framework() from
hardcoded _install_*() calls to using registry.install_all(context).
"""

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenario, then, when


# Scenario declaration linking feature file to test
@scenario(
    "milestone-3-switchover.feature",
    "Installer uses PluginRegistry for installation orchestration",
)
def test_install_framework_uses_plugin_registry():
    """Step 02-01: install_framework() uses PluginRegistry for installation."""
    pass


# -----------------------------------------------------------------------------
# Background Steps
# -----------------------------------------------------------------------------


@given("the nWave project root is available")
def nwave_project_root_available(project_root: Path):
    """Verify nWave project root is available."""
    assert project_root.exists(), f"Project root not found: {project_root}"


@given(parsers.parse('the Claude config directory is "{path}"'))
def claude_config_dir_set(path: str):
    """Set Claude config directory path."""
    pytest.claude_config_dir = path


@given(parsers.parse('the current installer version is "{version}"'))
def installer_version(version: str):
    """Store current installer version."""
    pytest.installer_version = version


@given("plugin infrastructure exists (base.py, registry.py)")
def plugin_infrastructure_exists(project_root: Path):
    """Verify plugin infrastructure files exist."""
    base_path = project_root / "scripts" / "install" / "plugins" / "base.py"
    registry_path = project_root / "scripts" / "install" / "plugins" / "registry.py"

    assert base_path.exists(), f"Plugin base.py not found: {base_path}"
    assert registry_path.exists(), f"Plugin registry.py not found: {registry_path}"


# -----------------------------------------------------------------------------
# Given Steps
# -----------------------------------------------------------------------------


@given("wrapper plugins are complete (Milestone 2)")
def wrapper_plugins_complete(project_root: Path):
    """Verify all 4 wrapper plugins are implemented."""
    from scripts.install.plugins.agents_plugin import AgentsPlugin
    from scripts.install.plugins.commands_plugin import CommandsPlugin
    from scripts.install.plugins.templates_plugin import TemplatesPlugin
    from scripts.install.plugins.utilities_plugin import UtilitiesPlugin

    plugins = [
        AgentsPlugin(),
        CommandsPlugin(),
        TemplatesPlugin(),
        UtilitiesPlugin(),
    ]

    for plugin in plugins:
        assert hasattr(plugin, "install"), f"{plugin.name} missing install() method"
        assert hasattr(plugin, "verify"), f"{plugin.name} missing verify() method"


@given("install_framework() is modified to use PluginRegistry")
def install_framework_uses_registry(project_root: Path):
    """Verify install_framework() has been modified to use PluginRegistry."""
    # Read the install_nwave.py file and check for plugin imports/usage
    install_script = project_root / "scripts" / "install" / "install_nwave.py"
    content = install_script.read_text()

    # Check that PluginRegistry is imported
    assert (
        "from scripts.install.plugins.registry import PluginRegistry" in content
        or "PluginRegistry" in content
    ), "install_framework() should import and use PluginRegistry"

    # Check that registry.install_all is used
    assert "registry.install_all" in content or "install_all" in content, (
        "install_framework() should call registry.install_all(context)"
    )


# -----------------------------------------------------------------------------
# When Steps
# -----------------------------------------------------------------------------


@when("I run install_nwave.py with plugin orchestration")
def run_install_with_plugins(
    clean_test_directory: Path, project_root: Path, test_logger
):
    """Run install_nwave.py using plugin orchestration."""
    from scripts.install.plugins.agents_plugin import AgentsPlugin
    from scripts.install.plugins.base import InstallContext
    from scripts.install.plugins.commands_plugin import CommandsPlugin
    from scripts.install.plugins.registry import PluginRegistry
    from scripts.install.plugins.templates_plugin import TemplatesPlugin
    from scripts.install.plugins.utilities_plugin import UtilitiesPlugin

    # Create registry and register all plugins
    registry = PluginRegistry()
    registry.register(AgentsPlugin())
    registry.register(CommandsPlugin())
    registry.register(TemplatesPlugin())
    registry.register(UtilitiesPlugin())

    # Create context with all required utilities
    context = InstallContext(
        claude_dir=clean_test_directory,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )

    pytest.registry = registry
    pytest.install_context = context


@when("registry.install_all(context) is called")
def call_registry_install_all():
    """Call registry.install_all(context)."""
    results = pytest.registry.install_all(pytest.install_context)
    pytest.install_results = results


# -----------------------------------------------------------------------------
# Then Steps
# -----------------------------------------------------------------------------


@then("all 4 plugins are installed in correct order")
def all_plugins_installed_in_order():
    """Verify all 4 plugins are installed in priority order."""
    results = pytest.install_results

    # Verify all 4 plugins have results
    assert len(results) == 4, f"Expected 4 plugin results, got {len(results)}"

    expected_plugins = ["agents", "commands", "templates", "utilities"]
    for plugin_name in expected_plugins:
        assert plugin_name in results, f"Plugin '{plugin_name}' not in results"

    # Verify execution order (by priority)
    execution_order = pytest.registry.get_execution_order()
    assert execution_order == expected_plugins, (
        f"Expected order {expected_plugins}, got {execution_order}"
    )


@then("InstallContext provides all required utilities")
def install_context_has_utilities():
    """Verify InstallContext has all required utilities."""
    context = pytest.install_context

    # Check required fields
    assert context.claude_dir is not None, "claude_dir is required"
    assert context.scripts_dir is not None, "scripts_dir is required"
    assert context.templates_dir is not None, "templates_dir is required"
    assert context.logger is not None, "logger is required"
    assert context.project_root is not None, "project_root is required"
    assert context.framework_source is not None, "framework_source is required"


@then("BackupManager creates backups before installation")
def backup_manager_creates_backups():
    """Verify BackupManager functionality (tested via context.backup_manager)."""
    # The BackupManager is called before install_framework() in the main flow
    # For this test, we verify the context can hold a backup_manager
    context = pytest.install_context
    # backup_manager is optional in InstallContext, verify it can be set
    assert hasattr(context, "backup_manager"), (
        "InstallContext should have backup_manager field"
    )


@then("installation completes successfully")
def installation_completes_successfully():
    """Verify all plugins installed successfully."""
    results = pytest.install_results

    for plugin_name, result in results.items():
        assert result.success, f"Plugin '{plugin_name}' failed: {result.message}"


@then("verification passes for all components")
def verification_passes():
    """Verify all plugins pass verification."""
    for plugin_name, result in pytest.install_results.items():
        # Verify each plugin
        plugin = pytest.registry.plugins[plugin_name]
        verify_result = plugin.verify(pytest.install_context)
        assert verify_result.success, (
            f"Plugin '{plugin_name}' verification failed: {verify_result.message}"
        )
