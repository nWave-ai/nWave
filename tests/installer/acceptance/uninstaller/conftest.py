"""Shared fixtures for uninstaller walking skeleton acceptance tests.

Provides the infrastructure to first install nWave into an isolated temp
directory, then invoke uninstall_nwave.py's main() and capture its TUI
output for assertion.
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


def _apply_patches(original_logger_init, claude_config_dir):
    """Apply shared patches: plain Logger, config dir redirect, subprocess mock.

    Returns a dict of originals for cleanup.
    """
    originals = {
        "logger_init": Logger.__init__,
        "get_config": PathUtils.get_claude_config_dir,
        "run_checks": PreflightChecker.run_all_checks,
        "subprocess_run": subprocess.run,
        "argv": sys.argv,
    }

    # Force plain text Logger (no Rich)
    def plain_logger_init(self, *args, **kwargs):
        original_logger_init(self, *args, **kwargs)
        self._rich_console = None

    Logger.__init__ = plain_logger_init

    # Config dir → temp
    PathUtils.get_claude_config_dir = staticmethod(lambda: claude_config_dir)

    # Preflight → all pass
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

    # subprocess.run → no-op success
    mock_completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )
    subprocess.run = lambda *a, **kw: mock_completed

    return originals


def _restore_patches(originals, original_logger_init):
    """Restore all monkey-patches."""
    Logger.__init__ = original_logger_init
    PathUtils.get_claude_config_dir = originals["get_config"]
    PreflightChecker.run_all_checks = originals["run_checks"]
    subprocess.run = originals["subprocess_run"]
    sys.argv = originals["argv"]


@pytest.fixture(scope="module")
def uninstaller_result(project_root, tmp_path_factory):
    """Install, then uninstall with --force --backup. Return (output, exit_code).

    Module-scoped: runs the full install + uninstall sequence once.
    Only the uninstall stdout is captured; install runs silently.
    """
    claude_config_dir = tmp_path_factory.mktemp("claude_config_uninstall")
    original_logger_init = Logger.__init__

    originals = _apply_patches(original_logger_init, claude_config_dir)

    try:
        # ── Phase 1: silent install to populate the config dir ──
        sys.argv = ["install_nwave.py"]
        devnull = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = devnull

        import scripts.install.install_nwave as install_mod

        importlib.reload(install_mod)
        install_mod.main()

        sys.stdout = old_stdout

        # Verify install actually populated something
        assert (claude_config_dir / "agents" / "nw").exists(), (
            "Install did not create agents"
        )
        assert (claude_config_dir / "commands" / "nw").exists(), (
            "Install did not create commands"
        )

        # ── Phase 2: uninstall with --force --backup, capture output ──
        sys.argv = ["uninstall_nwave.py", "--force", "--backup"]
        captured = io.StringIO()
        sys.stdout = captured

        import scripts.install.uninstall_nwave as uninstall_mod

        importlib.reload(uninstall_mod)
        exit_code = uninstall_mod.main()

        sys.stdout = old_stdout
        output = captured.getvalue()

        return output, exit_code

    finally:
        sys.stdout = sys.__stdout__  # safety net
        _restore_patches(originals, original_logger_init)


@pytest.fixture(scope="module")
def output(uninstaller_result) -> str:
    """Captured stdout from a full happy-path uninstallation."""
    return uninstaller_result[0]


@pytest.fixture(scope="module")
def exit_code(uninstaller_result) -> int:
    """Exit code from a full happy-path uninstallation."""
    return uninstaller_result[1]
