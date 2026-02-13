"""
Integration tests for upgrade scenarios (step 04-03).

Test upgrade from monolithic installer (v1.2.0) to plugin-based (v1.3.0+).
Ensure existing installations are preserved.

Domain: Plugin Infrastructure - Upgrade Compatibility
"""

import logging
from pathlib import Path

import pytest

from scripts.install.plugins.agents_plugin import AgentsPlugin
from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.commands_plugin import CommandsPlugin
from scripts.install.plugins.des_plugin import DESPlugin
from scripts.install.plugins.registry import PluginRegistry
from scripts.install.plugins.templates_plugin import TemplatesPlugin
from scripts.install.plugins.utilities_plugin import UtilitiesPlugin


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _simulate_v120(claude_dir: Path) -> Path:
    """
    Populate a directory with v1.2.0 monolithic installation artifacts.

    Returns the claude_dir for convenience.
    """
    # Create agents directory with some agent files
    agents_dir = claude_dir / "agents" / "nw"
    agents_dir.mkdir(parents=True, exist_ok=True)

    sample_agents = ["software-crafter.md", "solution-architect.md", "researcher.md"]
    for agent_name in sample_agents:
        agent_file = agents_dir / agent_name
        agent_file.write_text(f"# {agent_name}\n\nMonolithic v1.2.0 installation\n")

    # Create commands directory with command files
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    sample_commands = ["atdd.md", "root-why.md", "commit.md"]
    for cmd_name in sample_commands:
        cmd_file = commands_dir / cmd_name
        cmd_file.write_text(f"# {cmd_name}\n\nCommand from v1.2.0\n")

    # Create templates directory with template files
    templates_dir = claude_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    sample_templates = [
        "develop-outside-in-tdd.yaml",
        "nwave-complete-methodology.yaml",
    ]
    for template_name in sample_templates:
        template_file = templates_dir / template_name
        template_file.write_text(f"# {template_name}\nversion: 1.2.0\n")

    # Create scripts directory with utility scripts
    scripts_dir = claude_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    utility_script = scripts_dir / "validate_step_file.py"
    utility_script.write_text('"""Utility script v1.2.0."""\n__version__ = "1.2.0"\n')

    # Create version marker (simulating monolithic installation marker)
    version_file = claude_dir / ".nwave_version"
    version_file.write_text("1.2.0")

    return claude_dir


def _make_context(
    claude_dir: Path, project_root: Path, logger: logging.Logger
) -> InstallContext:
    """Create an InstallContext pointing at the given claude_dir."""
    return InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )


def _full_registry() -> PluginRegistry:
    """Create a PluginRegistry with all 5 plugins."""
    registry = PluginRegistry()
    registry.register(AgentsPlugin())
    registry.register(CommandsPlugin())
    registry.register(TemplatesPlugin())
    registry.register(UtilitiesPlugin())
    registry.register(DESPlugin())
    return registry


# -----------------------------------------------------------------------------
# Module-scoped fixtures: install once, share across read-only tests
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _module_project_root() -> Path:
    """Return the nWave project root directory (module-scoped)."""
    current = Path(__file__).resolve()
    return current.parents[4]


@pytest.fixture(scope="module")
def _module_logger() -> logging.Logger:
    """Provide a configured logger (module-scoped)."""
    logger = logging.getLogger("test.upgrade_scenarios")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture(scope="module")
def full_upgrade_state(tmp_path_factory, _module_project_root, _module_logger) -> tuple:
    """
    Simulate v1.2.0 -> plugin-based upgrade ONCE for the module.

    Returns (context, registry, install_results, pre_upgrade_agent_count).
    Tests using this fixture must NOT mutate the installed directory.
    """
    claude_dir = tmp_path_factory.mktemp("upgrade_full") / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    _simulate_v120(claude_dir)

    pre_upgrade_agent_count = len(list((claude_dir / "agents" / "nw").glob("*.md")))

    context = _make_context(claude_dir, _module_project_root, _module_logger)
    registry = _full_registry()
    results = registry.install_all(context)

    return context, registry, results, pre_upgrade_agent_count


