"""
Common Step Definitions for DES Installation Bug Tests.

This module contains shared step definitions used across multiple feature files:
- Test environment setup
- DES installation verification
- Basic precondition steps

Domain: Shared Infrastructure
"""

import os
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, then, when


# -----------------------------------------------------------------------------
# Given Steps: Environment Setup
# -----------------------------------------------------------------------------


@given("the test environment is initialized")
def test_environment_initialized(test_context: dict, project_root: Path):
    """Initialize the test environment with required context."""
    test_context["project_root"] = project_root
    test_context["initialized"] = True


@given("a temporary Claude config directory exists")
def temp_claude_dir_exists(temp_claude_dir: Path, test_context: dict):
    """Ensure temporary Claude config directory exists and store in context."""
    assert temp_claude_dir.exists(), f"Temp Claude dir not created: {temp_claude_dir}"
    test_context["claude_dir"] = temp_claude_dir


@given("a temporary project directory exists")
def temp_project_dir_exists(temp_project_dir: Path, test_context: dict):
    """Ensure temporary project directory exists and store in context."""
    assert temp_project_dir.exists(), (
        f"Temp project dir not created: {temp_project_dir}"
    )
    test_context["project_dir"] = temp_project_dir
    test_context["original_cwd"] = os.getcwd()

    # Change to project directory so config file resolution works
    os.chdir(temp_project_dir)


@given("the DES plugin is installed")
def des_plugin_is_installed(installed_des_path: Path, test_context: dict):
    """Verify DES plugin is installed at expected location."""
    # Note: This checks the REAL installation, not a test installation
    # This is intentional - we're testing the actual installed DES
    if not installed_des_path.exists():
        pytest.skip(f"DES not installed at {installed_des_path} - skipping test")

    test_context["installed_des_path"] = installed_des_path


@given(parsers.parse('DES is installed at "{path}"'))
def des_installed_at_path(path: str, test_context: dict):
    """Verify DES is installed at the specified path."""
    expanded_path = Path(path).expanduser()

    if not expanded_path.exists():
        pytest.skip(f"DES not installed at {expanded_path} - cannot test bug")

    test_context["installed_des_path"] = expanded_path


# -----------------------------------------------------------------------------
# When Steps: Common Actions
# -----------------------------------------------------------------------------


@when("I check the installation status")
def check_installation_status(test_context: dict):
    """Check the DES installation status."""
    des_path = test_context.get("installed_des_path")
    if des_path:
        test_context["installation_exists"] = des_path.exists()
        test_context["has_init"] = (
            (des_path / "__init__.py").exists() if des_path.exists() else False
        )
    else:
        test_context["installation_exists"] = False
        test_context["has_init"] = False


# -----------------------------------------------------------------------------
# Then Steps: Common Assertions
# -----------------------------------------------------------------------------


@then(parsers.parse('the DES module should be present at "{path}"'))
def des_module_present_at_path(path: str, test_context: dict):
    """Verify DES module exists at the specified path."""
    expanded_path = Path(path).expanduser()

    assert expanded_path.exists(), (
        f"DES module not found at {expanded_path}. "
        f"Expected installation directory to exist."
    )

    # Verify it looks like a Python package
    init_file = expanded_path / "__init__.py"
    assert init_file.exists(), (
        f"DES module at {expanded_path} missing __init__.py - "
        f"not a valid Python package"
    )


@then("the settings.local.json file should exist")
def settings_file_exists(test_context: dict):
    """Verify settings.local.json exists in Claude config (temp or real)."""
    claude_dir = test_context.get("claude_dir")
    if claude_dir:
        # Test environment
        settings_file = claude_dir / "settings.local.json"
    else:
        # Real installation
        settings_file = Path.home() / ".claude" / "settings.local.json"

    assert settings_file.exists(), (
        f"settings.local.json not found at {settings_file}. "
        f"DES installation incomplete."
    )


@then("the real settings.local.json file should exist")
def real_settings_file_exists():
    """Verify settings.local.json exists at the real Claude config location."""
    settings_file = Path.home() / ".claude" / "settings.local.json"

    assert settings_file.exists(), (
        f"settings.local.json not found at {settings_file}. "
        f"DES installation incomplete."
    )


@then("I should be able to import from scripts.install.plugins.des_plugin")
def can_import_des_plugin():
    """Verify DESPlugin can be imported."""
    try:
        from scripts.install.plugins.des_plugin import DESPlugin

        assert DESPlugin is not None, "DESPlugin import returned None"

        # Verify key methods exist
        plugin = DESPlugin()
        assert hasattr(plugin, "install"), "DESPlugin missing install() method"
        assert hasattr(plugin, "uninstall"), "DESPlugin missing uninstall() method"
        assert hasattr(plugin, "verify"), "DESPlugin missing verify() method"
    except ImportError as e:
        pytest.fail(f"Failed to import DESPlugin: {e}")
