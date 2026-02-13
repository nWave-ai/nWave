"""
Unit Tests for DESPlugin (Step 03-03 - Validation Tests).

Tests focused on DES import validation and script execution verification.
These tests validate DESPlugin.verify() behavior under various conditions.

Domain: Plugin Infrastructure - DES Plugin Verification
"""

import logging
from pathlib import Path

import pytest

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.des_plugin import DESPlugin


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.des_plugin_unit")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def project_root() -> Path:
    """Return the nWave project root directory."""
    current = Path(__file__).resolve()
    return current.parents[4]


@pytest.fixture
def clean_test_directory(tmp_path: Path) -> Path:
    """Provide a clean test installation directory simulating ~/.claude."""
    test_dir = tmp_path / ".claude"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


@pytest.fixture
def install_context(
    clean_test_directory: Path, project_root: Path, test_logger: logging.Logger
) -> InstallContext:
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
def des_installed_via_symlink(install_context: InstallContext, shared_des_source: Path):
    """
    Install DES module into the test context via symlink to shared copy.

    Uses a session-scoped shared DES source (copied once) instead of
    shutil.copytree per test (~3.5s saved per test).
    """
    target_des = install_context.claude_dir / "lib" / "python" / "des"
    target_des.parent.mkdir(parents=True, exist_ok=True)
    target_des.symlink_to(shared_des_source)
    return install_context


# -----------------------------------------------------------------------------
# Test: DESPlugin Initialization
# -----------------------------------------------------------------------------


class TestDESPluginInitialization:
    """Unit tests for DESPlugin initialization."""

    def test_des_plugin_has_correct_name(self):
        """DESPlugin should have name 'des'."""
        plugin = DESPlugin()
        assert plugin.name == "des"

    def test_des_plugin_has_correct_priority(self):
        """DESPlugin should have priority 50 (after core plugins)."""
        plugin = DESPlugin()
        assert plugin.priority == 50

    def test_des_plugin_declares_correct_dependencies(self):
        """DESPlugin should depend on templates and utilities."""
        plugin = DESPlugin()
        assert plugin.dependencies == ["templates", "utilities"]

    def test_des_plugin_defines_expected_scripts(self):
        """DESPlugin should define the expected DES scripts."""
        plugin = DESPlugin()
        assert "check_stale_phases.py" in plugin.DES_SCRIPTS
        assert "scope_boundary_check.py" in plugin.DES_SCRIPTS

    def test_des_plugin_defines_expected_templates(self):
        """DESPlugin should define the expected DES templates."""
        plugin = DESPlugin()
        assert ".pre-commit-config-nwave.yaml" in plugin.DES_TEMPLATES
        assert ".des-audit-README.md" in plugin.DES_TEMPLATES


# -----------------------------------------------------------------------------
# Test: DESPlugin.verify() Module Import Validation
# -----------------------------------------------------------------------------


class TestDESPluginVerifyModuleImport:
    """Unit tests for DESPlugin.verify() module import validation."""

    def test_verify_fails_when_des_module_import_fails(
        self, install_context: InstallContext
    ):
        """verify() should fail if DES module cannot be imported."""
        plugin = DESPlugin()

        # Create lib/python/des directory but without proper module
        lib_python = install_context.claude_dir / "lib" / "python" / "des"
        lib_python.mkdir(parents=True, exist_ok=True)

        # Create an __init__.py that doesn't export DESOrchestrator
        init_file = lib_python / "__init__.py"
        init_file.write_text("# Empty module\n")

        # Create scripts and templates to isolate the module import test
        scripts_dir = install_context.claude_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        for script in plugin.DES_SCRIPTS:
            (scripts_dir / script).touch()

        templates_dir = install_context.claude_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        for template in plugin.DES_TEMPLATES:
            (templates_dir / template).touch()

        result = plugin.verify(install_context)

        assert not result.success
        assert "DES module import failed" in result.errors[0]

    def test_verify_succeeds_when_des_module_is_importable(
        self, des_installed_via_symlink: InstallContext
    ):
        """verify() should succeed when DES module is properly installed."""
        import json

        plugin = DESPlugin()
        install_context = des_installed_via_symlink

        # Create scripts
        scripts_dir = install_context.claude_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        for script in plugin.DES_SCRIPTS:
            (scripts_dir / script).touch()

        # Create templates
        templates_dir = install_context.claude_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        for template in plugin.DES_TEMPLATES:
            (templates_dir / template).touch()

        # Create settings.json with hooks (verify() checks settings.json)
        lib_path = install_context.claude_dir / "lib" / "python"
        settings_file = install_context.claude_dir / "settings.json"
        hooks_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": {"tool": "Task"},
                        "command": "python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter pretask",
                        "env": {"PYTHONPATH": str(lib_path)},
                    }
                ],
                "SubagentStop": [
                    {
                        "command": "python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter subagent_stop",
                        "env": {"PYTHONPATH": str(lib_path)},
                    }
                ],
            }
        }
        settings_file.write_text(json.dumps(hooks_config, indent=2))

        result = plugin.verify(install_context)

        assert result.success
        assert "verification passed" in result.message.lower()


# -----------------------------------------------------------------------------
# Test: DESPlugin.verify() Scripts Validation
# -----------------------------------------------------------------------------


