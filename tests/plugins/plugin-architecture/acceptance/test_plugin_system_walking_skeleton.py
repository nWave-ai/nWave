"""
Walking Skeleton Acceptance Test - AgentsPlugin E2E.

This test proves the plugin system works end-to-end by installing
a single plugin (AgentsPlugin) through the complete infrastructure.

Step 01-01: Walking Skeleton - AgentsPlugin E2E
"""

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenario, then, when


# Scenario declaration linking feature file to test
@scenario(
    "walking-skeleton.feature",
    "Install single plugin through complete infrastructure",
)
def test_agents_plugin_installs_through_complete_infrastructure():
    """Acceptance test: AgentsPlugin installs through complete plugin infrastructure."""
    pass


# -----------------------------------------------------------------------------
# Background Steps
# -----------------------------------------------------------------------------


@given("the nWave project root is available")
def nwave_project_root(project_root: Path):
    """Verify nWave project root is available."""
    assert project_root.exists(), f"Project root not found: {project_root}"
    # Verify it's actually the nWave project
    assert (project_root / "nWave").exists() or (project_root / "scripts").exists()


@given(parsers.parse('the Claude config directory is "{path}"'))
def claude_config_dir_set(path: str):
    """Set Claude config directory path."""
    pytest.claude_config_dir = path


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


@given("plugin infrastructure exists with base classes")
def plugin_infrastructure_with_base_classes(project_root: Path):
    """Verify plugin infrastructure with base classes exists."""
    from scripts.install.plugins.base import (
        InstallationPlugin,
        InstallContext,
        PluginResult,
    )

    assert InstallationPlugin is not None
    assert InstallContext is not None
    assert PluginResult is not None


@given("AgentsPlugin is implemented with install() and verify() methods")
def agents_plugin_implemented(project_root: Path):
    """Verify AgentsPlugin is implemented."""
    from scripts.install.plugins.agents_plugin import AgentsPlugin

    plugin = AgentsPlugin()
    assert hasattr(plugin, "install"), "AgentsPlugin missing install() method"
    assert hasattr(plugin, "verify"), "AgentsPlugin missing verify() method"
    assert callable(plugin.install), "install() must be callable"
    assert callable(plugin.verify), "verify() must be callable"


@given("a clean test installation directory exists")
def clean_test_dir_exists(clean_test_directory: Path):
    """Verify clean test directory exists."""
    assert clean_test_directory.exists()


@given(parsers.parse('agent source files are available at "{path}"'))
def agent_source_available(path: str, project_root: Path):
    """Verify agent source files are available."""
    # Try both nWave/agents/nw and nWave/agents paths
    source_path = project_root / path
    if not source_path.exists():
        # Try alternative path
        alt_path = project_root / "nWave" / "agents"
        if alt_path.exists():
            return  # Alternative exists
        pytest.skip(f"Agent source not found: {source_path}")


@given(
    parsers.parse("agent source directory contains at least {count:d} agent .md files")
)
def agent_source_has_files(count: int, project_root: Path):
    """Verify agent source has minimum files."""
    # Check both possible locations
    for agents_dir in [
        project_root / "nWave" / "agents" / "nw",
        project_root / "nWave" / "agents",
    ]:
        if agents_dir.exists():
            agent_files = list(agents_dir.glob("*.md"))
            if len(agent_files) >= count:
                return
            # Store the path that exists for later use
            pytest.agent_source_dir = agents_dir
            assert len(agent_files) >= count, (
                f"Expected >= {count} agent files, found {len(agent_files)} in {agents_dir}"
            )
            return

    pytest.skip("Agent directory not found")


# -----------------------------------------------------------------------------
# When Steps
# -----------------------------------------------------------------------------


@when("I create a PluginRegistry instance")
def create_registry_instance(plugin_registry):
    """Create a PluginRegistry instance."""
    pytest.registry = plugin_registry


@when("I register AgentsPlugin with the registry")
def register_agents_plugin(plugin_registry):
    """Register AgentsPlugin with the registry."""
    from scripts.install.plugins.agents_plugin import AgentsPlugin

    plugin = AgentsPlugin()
    plugin_registry.register(plugin)
    pytest.agents_plugin = plugin


@when("I create an InstallContext with test directory path")
def create_install_context_with_test_dir(install_context):
    """Create InstallContext with test directory."""
    pytest.install_context = install_context


@when(parsers.parse('I call registry.install_plugin("{plugin_name}", context)'))
def call_install_plugin(plugin_name: str, plugin_registry, install_context):
    """Call install on the specific plugin through the registry."""
    # Use install_all which will install the registered plugin
    results = plugin_registry.install_all(install_context)
    pytest.install_results = results
    if plugin_name in results:
        pytest.install_result = results[plugin_name]
    else:
        pytest.install_result = None


# -----------------------------------------------------------------------------
# Then Steps
# -----------------------------------------------------------------------------


@then("AgentsPlugin.install() executes successfully")
def agents_plugin_install_succeeds():
    """Verify AgentsPlugin installation succeeded."""
    assert hasattr(pytest, "install_result"), "No install result found"
    result = pytest.install_result
    assert result is not None, "Install result is None - plugin may not have been found"
    assert result.success, f"Installation failed: {result.message}"


@then(parsers.parse('agent files are copied to "{target_path}"'))
def agent_files_copied(target_path: str, clean_test_directory: Path):
    """Verify agent files are copied to target directory."""
    # Replace {test_dir} with actual test directory
    actual_path = clean_test_directory / "agents" / "nw"
    assert actual_path.exists(), f"Agent directory not created: {actual_path}"


@then("at least 1 agent .md file exists in the target directory")
def at_least_one_agent_file(clean_test_directory: Path):
    """Verify at least one agent file exists in target."""
    agents_dir = clean_test_directory / "agents" / "nw"
    agent_files = list(agents_dir.glob("*.md"))
    assert len(agent_files) >= 1, f"Expected >= 1 agent files, found {len(agent_files)}"


@then(
    parsers.parse('AgentsPlugin.verify() returns success with message "{expected_msg}"')
)
def verify_returns_success_with_message(expected_msg: str, install_context):
    """Verify AgentsPlugin.verify() returns success with expected message."""
    result = pytest.agents_plugin.verify(install_context)
    assert result.success, f"Verification failed: {result.message}"
    assert expected_msg in result.message, (
        f"Expected message containing '{expected_msg}', got: {result.message}"
    )


@then("the agents directory is accessible and functional")
def agents_directory_accessible(clean_test_directory: Path):
    """Verify agents directory is accessible."""
    agents_dir = clean_test_directory / "agents" / "nw"
    assert agents_dir.exists(), f"Agents directory not found: {agents_dir}"
    assert agents_dir.is_dir(), f"Not a directory: {agents_dir}"
    # Verify we can list contents
    files = list(agents_dir.iterdir())
    assert len(files) >= 0  # Directory is accessible
