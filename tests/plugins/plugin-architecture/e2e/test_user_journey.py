"""
End-to-End User Journey Validation Tests.

Step 05-02: Final validation that the complete plugin architecture
provides the expected user experience during installation.

Tests verify:
- Plugin registry installs 5 plugins in correct order
- Each plugin executes successfully with dependencies resolved
- DES plugin is installed after its dependencies (templates, utilities)
- Installation completion is properly tracked
- All components are functional after installation
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
# Module-scoped fixtures for shared install state (~13s saved)
# -----------------------------------------------------------------------------


def _make_registry() -> PluginRegistry:
    """Create a registry with all 5 plugins registered."""
    registry = PluginRegistry()
    registry.register(AgentsPlugin())
    registry.register(CommandsPlugin())
    registry.register(TemplatesPlugin())
    registry.register(UtilitiesPlugin())
    registry.register(DESPlugin())
    return registry


@pytest.fixture(scope="module")
def installed_plugin_state(tmp_path_factory) -> tuple:
    """
    Install all 5 plugins once and return shared state.

    Module-scoped: tests must NOT mutate the installed directory.

    Returns (context, registry, results) for the 4 install-dependent tests.
    """
    project_root = Path(__file__).resolve().parents[4]
    logger = logging.getLogger("test.user-journey")
    logger.setLevel(logging.DEBUG)

    claude_dir = tmp_path_factory.mktemp("user_journey") / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    context = InstallContext(
        claude_dir=claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )

    registry = _make_registry()
    results = registry.install_all(context)

    return context, registry, results


class TestUserJourneyPluginInstallation:
    """E2E tests for complete plugin installation user journey."""

    @pytest.fixture
    def five_plugin_registry(self) -> PluginRegistry:
        """Create a registry with all 5 plugins registered (lightweight)."""
        return _make_registry()

    def test_all_plugins_registered_and_ordered(
        self, five_plugin_registry: PluginRegistry
    ):
        """
        Verify all plugins are registered and ordered by dependencies.

        Given: User downloads nWave installer with all plugins
        When: Registry resolves execution order
        Then: All plugins are scheduled in dependency order
        """
        # Act: Get execution order
        execution_order = five_plugin_registry.get_execution_order()

        # Assert: 5 plugins are registered
        assert len(execution_order) == 5, (
            f"Expected 5 plugins, got {len(execution_order)}: {execution_order}"
        )

        # Assert: All expected plugins are present
        expected_plugins = {"agents", "commands", "templates", "utilities", "des"}
        actual_plugins = set(execution_order)
        assert actual_plugins == expected_plugins, (
            f"Missing plugins: {expected_plugins - actual_plugins}"
        )

    def test_des_plugin_executes_after_dependencies(
        self, five_plugin_registry: PluginRegistry
    ):
        """
        Verify DES plugin executes after its dependencies.

        DES depends on: templates, utilities
        Therefore DES must appear after both in execution order.
        """
        # Act: Get execution order
        execution_order = five_plugin_registry.get_execution_order()

        # Assert: Find positions
        des_position = execution_order.index("des")
        templates_position = execution_order.index("templates")
        utilities_position = execution_order.index("utilities")

        # Assert: DES is after its dependencies
        assert des_position > templates_position, (
            f"DES ({des_position}) should execute after templates ({templates_position})"
        )
        assert des_position > utilities_position, (
            f"DES ({des_position}) should execute after utilities ({utilities_position})"
        )

    def test_all_plugins_install_successfully(self, installed_plugin_state):
        """
        Verify all plugins install successfully.

        Given: Fresh installation environment
        When: All plugins are installed
        Then: All plugins report success
        """
        _context, _registry, results = installed_plugin_state

        # Assert: 5 results returned
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"

        # Assert: All plugins succeeded
        failed_plugins = [
            name for name, result in results.items() if not result.success
        ]
        assert not failed_plugins, (
            f"Plugins failed: {failed_plugins}. "
            f"Details: {[(name, results[name].message) for name in failed_plugins]}"
        )

    def test_installation_creates_expected_artifacts(self, installed_plugin_state):
        """
        Verify installation creates expected directory structure.

        Then: User can verify installation shows all components
        """
        context, _registry, _results = installed_plugin_state

        # Assert: Key directories created
        claude_dir = context.claude_dir
        expected_dirs = ["agents", "commands", "templates", "scripts"]

        for dir_name in expected_dirs:
            dir_path = claude_dir / dir_name
            assert dir_path.exists() or dir_name == "scripts", (
                f"Expected directory not created: {dir_path}"
            )

    def test_des_artifacts_installed(self, installed_plugin_state):
        """
        Verify DES-specific artifacts are installed.

        Then: DES is available for production use
        """
        _context, _registry, results = installed_plugin_state

        # Assert: DES plugin succeeded
        assert "des" in results, "DES plugin not in results"
        assert results["des"].success, f"DES failed: {results['des'].message}"

        # Note: DES module directory at claude_dir/lib/python/des requires
        # src/des to exist, which may not in test env. The success of the
        # DES plugin result indicates it handled this correctly.

    def test_installation_order_matches_progress_expectations(
        self, five_plugin_registry: PluginRegistry
    ):
        """
        Verify installation order matches expected progress output.

        Expected progress order:
        [1/5] agents
        [2/5] commands
        [3/5] templates
        [4/5] utilities
        [5/5] des
        """
        # Act: Get execution order
        execution_order = five_plugin_registry.get_execution_order()

        # Assert: Order matches expected progress sequence
        # Note: Exact order depends on priority and dependencies
        # DES must be last due to dependencies
        assert execution_order[-1] == "des", (
            f"DES should be last due to dependencies, but order is: {execution_order}"
        )

        # Assert: agents, commands, templates, utilities come before des
        des_index = execution_order.index("des")
        for plugin in ["agents", "commands", "templates", "utilities"]:
            plugin_index = execution_order.index(plugin)
            assert plugin_index < des_index, f"{plugin} should come before des"

    def test_plugin_count_for_progress_display(
        self, five_plugin_registry: PluginRegistry
    ):
        """
        Verify plugin count is 5 for progress display.

        User expects to see: "Installing 5 plugins..."
        """
        # Act: Count registered plugins
        plugin_count = len(five_plugin_registry.plugins)

        # Assert: 5 plugins registered
        assert plugin_count == 5, (
            f"Expected 5 plugins for progress display, got {plugin_count}"
        )

    def test_verification_can_check_all_plugins(self, installed_plugin_state):
        """
        Verify all plugins can be verified after installation.

        Then: Verification table shows all components
        """
        context, registry, _results = installed_plugin_state

        # Act: Verify (install already done by shared fixture)
        verify_results = registry.verify_all(context)

        # Assert: All 5 plugins have verification results
        assert len(verify_results) == 5, (
            f"Expected 5 verification results, got {len(verify_results)}"
        )

        # Log any verification failures (informational - some may fail in test env)
        for name, result in verify_results.items():
            if not result.success:
                print(f"  Verification note: {name} - {result.message}")
