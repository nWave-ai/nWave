"""
Integration tests for multi-plugin dependency resolution.

Step 01-05: Multi-Plugin Dependency Resolution Validation
Tests that all 4 wrapper plugins work together with proper dependency resolution.

Domain: Plugin Infrastructure - Multi-Plugin Orchestration
"""

import logging
from pathlib import Path

import pytest

from scripts.install.plugins.agents_plugin import AgentsPlugin
from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.install.plugins.commands_plugin import CommandsPlugin
from scripts.install.plugins.registry import PluginRegistry
from scripts.install.plugins.templates_plugin import TemplatesPlugin
from scripts.install.plugins.utilities_plugin import UtilitiesPlugin


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.multi_plugin")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    current = Path(__file__).resolve()
    return current.parents[4]  # 4 levels up from test file


@pytest.fixture
def install_context(tmp_path: Path, project_root: Path, test_logger: logging.Logger):
    """Create InstallContext for testing with real paths.

    Note: Subdirectories are created by plugins during install(),
    so we only create the base claude_dir here.
    """
    test_claude_dir = tmp_path / ".claude"
    test_claude_dir.mkdir(parents=True, exist_ok=True)

    return InstallContext(
        claude_dir=test_claude_dir,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=project_root / "nWave",
        dry_run=False,
    )


@pytest.fixture
def registry_with_all_plugins() -> PluginRegistry:
    """Create a PluginRegistry with all 4 wrapper plugins registered."""
    registry = PluginRegistry()
    registry.register(AgentsPlugin())
    registry.register(CommandsPlugin())
    registry.register(TemplatesPlugin())
    registry.register(UtilitiesPlugin())
    return registry


# -----------------------------------------------------------------------------
# Priority and Expected Order Constants
# -----------------------------------------------------------------------------

EXPECTED_PRIORITY_ORDER = ["agents", "commands", "templates", "utilities"]
AGENTS_PRIORITY = 10
COMMANDS_PRIORITY = 20
TEMPLATES_PRIORITY = 30
UTILITIES_PRIORITY = 40


# -----------------------------------------------------------------------------
# Test: Priority Ordering
# -----------------------------------------------------------------------------


def test_get_execution_order_returns_plugins_ordered_by_priority(
    registry_with_all_plugins: PluginRegistry,
):
    """
    PluginRegistry.get_execution_order() should return plugins in priority order.

    Given: Registry with all 4 wrapper plugins registered
    When: get_execution_order() is called
    Then: Order is [agents(10), commands(20), templates(30), utilities(40)]
    """
    # Act
    order = registry_with_all_plugins.get_execution_order()

    # Assert
    assert order == EXPECTED_PRIORITY_ORDER, (
        f"Expected order {EXPECTED_PRIORITY_ORDER}, got {order}"
    )


def test_execution_order_is_deterministic_across_multiple_calls(
    registry_with_all_plugins: PluginRegistry,
):
    """
    PluginRegistry.get_execution_order() should return same order every time.

    Given: Registry with all 4 wrapper plugins registered
    When: get_execution_order() is called multiple times
    Then: Same order is returned each time
    """
    # Act - call multiple times
    order1 = registry_with_all_plugins.get_execution_order()
    order2 = registry_with_all_plugins.get_execution_order()
    order3 = registry_with_all_plugins.get_execution_order()

    # Assert - all should be identical
    assert order1 == order2 == order3, (
        f"Order not deterministic: {order1} vs {order2} vs {order3}"
    )


def test_execution_order_is_deterministic_regardless_of_registration_order():
    """
    PluginRegistry.get_execution_order() should return priority order regardless
    of the order plugins were registered.

    Given: Plugins are registered in reverse priority order
    When: get_execution_order() is called
    Then: Order respects priority, not registration order
    """
    # Arrange - register in reverse order
    registry = PluginRegistry()
    registry.register(UtilitiesPlugin())  # priority=40 first
    registry.register(TemplatesPlugin())  # priority=30
    registry.register(CommandsPlugin())  # priority=20
    registry.register(AgentsPlugin())  # priority=10 last

    # Act
    order = registry.get_execution_order()

    # Assert - should still be priority order
    assert order == EXPECTED_PRIORITY_ORDER, (
        f"Expected {EXPECTED_PRIORITY_ORDER}, got {order}"
    )


