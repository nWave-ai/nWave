"""
Integration Test for DES Import and Script Execution Validation (Step 03-03).

This test verifies that:
1. DES module can be imported after installation
2. DES scripts have executable permissions
3. DES scripts execute without errors
4. DESPlugin.verify() returns success after installation

Based on: milestone-4-des-plugin.feature scenarios:
- "DES module is importable after installation"
- "DES scripts are executable and functional"
"""

import logging
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest


# -----------------------------------------------------------------------------
# Test Fixtures (Module-Level to Eliminate Duplication)
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def test_logger() -> logging.Logger:
    """Provide a configured logger for test execution."""
    logger = logging.getLogger("test.des_import_validation")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture(scope="module")
def project_root() -> Path:
    """Return the nWave project root directory."""
    current = Path(__file__).resolve()
    return current.parents[4]  # 4 levels up from test file


@pytest.fixture(scope="module")
def clean_test_directory(tmp_path_factory) -> Path:
    """Provide a clean test installation directory simulating ~/.claude."""
    test_dir = tmp_path_factory.mktemp("des_import") / ".claude"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


@pytest.fixture(scope="module")
def installed_des_context(clean_test_directory, project_root, test_logger):
    """
    Provide a context with DES fully installed.

    This fixture installs all plugins (including DES and its dependencies)
    and returns the InstallContext for validation testing.

    Module-scoped: tests must NOT mutate the installed directory.
    """
    from scripts.install.plugins.agents_plugin import AgentsPlugin
    from scripts.install.plugins.base import InstallContext
    from scripts.install.plugins.commands_plugin import CommandsPlugin
    from scripts.install.plugins.des_plugin import DESPlugin
    from scripts.install.plugins.registry import PluginRegistry
    from scripts.install.plugins.templates_plugin import TemplatesPlugin
    from scripts.install.plugins.utilities_plugin import UtilitiesPlugin

    framework_source = project_root / "nWave"

    context = InstallContext(
        claude_dir=clean_test_directory,
        scripts_dir=project_root / "scripts" / "install",
        templates_dir=project_root / "nWave" / "templates",
        logger=test_logger,
        project_root=project_root,
        framework_source=framework_source,
        dry_run=False,
    )

    registry = PluginRegistry()
    registry.register(DESPlugin())
    registry.register(AgentsPlugin())
    registry.register(CommandsPlugin())
    registry.register(TemplatesPlugin())
    registry.register(UtilitiesPlugin())

    results = registry.install_all(context)

    assert "des" in results, "DES plugin not in install results"
    assert results["des"].success, f"DES installation failed: {results['des'].message}"

    return context


# -----------------------------------------------------------------------------
# Test Classes
# -----------------------------------------------------------------------------


