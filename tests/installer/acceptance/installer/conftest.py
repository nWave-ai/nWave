"""Shared fixtures for installer walking skeleton acceptance tests.

Provides the infrastructure to invoke install_nwave.py's main() in an
isolated environment and capture its TUI output for assertion.
"""

import importlib
import io
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.install.install_utils import Logger, PathUtils
from scripts.install.preflight_checker import CheckResult, PreflightChecker


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Real project root (4 levels up from this file)."""
    return Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def installer_result(project_root, tmp_path_factory):
    """Run install_nwave.py main() once and return (output, exit_code).

    Module-scoped: executes the full happy-path installation a single time
    and caches the captured stdout for all tests in the module.

    Patches applied (manually, since monkeypatch is function-scoped):
    - Logger forced to plain text (no Rich console)
    - CLAUDE_CONFIG_DIR pointed at a temp directory
    - PreflightChecker returns all-passing results
    - subprocess.run returns success for embedding/build calls
    """
    claude_config_dir = tmp_path_factory.mktemp("claude_config")

    # Save originals for cleanup
    original_logger_init = Logger.__init__
    original_get_config = PathUtils.get_claude_config_dir
    original_run_checks = PreflightChecker.run_all_checks
    original_subprocess_run = subprocess.run
    original_argv = sys.argv

    try:
        # --- Patch Logger: disable Rich so output goes through plain print ---
        def plain_logger_init(self, *args, **kwargs):
            original_logger_init(self, *args, **kwargs)
            self._rich_console = None

        Logger.__init__ = plain_logger_init

        # --- Patch config dir → temp ---
        PathUtils.get_claude_config_dir = staticmethod(lambda: claude_config_dir)

        # --- Patch preflight → all pass ---
        passing_results = [
            CheckResult(
                passed=True,
                error_code=None,
                message="Virtual environment detected.",
                remediation=None,
            ),
            CheckResult(
                passed=True,
                error_code=None,
                message="Pipenv is available.",
                remediation=None,
            ),
            CheckResult(
                passed=True,
                error_code=None,
                message="All required dependencies are available.",
                remediation=None,
            ),
        ]
        PreflightChecker.run_all_checks = lambda self, **kw: passing_results

        # --- Patch subprocess.run → no-op success ---
        mock_completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        subprocess.run = lambda *a, **kw: mock_completed

        # --- Set argv ---
        sys.argv = ["install_nwave.py"]

        # --- Capture stdout ---
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        # Reload to pick up any source changes since last import
        import scripts.install.install_nwave as _mod

        importlib.reload(_mod)
        exit_code = _mod.main()

        sys.stdout = old_stdout
        output = captured.getvalue()

        return output, exit_code

    finally:
        # Restore everything
        Logger.__init__ = original_logger_init
        PathUtils.get_claude_config_dir = original_get_config
        PreflightChecker.run_all_checks = original_run_checks
        subprocess.run = original_subprocess_run
        sys.argv = original_argv


@pytest.fixture(scope="module")
def output(installer_result) -> str:
    """Captured stdout from a full happy-path installation."""
    return installer_result[0]


@pytest.fixture(scope="module")
def exit_code(installer_result) -> int:
    """Exit code from a full happy-path installation."""
    return installer_result[1]