# -----------------------------------------------------------------------------
# Test: Plugin Priorities
# -----------------------------------------------------------------------------


def test_agents_plugin_has_priority_10():
    """AgentsPlugin should have priority 10 (earliest execution)."""
    plugin = AgentsPlugin()
    assert plugin.priority == AGENTS_PRIORITY, (
        f"Expected priority {AGENTS_PRIORITY}, got {plugin.priority}"
    )


def test_commands_plugin_has_priority_20():
    """CommandsPlugin should have priority 20."""
    plugin = CommandsPlugin()
    assert plugin.priority == COMMANDS_PRIORITY, (
        f"Expected priority {COMMANDS_PRIORITY}, got {plugin.priority}"
    )


def test_templates_plugin_has_priority_30():
    """TemplatesPlugin should have priority 30."""
    plugin = TemplatesPlugin()
    assert plugin.priority == TEMPLATES_PRIORITY, (
        f"Expected priority {TEMPLATES_PRIORITY}, got {plugin.priority}"
    )


def test_utilities_plugin_has_priority_40():
    """UtilitiesPlugin should have priority 40 (latest execution)."""
    plugin = UtilitiesPlugin()
    assert plugin.priority == UTILITIES_PRIORITY, (
        f"Expected priority {UTILITIES_PRIORITY}, got {plugin.priority}"
    )


# -----------------------------------------------------------------------------
# Test: install_all() Orchestration
# -----------------------------------------------------------------------------


def test_install_all_installs_all_registered_plugins(
    registry_with_all_plugins: PluginRegistry,
    install_context: InstallContext,
):
    """
    PluginRegistry.install_all() should install all registered plugins successfully.

    Given: Registry with all wrapper plugins registered
    When: install_all(context) is called
    Then: All plugins install and return success
    """
    # Act
    results = registry_with_all_plugins.install_all(install_context)

    # Assert - all 4 plugins should be in results
    assert len(results) == 4, f"Expected 4 results, got {len(results)}"

    # All should be successful
    for plugin_name in EXPECTED_PRIORITY_ORDER:
        assert plugin_name in results, f"Plugin '{plugin_name}' not in results"
        result = results[plugin_name]
        assert result.success, f"Plugin '{plugin_name}' failed: {result.message}"


def test_install_all_returns_results_dictionary_keyed_by_plugin_name(
    registry_with_all_plugins: PluginRegistry,
    install_context: InstallContext,
):
    """
    PluginRegistry.install_all() should return dict with plugin names as keys.

    Given: Registry with all 4 wrapper plugins
    When: install_all() is called
    Then: Results dict has keys: agents, commands, templates, utilities
    """
    # Act
    results = registry_with_all_plugins.install_all(install_context)

    # Assert - check all expected keys present
    expected_keys = set(EXPECTED_PRIORITY_ORDER)
    actual_keys = set(results.keys())
    assert actual_keys == expected_keys, (
        f"Expected keys {expected_keys}, got {actual_keys}"
    )


def test_install_all_results_contain_plugin_result_objects(
    registry_with_all_plugins: PluginRegistry,
    install_context: InstallContext,
):
    """
    PluginRegistry.install_all() should return PluginResult objects.

    Given: Registry with all 4 wrapper plugins
    When: install_all() is called
    Then: Each result is a PluginResult with proper structure
    """
    # Act
    results = registry_with_all_plugins.install_all(install_context)

    # Assert - each result should be PluginResult
    for plugin_name, result in results.items():
        assert isinstance(result, PluginResult), (
            f"Expected PluginResult for '{plugin_name}', got {type(result)}"
        )
        assert result.plugin_name == plugin_name, (
            f"PluginResult.plugin_name mismatch: expected '{plugin_name}', got '{result.plugin_name}'"
        )


# -----------------------------------------------------------------------------
# Test: Circular Dependency Detection
# -----------------------------------------------------------------------------


class CircularPluginA(InstallationPlugin):
    """Test plugin A that depends on plugin B."""

    def __init__(self):
        super().__init__(name="circular_a", priority=10)
        self.dependencies = ["circular_b"]

    def install(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name, message="OK")

    def verify(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name, message="OK")