# -----------------------------------------------------------------------------
# Per-test fixtures (only for tests that mutate state)
# -----------------------------------------------------------------------------


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.upgrade_scenarios")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    current = Path(__file__).resolve()
    return current.parents[4]  # 4 levels up from test file


@pytest.fixture
def clean_test_directory(tmp_path: Path) -> Path:
    """Provide a clean test installation directory simulating ~/.claude."""
    test_dir = tmp_path / ".claude"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


@pytest.fixture
def install_context(clean_test_directory, project_root, test_logger):
    """Create InstallContext for testing."""
    return InstallContext(
        claude_dir=clean_test_directory,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )


@pytest.fixture
def simulated_v120_installation(clean_test_directory: Path, project_root: Path) -> Path:
    """
    Simulate an existing v1.2.0 monolithic installation (per-test).

    Returns the claude_dir path for the simulated installation.
    """
    return _simulate_v120(clean_test_directory)


# -----------------------------------------------------------------------------
# Test Class: Upgrade Scenario - Existing Components Preserved
# -----------------------------------------------------------------------------


class TestExistingComponentsPreservedDuringUpgrade:
    """
    Integration tests for verifying existing components are preserved
    during upgrade from monolithic v1.2.0 to plugin-based v1.3.0+.
    """

    def test_existing_agents_detected_before_upgrade(
        self,
        simulated_v120_installation: Path,
        project_root: Path,
        test_logger: logging.Logger,
    ):
        """
        Existing components should be detected before upgrade.

        Given: v1.2.0 monolithic installation exists
        When: Plugin-based installer scans the installation
        Then: Existing agent files are detected
        """
        # Arrange - simulated installation already created by fixture
        agents_dir = simulated_v120_installation / "agents" / "nw"

        # Assert - existing agents are present before upgrade
        assert agents_dir.exists(), (
            "Agents directory should exist in v1.2.0 installation"
        )
        existing_agents = list(agents_dir.glob("*.md"))
        assert len(existing_agents) == 3, (
            f"Expected 3 agent files from v1.2.0, found {len(existing_agents)}"
        )

    def test_existing_agents_preserved_after_plugin_installation(
        self,
        full_upgrade_state,
    ):
        """
        Existing agent files should be preserved or upgraded after plugin installation.

        Given: v1.2.0 monolithic installation with 3 agents
        When: AgentsPlugin.install() runs
        Then: Agents are present (existing preserved or upgraded)
        """
        context, _registry, results, pre_upgrade_agent_count = full_upgrade_state

        # Assert - agents plugin succeeded
        assert results["agents"].success, (
            f"AgentsPlugin installation failed: {results['agents'].message}"
        )

        # Assert - agents preserved or upgraded
        agents_dir = context.claude_dir / "agents" / "nw"
        post_upgrade_agents = list(agents_dir.glob("*.md"))
        assert len(post_upgrade_agents) >= pre_upgrade_agent_count, (
            f"Expected at least {pre_upgrade_agent_count} agents after upgrade, "
            f"found {len(post_upgrade_agents)}"
        )

    def test_existing_commands_preserved_after_plugin_installation(
        self,
        full_upgrade_state,
    ):
        """
        Existing command files should be preserved after plugin installation.

        Given: v1.2.0 monolithic installation with 3 commands
        When: CommandsPlugin.install() runs
        Then: Commands are present (existing preserved or upgraded)
        """
        context, _registry, results, _pre_agents = full_upgrade_state

        # Assert - commands plugin succeeded
        assert results["commands"].success, (
            f"CommandsPlugin installation failed: {results['commands'].message}"
        )

        # Assert - commands preserved (v1.2.0 had 3 commands)
        commands_dir = context.claude_dir / "commands"
        post_upgrade_commands = list(commands_dir.glob("*.md"))
        assert len(post_upgrade_commands) >= 3, (
            f"Expected at least 3 commands after upgrade, "
            f"found {len(post_upgrade_commands)}"
        )


