"""Shared fixtures for installer walking skeleton acceptance tests.

Provides the infrastructure to invoke install_nwave.py's main() in an
isolated environment and capture its TUI output for assertion.
"""

import importlib
import io
import os
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
    opencode_config_dir = tmp_path_factory.mktemp("opencode_config")

    # Save originals for cleanup
    original_logger_init = Logger.__init__
    original_get_config = PathUtils.get_claude_config_dir
    original_get_opencode = PathUtils.get_opencode_config_dir
    original_run_checks = PreflightChecker.run_all_checks
    original_subprocess_run = subprocess.run
    original_argv = sys.argv
    original_opencode_env = os.environ.get("OPENCODE_CONFIG_DIR")

    try:
        # --- Patch Logger: disable Rich so output goes through plain print ---
        def plain_logger_init(self, *args, **kwargs):
            original_logger_init(self, *args, **kwargs)
            self._rich_console = None

        Logger.__init__ = plain_logger_init

        # --- Patch config dirs → temp ---
        # claude_config_dir: resolved via PathUtils.get_claude_config_dir
        # opencode_config_dir: resolved via both PathUtils.get_opencode_config_dir
        #   AND the per-plugin _opencode_*_dir functions that each read
        #   OPENCODE_CONFIG_DIR directly — set both paths to the same tmp
        #   dir to isolate the installer from the user's real ~/.config/opencode/.
        PathUtils.get_claude_config_dir = staticmethod(lambda: claude_config_dir)
        PathUtils.get_opencode_config_dir = staticmethod(lambda: opencode_config_dir)
        os.environ["OPENCODE_CONFIG_DIR"] = str(opencode_config_dir)

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

        # --- Patch AttributionPlugin hook lifecycle to prevent real FS writes ---
        # AttributionPlugin() defaults self._config_dir to Path.home() / ".nwave",
        # and install_attribution_hook's _resolve_hooks_dir falls through to a
        # cwd-relative .git/hooks/ when subprocess returns empty stdout (as the
        # mock above does). Without patching, the installer writes to the real
        # ~/.nwave/ and .git/hooks/ of whichever repo the tests run from.
        import scripts.install.attribution_utils as _attr_utils
        import scripts.install.plugins.attribution_plugin as _attr_plugin

        original_install_hook_utils = _attr_utils.install_attribution_hook
        original_install_hook_plugin = _attr_plugin.install_attribution_hook
        original_write_pref = _attr_utils.write_attribution_preference
        _attr_plugin.install_attribution_hook = lambda config_dir=None: (
            claude_config_dir / ".nwave" / "hooks" / "prepare-commit-msg"
        )
        _attr_utils.install_attribution_hook = _attr_plugin.install_attribution_hook
        _attr_utils.write_attribution_preference = lambda *a, **kw: None

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
        PathUtils.get_opencode_config_dir = original_get_opencode
        PreflightChecker.run_all_checks = original_run_checks
        subprocess.run = original_subprocess_run
        _attr_utils.install_attribution_hook = original_install_hook_utils
        _attr_plugin.install_attribution_hook = original_install_hook_plugin
        _attr_utils.write_attribution_preference = original_write_pref
        sys.argv = original_argv
        if original_opencode_env is None:
            os.environ.pop("OPENCODE_CONFIG_DIR", None)
        else:
            os.environ["OPENCODE_CONFIG_DIR"] = original_opencode_env


@pytest.fixture(scope="module")
def output(installer_result) -> str:
    """Captured stdout from a full happy-path installation."""
    return installer_result[0]


@pytest.fixture(scope="module")
def exit_code(installer_result) -> int:
    """Exit code from a full happy-path installation."""
    return installer_result[1]