class CircularPluginB(InstallationPlugin):
    """Test plugin B that depends on plugin A (creates circular dependency)."""

    def __init__(self):
        super().__init__(name="circular_b", priority=20)
        self.dependencies = ["circular_a"]

    def install(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name, message="OK")

    def verify(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name, message="OK")


def test_get_execution_order_raises_error_for_circular_dependency():
    """
    PluginRegistry.get_execution_order() should raise error for circular deps.

    Given: Two plugins with circular dependency (A depends on B, B depends on A)
    When: get_execution_order() is called
    Then: ValueError is raised with 'Circular dependency' in message
    """
    # Arrange
    registry = PluginRegistry()
    registry.register(CircularPluginA())
    registry.register(CircularPluginB())

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        registry.get_execution_order()

    assert "Circular dependency" in str(exc_info.value), (
        f"Expected 'Circular dependency' in error, got: {exc_info.value}"
    )


def test_circular_dependency_error_is_descriptive():
    """
    Circular dependency error should be descriptive for debugging.

    Given: Plugins with circular dependency
    When: get_execution_order() fails
    Then: Error message helps identify the problem
    """
    # Arrange
    registry = PluginRegistry()
    registry.register(CircularPluginA())
    registry.register(CircularPluginB())

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        registry.get_execution_order()

    error_msg = str(exc_info.value)
    # Should contain helpful context
    assert len(error_msg) > 10, "Error message should be descriptive"


# -----------------------------------------------------------------------------
# Test: Missing Dependency Detection
# -----------------------------------------------------------------------------


class PluginWithMissingDep(InstallationPlugin):
    """Test plugin that depends on a non-existent plugin."""

    def __init__(self):
        super().__init__(name="missing_dep_plugin", priority=10)
        self.dependencies = ["non_existent_plugin"]

    def install(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name, message="OK")

    def verify(self, context: InstallContext) -> PluginResult:
        return PluginResult(success=True, plugin_name=self.name, message="OK")


def test_get_execution_order_raises_error_for_missing_dependency():
    """
    PluginRegistry.get_execution_order() should raise error for missing deps.

    Given: A plugin depends on a non-registered plugin
    When: get_execution_order() is called
    Then: ValueError is raised indicating missing dependency
    """
    # Arrange
    registry = PluginRegistry()
    registry.register(PluginWithMissingDep())

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        registry.get_execution_order()

    error_msg = str(exc_info.value)
    assert "missing" in error_msg.lower() or "depends on" in error_msg.lower(), (
        f"Expected error about missing dependency, got: {error_msg}"
    )


# -----------------------------------------------------------------------------
# Test: Empty Registry
# -----------------------------------------------------------------------------


def test_get_execution_order_returns_empty_list_for_empty_registry():
    """
    PluginRegistry.get_execution_order() should return empty list when no plugins.

    Given: Empty PluginRegistry
    When: get_execution_order() is called
    Then: Empty list is returned
    """
    # Arrange
    registry = PluginRegistry()

    # Act
    order = registry.get_execution_order()

    # Assert
    assert order == [], f"Expected empty list, got {order}"


def test_install_all_returns_empty_dict_for_empty_registry(
    install_context: InstallContext,
):
    """
    PluginRegistry.install_all() should return empty dict when no plugins.

    Given: Empty PluginRegistry
    When: install_all() is called
    Then: Empty dict is returned
    """
    # Arrange
    registry = PluginRegistry()

    # Act
    results = registry.install_all(install_context)

    # Assert
    assert results == {}, f"Expected empty dict, got {results}"


# -----------------------------------------------------------------------------
# Test: Single Plugin
# -----------------------------------------------------------------------------


def test_get_execution_order_works_with_single_plugin():
    """
    PluginRegistry.get_execution_order() should work with single plugin.

    Given: Registry with only AgentsPlugin
    When: get_execution_order() is called
    Then: List with single plugin name is returned
    """
    # Arrange
    registry = PluginRegistry()
    registry.register(AgentsPlugin())

    # Act
    order = registry.get_execution_order()

    # Assert
    assert order == ["agents"], f"Expected ['agents'], got {order}"