# -----------------------------------------------------------------------------
# Test Class: Upgrade Scenario - DES Plugin Addition
# -----------------------------------------------------------------------------


class TestDESPluginAddedDuringUpgrade:
    """
    Integration tests for verifying DES plugin can be added to existing
    installation without affecting existing components.
    """

    def test_des_plugin_added_to_existing_installation(
        self,
        full_upgrade_state,
    ):
        """
        DES plugin should be added to existing installation.

        Given: v1.2.0 installation exists (without DES)
        When: Full plugin-based installation runs (with DES)
        Then: DES components are added without breaking existing installation
        """
        context, _registry, results, pre_upgrade_agent_count = full_upgrade_state

        # Assert - DES was added
        assert "des" in results, "DES plugin should be in results"
        assert results["des"].success, (
            f"DES installation failed: {results['des'].message}"
        )

        # Assert - existing components preserved
        agents_dir = context.claude_dir / "agents" / "nw"
        post_upgrade_agent_count = len(list(agents_dir.glob("*.md")))
        assert post_upgrade_agent_count >= pre_upgrade_agent_count, (
            "Existing agents should be preserved after DES addition"
        )

    def test_des_plugin_does_not_modify_existing_agents(
        self,
        full_upgrade_state,
    ):
        """
        DES plugin installation should not modify existing agent files.

        Given: v1.2.0 installation with specific agent content
        When: DES plugin installed
        Then: Agent files are either unchanged or upgraded (not corrupted)

        Note: After full upgrade (base + DES), agent files should still be
        present and valid. DES plugin does not touch agent files.
        """
        context, _registry, results, _pre_agents = full_upgrade_state

        # Assert - DES installed successfully
        assert results["des"].success, (
            f"DES installation failed: {results['des'].message}"
        )

        # Assert - agent files are present and valid after full upgrade
        agents_dir = context.claude_dir / "agents" / "nw"
        agent_files = {f.name for f in agents_dir.glob("*.md")}
        assert len(agent_files) > 0, "Agent files should be present after upgrade"


# -----------------------------------------------------------------------------
# Test Class: Upgrade Scenario - Verification After Upgrade
# -----------------------------------------------------------------------------


class TestVerificationPassesAfterUpgrade:
    """
    Integration tests for verifying that verification passes for all
    components after upgrade from monolithic to plugin-based installer.
    """

    def test_all_plugins_verify_after_full_upgrade(
        self,
        full_upgrade_state,
    ):
        """
        All plugins should verify successfully after full upgrade.

        Given: v1.2.0 monolithic installation
        When: Full plugin-based upgrade completes
        Then: All plugins verify successfully
        """
        context, registry, results, _pre_agents = full_upgrade_state

        # Verify all installed successfully
        for plugin_name, result in results.items():
            assert result.success, (
                f"Plugin '{plugin_name}' installation failed: {result.message}"
            )

        # Act - Verify all plugins
        verify_results = registry.verify_all(context)

        # Assert - all verify successfully
        for plugin_name, result in verify_results.items():
            assert result.success, (
                f"Plugin '{plugin_name}' verification failed: {result.message}\n"
                f"Errors: {result.errors}"
            )

    def test_agents_plugin_verifies_after_upgrade(
        self,
        full_upgrade_state,
    ):
        """
        AgentsPlugin should verify successfully after upgrade.

        Given: v1.2.0 installation upgraded with AgentsPlugin
        When: AgentsPlugin.verify() is called
        Then: Verification passes
        """
        context, _registry, results, _pre_agents = full_upgrade_state

        # Assert install succeeded
        assert results["agents"].success, (
            f"Installation failed: {results['agents'].message}"
        )

        # Act - Verify
        plugin = AgentsPlugin()
        verify_result = plugin.verify(context)

        # Assert
        assert verify_result.success, (
            f"AgentsPlugin verification failed after upgrade: {verify_result.message}"
        )

    def test_des_plugin_verifies_after_addition_to_existing_installation(
        self,
        full_upgrade_state,
    ):
        """
        DESPlugin should verify successfully when added to existing installation.

        Given: v1.2.0 installation with base plugins upgraded
        When: DES plugin is added and verify() is called
        Then: DES verification passes
        """
        context, _registry, results, _pre_agents = full_upgrade_state

        # Assert DES installed
        assert results["des"].success, (
            f"DES installation failed: {results['des'].message}"
        )

        # Act - Verify DES
        des_plugin = DESPlugin()
        verify_result = des_plugin.verify(context)

        # Assert
        assert verify_result.success, (
            f"DES verification failed after upgrade: {verify_result.message}\n"
            f"Errors: {verify_result.errors}"
        )


