"""Installer step definitions for manifest circular dependency bug tests."""

import os
import subprocess
import sys

import pytest
from pytest_bdd import given, then, when


@given("the installer is ready to run")
def installer_ready(project_root):
    """Verify the installer script exists and is ready."""
    install_script = project_root / "scripts" / "install" / "install_nwave.py"
    assert install_script.exists(), f"Installer not found at {install_script}"
    pytest.install_script = install_script


@when("I run the nWave installer")
def run_installer(monkeypatch, project_root):
    """Run the nWave installer with test environment."""
    # Set HOME to test directory so installer uses test .claude dir
    monkeypatch.setenv("HOME", str(pytest.test_dir))

    # Set PYTHONPATH to include project root for imports
    pythonpath = str(project_root)
    env = os.environ.copy()
    env["PYTHONPATH"] = pythonpath
    env["HOME"] = str(pytest.test_dir)

    # Run installer
    result = subprocess.run(
        [sys.executable, str(pytest.install_script)],
        cwd=project_root,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )

    pytest.install_result = result
    pytest.install_output = result.stdout
    pytest.install_errors = result.stderr


@then("the installation should complete successfully")
def installation_successful():
    """Verify installation completed successfully."""
    # Check that installation didn't fail with error
    # Note: Due to the bug, this will currently fail because validation fails
    # After fix, this should pass
    assert pytest.install_result.returncode == 0, (
        f"Installation failed with exit code {pytest.install_result.returncode}. "
        f"Output: {pytest.install_output}\\nError: {pytest.install_errors}"
    )


@then("the validation should pass")
def validation_passed():
    """Verify validation passed."""
    # Check for PASSED in validation output (with or without ANSI codes)
    assert (
        "Installation validation" in pytest.install_output
        and "PASSED" in pytest.install_output
    ), f"Validation did not pass. Output: {pytest.install_output}"


@given("the installer has completed installation")
def installer_completed():
    """Verify installer has completed the installation phase."""
    # This step assumes we've already run the installer
    assert hasattr(pytest, "install_output"), "Installer has not been run"
    assert "Installing framework files" in pytest.install_output


@when("the validation step runs")
def validation_runs():
    """Verify validation step is running."""
    # Validation runs as part of installation, check output
    assert (
        "Validating installation" in pytest.install_output
        or "Validation Results" in pytest.install_output
    )
