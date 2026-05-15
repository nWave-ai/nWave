"""Install-and-import smoke tests for the nwave wheel.

Validates that a wheel installed in a clean venv (no dev deps) produces
a working DES runtime and nwave-ai CLI:

  - DES hook adapter importable via ``python -m``
  - ``from des.adapters.drivers.hooks import claude_code_hook_adapter`` works
  - ``from nwave_ai import cli`` works
  - ``python -m nwave_ai.cli version`` returns a valid version string
  - No ``src.des`` import paths remain in installed code (import rewrite verified)
  - Missing DES module causes detectable failure

Pure validation functions live in scripts/validation/validate_installed_wheel.py.
Tests exercise them against a real wheel installed in a temp venv.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validation.validate_installed_wheel import (
    check_importable,
    check_module_runnable,
    check_no_src_imports,
    find_site_packages,
    run_install_smoke,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory) -> Path:
    """Build a wheel from the current project and return its path."""
    output_dir = tmp_path_factory.mktemp("wheel_output")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(output_dir)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        f"Wheel build failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    wheels = list(output_dir.glob("*.whl"))
    assert len(wheels) == 1, f"Expected exactly 1 wheel, found {len(wheels)}"
    return wheels[0]


@pytest.fixture(scope="module")
def installed_venv(built_wheel: Path, tmp_path_factory) -> Path:
    """Create a clean venv, install the wheel, return the venv path."""
    venv_dir = tmp_path_factory.mktemp("smoke_venv")

    # Create venv
    result = subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, (
        f"venv creation failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    # Install wheel (no dev deps)
    venv_python = venv_dir / "bin" / "python"
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", str(built_wheel)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        f"Wheel install failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    return venv_dir


@pytest.fixture(scope="module")
def venv_python(installed_venv: Path) -> Path:
    """Return the path to the venv's Python interpreter."""
    return installed_venv / "bin" / "python"


# ---------------------------------------------------------------------------
# Scenario: Full smoke report passes on valid install
# ---------------------------------------------------------------------------


class TestFullSmokeReportPasses:
    """A correctly installed wheel should produce a passing smoke report."""

    def test_run_install_smoke_all_pass(self, venv_python: Path):
        """The full smoke check pipeline returns all-passing results."""
        report = run_install_smoke(venv_python)

        failures = [r for r in report.results if not r.passed]
        assert failures == [], (
            f"Expected all smoke checks to pass, got {len(failures)} failure(s):\n"
            + "\n".join(f"  - [{r.check_name}] {r.message}" for r in failures)
        )


# ---------------------------------------------------------------------------
# Scenario: DES hook adapter is importable
# ---------------------------------------------------------------------------


class TestDesHookAdapterImportable:
    """The DES hook adapter must be importable in the installed venv."""

    def test_des_hook_adapter_import(self, venv_python: Path):
        """Importing the hook adapter module succeeds."""
        result = check_importable(
            venv_python,
            "des.adapters.drivers.hooks.claude_code_hook_adapter",
        )
        assert result.passed, f"DES hook adapter not importable: {result.message}"

    def test_des_domain_import(self, venv_python: Path):
        """Importing des.domain succeeds."""
        result = check_importable(venv_python, "des.domain")
        assert result.passed, f"des.domain not importable: {result.message}"

    def test_des_application_import(self, venv_python: Path):
        """Importing des.application succeeds."""
        result = check_importable(venv_python, "des.application")
        assert result.passed, f"des.application not importable: {result.message}"


# ---------------------------------------------------------------------------
# Scenario: nwave-ai CLI responds with version
# ---------------------------------------------------------------------------


class TestNwaveCliVersion:
    """The nwave-ai CLI must respond to version command."""

    def test_nwave_cli_importable(self, venv_python: Path):
        """Importing nwave_ai.cli succeeds."""
        result = check_importable(venv_python, "nwave_ai.cli")
        assert result.passed, f"nwave_ai.cli not importable: {result.message}"

    def test_nwave_cli_version_output(self, venv_python: Path):
        """Running 'python -m nwave_ai.cli version' returns a version string."""
        result = check_module_runnable(
            venv_python,
            "nwave_ai.cli",
            args=["version"],
        )
        assert result.passed, f"nwave-ai version command failed: {result.message}"


# ---------------------------------------------------------------------------
# Scenario: No src.des import paths in installed code
# ---------------------------------------------------------------------------


class TestNoSrcDesImports:
    """Installed code must not contain 'from src.des' or 'import src.des'."""

    def test_no_src_imports_in_des_package(self, venv_python: Path):
        """The des/ package in site-packages has no src.des references."""
        site_packages = find_site_packages(venv_python)
        result = check_no_src_imports(site_packages, "des")
        assert result.passed, (
            f"Found src.des import paths in installed code: {result.message}"
        )


# ---------------------------------------------------------------------------
# Scenario: Missing DES module causes detectable failure
# ---------------------------------------------------------------------------


class TestMissingDesModuleDetected:
    """check_importable must correctly report failure for missing modules."""

    def test_missing_module_detected(self, venv_python: Path):
        """A nonexistent module is correctly flagged as not importable."""
        result = check_importable(venv_python, "des.nonexistent_module_xyz")
        assert not result.passed, (
            "Expected check_importable to fail for nonexistent module"
        )
        assert "nonexistent_module_xyz" in result.message


# ---------------------------------------------------------------------------
# Scenario: DES hook adapter runnable as module
# ---------------------------------------------------------------------------


class TestDesHookAdapterRunnable:
    """The DES hook adapter must be runnable via python -m."""

    def test_hook_adapter_module_runnable(self, venv_python: Path):
        """Running 'python -m des.adapters.drivers.hooks.claude_code_hook_adapter'
        with no arguments exits without crashing (may show usage)."""
        result = check_module_runnable(
            venv_python,
            "des.adapters.drivers.hooks.claude_code_hook_adapter",
            args=[],
            allow_nonzero=True,
        )
        assert result.passed, (
            f"DES hook adapter not runnable as module: {result.message}"
        )