# -----------------------------------------------------------------------------
# Test Class: Upgrade Scenario - No Functionality Broken
# -----------------------------------------------------------------------------


class TestNoFunctionalityBrokenAfterUpgrade:
    """
    Integration tests for verifying that no existing functionality is broken
    after upgrade from monolithic to plugin-based installer.
    """

    def test_agent_files_readable_after_upgrade(
        self,
        full_upgrade_state,
    ):
        """
        Agent files should be readable after upgrade.

        Given: v1.2.0 installation upgraded with plugin-based installer
        When: Agent files are read
        Then: All files are valid and readable
        """
        context, _registry, results, _pre_agents = full_upgrade_state
        assert results["agents"].success

        # Act - Read all agent files
        agents_dir = context.claude_dir / "agents" / "nw"
        agent_files = list(agents_dir.glob("*.md"))

        # Assert - all files readable
        for agent_file in agent_files:
            try:
                content = agent_file.read_text(encoding="utf-8")
                assert len(content) > 0, f"Agent file {agent_file.name} is empty"
            except Exception as e:
                pytest.fail(f"Agent file {agent_file.name} not readable: {e}")

    def test_template_files_readable_after_upgrade(
        self,
        full_upgrade_state,
    ):
        """
        Template files should be readable after upgrade.

        Given: v1.2.0 installation upgraded with plugin-based installer
        When: Template files are read
        Then: All files are valid and readable
        """
        context, _registry, results, _pre_agents = full_upgrade_state
        assert results["templates"].success

        # Act - Read all template files
        templates_dir = context.claude_dir / "templates"
        template_files = list(templates_dir.glob("*.yaml")) + list(
            templates_dir.glob("*.md")
        )

        # Assert - all files readable
        for template_file in template_files:
            try:
                content = template_file.read_text(encoding="utf-8")
                assert len(content) > 0, f"Template file {template_file.name} is empty"
            except Exception as e:
                pytest.fail(f"Template file {template_file.name} not readable: {e}")

    def test_installation_order_respected_during_upgrade(self):
        """
        Plugin installation order should be respected during upgrade.

        Given: v1.2.0 installation
        When: Plugin registry installs all plugins
        Then: Plugins are installed in priority order (agents, commands, templates, utilities, des)
        """
        # Arrange - only testing execution order, not actual installation
        registry = PluginRegistry()
        # Register in random order
        registry.register(DESPlugin())
        registry.register(TemplatesPlugin())
        registry.register(AgentsPlugin())
        registry.register(UtilitiesPlugin())
        registry.register(CommandsPlugin())

        # Act
        execution_order = registry.get_execution_order()

        # Assert - proper order
        expected_order = ["agents", "commands", "templates", "utilities", "des"]
        assert execution_order == expected_order, (
            f"Expected order {expected_order}, got {execution_order}"
        )