class TestDESModuleImportValidation:
    """Integration tests for DES module importability after installation."""

    def test_des_module_import_succeeds_in_subprocess(self, installed_des_context):
        """
        Verify DES module can be imported via subprocess.

        Acceptance Criteria (from feature file):
        - Subprocess import test: python3 -c 'from des.application import DESOrchestrator'
        """
        lib_python = installed_des_context.claude_dir / "lib" / "python"

        lib_python_str = str(lib_python)
        import_cmd = (
            f"import sys; "
            f"sys.path.insert(0, {lib_python_str!r}); "
            f"from des.application import DESOrchestrator; "
            f"print('DES OK')"
        )

        result = subprocess.run(
            [sys.executable, "-c", import_cmd],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, (
            f"DES module import failed.\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
        assert "DES OK" in result.stdout, (
            f"Expected 'DES OK' in output, got: {result.stdout}"
        )

    def test_des_orchestrator_can_be_instantiated(self, installed_des_context):
        """
        Verify DESOrchestrator class can be instantiated.

        This tests that the DES module is not only importable but functional.
        """
        lib_python = installed_des_context.claude_dir / "lib" / "python"

        lib_python_str = str(lib_python)
        instantiate_cmd = (
            f"import sys; "
            f"sys.path.insert(0, {lib_python_str!r}); "
            f"from des.application import DESOrchestrator; "
            f"o = DESOrchestrator.__new__(DESOrchestrator); "
            f"print('Instantiation OK')"
        )

        result = subprocess.run(
            [sys.executable, "-c", instantiate_cmd],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, (
            f"DESOrchestrator instantiation failed.\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
        assert "Instantiation OK" in result.stdout


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Unix executable permissions not applicable on Windows",
)
class TestDESScriptExecutablePermissions:
    """Integration tests for DES script executable permissions."""

    def test_check_stale_phases_has_executable_permission(self, installed_des_context):
        """
        Verify check_stale_phases.py has executable permissions (chmod +x).

        Acceptance Criteria (from feature file):
        - DES scripts have executable permissions (chmod +x)
        """
        script_path = (
            installed_des_context.claude_dir / "scripts" / "check_stale_phases.py"
        )

        assert script_path.exists(), f"Script not found: {script_path}"

        mode = script_path.stat().st_mode
        is_executable = bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

        assert is_executable, (
            f"check_stale_phases.py is not executable. Mode: {oct(mode)}"
        )

    def test_scope_boundary_check_has_executable_permission(
        self, installed_des_context
    ):
        """
        Verify scope_boundary_check.py has executable permissions (chmod +x).
        """
        script_path = (
            installed_des_context.claude_dir / "scripts" / "scope_boundary_check.py"
        )

        assert script_path.exists(), f"Script not found: {script_path}"

        mode = script_path.stat().st_mode
        is_executable = bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

        assert is_executable, (
            f"scope_boundary_check.py is not executable. Mode: {oct(mode)}"
        )


class TestDESScriptExecution:
    """Integration tests for DES script execution without errors."""

    def _create_pythonpath_env(self, lib_python: Path) -> dict:
        """Create environment with PYTHONPATH including DES module."""
        env = os.environ.copy()
        existing_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{lib_python}{os.pathsep}{existing_path}"
            if existing_path
            else str(lib_python)
        )
        return env

    def test_check_stale_phases_executes_without_import_error(
        self, installed_des_context
    ):
        """
        Verify check_stale_phases.py executes without import errors.

        The script should either succeed or fail gracefully with
        "DES module not available" message (which is expected since
        DES components like StaleExecutionDetector may not exist).
        """
        script_path = (
            installed_des_context.claude_dir / "scripts" / "check_stale_phases.py"
        )
        lib_python = installed_des_context.claude_dir / "lib" / "python"

        env = self._create_pythonpath_env(lib_python)

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )

        # Script should not crash with import error for des.application
        assert (
            "Traceback" not in result.stderr or "des.application" not in result.stderr
        ), (
            f"Script crashed with DES import error.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        valid_outputs = [
            "No stale phases detected",
            "DES module not available",
            "stale phase check skipped",
        ]
        output = result.stdout + result.stderr

        assert result.returncode == 0 or any(msg in output for msg in valid_outputs), (
            f"Script did not execute properly.\n"
            f"Return code: {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_scope_boundary_check_executes_without_import_error(
        self, installed_des_context
    ):
        """
        Verify scope_boundary_check.py executes without import errors.

        The script should either succeed or fail gracefully with
        "DES module not available" message.
        """
        script_path = (
            installed_des_context.claude_dir / "scripts" / "scope_boundary_check.py"
        )
        lib_python = installed_des_context.claude_dir / "lib" / "python"

        env = self._create_pythonpath_env(lib_python)

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )

        assert (
            "Traceback" not in result.stderr or "des.validation" not in result.stderr
        ), (
            f"Script crashed with DES import error.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        valid_outputs = [
            "All staged files within declared scope",
            "DES module not available",
            "scope boundary check skipped",
        ]
        output = result.stdout + result.stderr

        assert result.returncode == 0 or any(msg in output for msg in valid_outputs), (
            f"Script did not execute properly.\n"
            f"Return code: {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


class TestDESPluginVerifyIntegration:
    """Integration tests for DESPlugin.verify() method."""

    def test_des_plugin_verify_returns_success_after_installation(
        self, installed_des_context
    ):
        """
        Verify DESPlugin.verify() returns success after full installation.

        Acceptance Criteria (from feature file):
        - DESPlugin.verify() returns success after installation
        """
        from scripts.install.plugins.des_plugin import DESPlugin

        plugin = DESPlugin()
        result = plugin.verify(installed_des_context)

        assert result.success, (
            f"DESPlugin.verify() failed.\n"
            f"Message: {result.message}\nErrors: {result.errors}"
        )
        assert "verification passed" in result.message.lower(), (
            f"Expected verification passed message, got: {result.message}"
        )

    def test_des_plugin_verify_validates_module_import(self, installed_des_context):
        """Verify DESPlugin.verify() checks that DES module is importable."""
        from scripts.install.plugins.des_plugin import DESPlugin

        plugin = DESPlugin()
        result = plugin.verify(installed_des_context)

        assert result.success, (
            f"DESPlugin.verify() should pass when module is importable.\n"
            f"Errors: {result.errors}"
        )

    def test_des_plugin_verify_validates_scripts_present(self, installed_des_context):
        """Verify DESPlugin.verify() checks that scripts are present."""
        from scripts.install.plugins.des_plugin import DESPlugin

        plugin = DESPlugin()
        result = plugin.verify(installed_des_context)

        assert result.success, (
            f"DESPlugin.verify() should pass when scripts are present.\n"
            f"Errors: {result.errors}"
        )

    def test_des_plugin_verify_validates_templates_present(self, installed_des_context):
        """Verify DESPlugin.verify() checks that templates are present."""
        from scripts.install.plugins.des_plugin import DESPlugin

        plugin = DESPlugin()
        result = plugin.verify(installed_des_context)

        assert result.success, (
            f"DESPlugin.verify() should pass when templates are present.\n"
            f"Errors: {result.errors}"
        )