class TestDESPluginVerifyScripts:
    """Unit tests for DESPlugin.verify() script presence validation."""

    def test_verify_fails_when_check_stale_phases_missing(
        self, des_installed_via_symlink: InstallContext
    ):
        """verify() should fail if check_stale_phases.py is missing."""
        plugin = DESPlugin()
        install_context = des_installed_via_symlink

        # Create scripts directory but only scope_boundary_check.py
        scripts_dir = install_context.claude_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "scope_boundary_check.py").touch()
        # Missing: check_stale_phases.py

        # Create templates
        templates_dir = install_context.claude_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        for template in plugin.DES_TEMPLATES:
            (templates_dir / template).touch()

        result = plugin.verify(install_context)

        assert not result.success
        assert any("check_stale_phases.py" in error for error in result.errors)

    def test_verify_fails_when_scope_boundary_check_missing(
        self, des_installed_via_symlink: InstallContext
    ):
        """verify() should fail if scope_boundary_check.py is missing."""
        plugin = DESPlugin()
        install_context = des_installed_via_symlink

        # Create scripts directory but only check_stale_phases.py
        scripts_dir = install_context.claude_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "check_stale_phases.py").touch()
        # Missing: scope_boundary_check.py

        # Create templates
        templates_dir = install_context.claude_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        for template in plugin.DES_TEMPLATES:
            (templates_dir / template).touch()

        result = plugin.verify(install_context)

        assert not result.success
        assert any("scope_boundary_check.py" in error for error in result.errors)


# -----------------------------------------------------------------------------
# Test: DESPlugin.verify() Templates Validation
# -----------------------------------------------------------------------------


class TestDESPluginVerifyTemplates:
    """Unit tests for DESPlugin.verify() template presence validation."""

    def test_verify_fails_when_des_audit_readme_missing(
        self, des_installed_via_symlink: InstallContext
    ):
        """verify() should fail if .des-audit-README.md is missing."""
        plugin = DESPlugin()
        install_context = des_installed_via_symlink

        # Create scripts
        scripts_dir = install_context.claude_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        for script in plugin.DES_SCRIPTS:
            (scripts_dir / script).touch()

        # Create templates directory but only pre-commit config
        templates_dir = install_context.claude_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        (templates_dir / ".pre-commit-config-nwave.yaml").touch()
        # Missing: .des-audit-README.md

        result = plugin.verify(install_context)

        assert not result.success
        assert any(".des-audit-README.md" in error for error in result.errors)

    def test_verify_fails_when_precommit_config_missing(
        self, des_installed_via_symlink: InstallContext
    ):
        """verify() should fail if .pre-commit-config-nwave.yaml is missing."""
        plugin = DESPlugin()
        install_context = des_installed_via_symlink

        # Create scripts
        scripts_dir = install_context.claude_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        for script in plugin.DES_SCRIPTS:
            (scripts_dir / script).touch()

        # Create templates directory but only des-audit-README
        templates_dir = install_context.claude_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        (templates_dir / ".des-audit-README.md").touch()
        # Missing: .pre-commit-config-nwave.yaml

        result = plugin.verify(install_context)

        assert not result.success
        assert any(".pre-commit-config-nwave.yaml" in error for error in result.errors)


# -----------------------------------------------------------------------------
# Test: DESPlugin.verify() Complete Validation
# -----------------------------------------------------------------------------


class TestDESPluginVerifyComplete:
    """Unit tests for complete DESPlugin.verify() validation."""

    def test_verify_returns_all_errors_when_multiple_items_missing(
        self, install_context: InstallContext
    ):
        """verify() should return all errors when multiple items are missing."""
        plugin = DESPlugin()

        # Create empty directories only
        (install_context.claude_dir / "lib" / "python" / "des").mkdir(
            parents=True, exist_ok=True
        )
        (install_context.claude_dir / "scripts").mkdir(parents=True, exist_ok=True)
        (install_context.claude_dir / "templates").mkdir(parents=True, exist_ok=True)

        # Write a minimal __init__.py that won't have DESOrchestrator
        init_file = (
            install_context.claude_dir / "lib" / "python" / "des" / "__init__.py"
        )
        init_file.write_text("# Empty\n")

        result = plugin.verify(install_context)

        assert not result.success
        # Should have errors for module import, scripts, and templates
        assert len(result.errors) >= 1
        # At minimum, module import should fail
        assert any("DES module" in error for error in result.errors)

    def test_verify_message_contains_success_indicators_on_pass(
        self, des_installed_via_symlink: InstallContext
    ):
        """verify() success message should indicate what was verified."""
        import json

        plugin = DESPlugin()
        install_context = des_installed_via_symlink

        scripts_dir = install_context.claude_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        for script in plugin.DES_SCRIPTS:
            (scripts_dir / script).touch()

        templates_dir = install_context.claude_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        for template in plugin.DES_TEMPLATES:
            (templates_dir / template).touch()

        # Create settings.json with hooks (verify() checks settings.json)
        lib_path = install_context.claude_dir / "lib" / "python"
        settings_file = install_context.claude_dir / "settings.json"
        hooks_config = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": {"tool": "Task"},
                        "command": "python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter pretask",
                        "env": {"PYTHONPATH": str(lib_path)},
                    }
                ],
                "SubagentStop": [
                    {
                        "command": "python3 -m des.adapters.drivers.hooks.claude_code_hook_adapter subagent_stop",
                        "env": {"PYTHONPATH": str(lib_path)},
                    }
                ],
            }
        }
        settings_file.write_text(json.dumps(hooks_config, indent=2))

        result = plugin.verify(install_context)

        assert result.success
        assert (
            "module" in result.message.lower()
            or "verification" in result.message.lower()
        )
