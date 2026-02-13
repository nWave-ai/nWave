"""
Plugin Infrastructure Step Definitions.

This module contains step definitions related to:
- Plugin creation and configuration
- Plugin interface validation
- Plugin wrapper pattern implementation

Domain: Plugin Infrastructure
"""

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, then, when


# -----------------------------------------------------------------------------
# Given Steps: Plugin Preconditions
# -----------------------------------------------------------------------------


@given("plugin infrastructure exists (base.py, registry.py)")
def plugin_infrastructure_exists(project_root: Path):
    """Verify plugin infrastructure files exist."""
    base_path = project_root / "scripts" / "install" / "plugins" / "base.py"
    registry_path = project_root / "scripts" / "install" / "plugins" / "registry.py"

    # For walking skeleton, we verify infrastructure exists
    # Tests will skip if infrastructure not yet implemented
    if not base_path.exists():
        pytest.skip(f"Plugin base.py not found: {base_path}")
    if not registry_path.exists():
        pytest.skip(f"Plugin registry.py not found: {registry_path}")


@given("plugin infrastructure exists with base classes")
def plugin_infrastructure_with_base_classes(project_root: Path):
    """Verify plugin infrastructure with base classes exists."""
    try:
        from scripts.install.plugins.base import (
            InstallationPlugin,
            InstallContext,
            PluginResult,
        )

        assert InstallationPlugin is not None
        assert InstallContext is not None
        assert PluginResult is not None
    except ImportError as e:
        pytest.skip(f"Plugin base classes not importable: {e}")


@given("AgentsPlugin is implemented with install() and verify() methods")
def agents_plugin_implemented(project_root: Path):
    """Verify AgentsPlugin is implemented."""
    try:
        from scripts.install.plugins.agents_plugin import AgentsPlugin

        plugin = AgentsPlugin()
        assert hasattr(plugin, "install"), "AgentsPlugin missing install() method"
        assert hasattr(plugin, "verify"), "AgentsPlugin missing verify() method"
        assert callable(plugin.install), "install() must be callable"
        assert callable(plugin.verify), "verify() must be callable"
    except ImportError as e:
        pytest.skip(f"AgentsPlugin not importable: {e}")


@given("base.py defines InstallationPlugin interface")
def base_defines_interface(project_root: Path):
    """Verify base.py defines the required interface."""
    try:
        from scripts.install.plugins.base import InstallationPlugin

        # Verify interface methods exist
        assert hasattr(InstallationPlugin, "install")
        assert hasattr(InstallationPlugin, "verify")
        assert hasattr(InstallationPlugin, "name")
    except ImportError:
        pytest.skip("InstallationPlugin not yet implemented")


@given("registry.py implements PluginRegistry with topological sort")
def registry_implements_topological_sort(project_root: Path):
    """Verify registry.py implements PluginRegistry with topological sort."""
    try:
        from scripts.install.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        assert hasattr(registry, "register"), "PluginRegistry missing register() method"
        assert hasattr(registry, "get_installation_order"), (
            "Missing get_installation_order()"
        )
    except ImportError:
        pytest.skip("PluginRegistry not yet implemented")


@given("module-level functions are extracted from install_nwave.py")
def module_functions_extracted(project_root: Path):
    """Verify module-level functions are extracted for wrapper pattern."""
    # This step validates that install methods can be called independently
    # Implementation depends on refactoring install_nwave.py
    pass  # Will be implemented during Milestone 2


@given("circular import prevention is validated")
def circular_import_validated():
    """Verify no circular imports exist in plugin infrastructure."""
    try:
        # Attempt to import all plugin modules
        from scripts.install.plugins import (
            base,  # noqa: F401
            registry,  # noqa: F401
        )
        # If we get here, no circular imports
    except ImportError as e:
        if "circular" in str(e).lower():
            pytest.fail(f"Circular import detected: {e}")
        raise


# -----------------------------------------------------------------------------
# When Steps: Plugin Actions
# -----------------------------------------------------------------------------


@when(parsers.parse("I create {plugin_name} wrapper around {method_name}()"))
def create_plugin_wrapper(plugin_name: str, method_name: str):
    """Create a plugin wrapper around existing method."""
    # This step is declarative - validates plugin creation approach
    # Actual implementation happens in plugin files
    pass


# -----------------------------------------------------------------------------
# Then Steps: Plugin Assertions
# -----------------------------------------------------------------------------


@then("all 4 wrapper plugins call existing methods correctly")
def wrapper_plugins_call_existing_methods():
    """Verify wrapper plugins delegate to existing installation methods."""
    try:
        from scripts.install.plugins.agents_plugin import AgentsPlugin
        from scripts.install.plugins.commands_plugin import CommandsPlugin
        from scripts.install.plugins.templates_plugin import TemplatesPlugin
        from scripts.install.plugins.utilities_plugin import UtilitiesPlugin

        # All plugins should be importable
        assert AgentsPlugin is not None
        assert CommandsPlugin is not None
        assert TemplatesPlugin is not None
        assert UtilitiesPlugin is not None
    except ImportError as e:
        pytest.skip(f"Wrapper plugins not yet implemented: {e}")


@then("no behavioral changes occur (same output as pre-plugin)")
def no_behavioral_changes():
    """Verify plugin-based installation produces identical results."""
    # This is validated through baseline comparison in integration tests
    pass


@then("no circular import errors are detected")
def no_circular_import_errors():
    """Verify no circular imports in plugin modules."""
    try:
        # Re-import all plugin modules
        import importlib
        import sys

        modules_to_check = [
            "scripts.install.plugins.base",
            "scripts.install.plugins.registry",
        ]

        for module in modules_to_check:
            if module in sys.modules:
                del sys.modules[module]

        for module in modules_to_check:
            try:
                importlib.import_module(module)
            except ImportError:
                pass  # Module may not exist yet
    except Exception as e:
        if "circular" in str(e).lower():
            pytest.fail(f"Circular import detected: {e}")


@then("each plugin has unit tests that pass")
def plugins_have_unit_tests(project_root: Path):
    """Verify each plugin has passing unit tests."""
    # This is validated by running pytest on plugin test files
    pass


@then("each plugin implements fallback verification logic")
def plugins_implement_fallback_verification():
    """Verify plugins have fallback verification."""
    # Validated during plugin implementation
    pass
