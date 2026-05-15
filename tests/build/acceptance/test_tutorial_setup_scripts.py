"""Acceptance tests for tutorial setup scripts.

Discovers every `docs/guides/*/setup.py` and exercises it in an isolated
tmpdir. Catches drift between a tutorial's documented setup and its
automated counterpart.

Per docs/internal/writing-tutorials.md, each setup.py must:
- Exit 0 on a fresh run
- Create at least one non-hidden directory in cwd (proves it did something)
- Be idempotent on a second run (skip-if-exists)
- Support --force to wipe and recreate

Tests parametrize over discovered scripts. The test file passes trivially
when no scripts exist yet (early in the rollout).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GUIDES_DIR = PROJECT_ROOT / "docs" / "guides"


def discover_setup_scripts() -> list[Path]:
    """Find every docs/guides/*/setup.py in the repo."""
    if not GUIDES_DIR.exists():
        return []
    return sorted(GUIDES_DIR.glob("*/setup.py"))


SETUP_SCRIPTS = discover_setup_scripts()
SCRIPT_IDS = [s.parent.name for s in SETUP_SCRIPTS]


def _run_setup(script: Path, workdir: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a setup script in workdir, capturing output.

    Sets ``GIT_CEILING_DIRECTORIES`` to the workdir so any ``git`` invocation
    inside the setup script cannot walk up to the host nwave-dev repo and
    mutate its refs/config (per docs/analysis/rca-test-git-pollution-2026-04-27.md).
    Strips inherited ``GIT_*`` vars for the same reason.
    """
    import os
    import sys

    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CEILING_DIRECTORIES"] = str(workdir)

    return subprocess.run(
        [sys.executable, str(script.resolve()), *args],
        cwd=str(workdir),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        env=env,
    )


def _non_hidden_subdirs(directory: Path) -> list[Path]:
    """List non-hidden subdirectories of `directory` (excludes .venv etc.)."""
    return [p for p in directory.iterdir() if p.is_dir() and not p.name.startswith(".")]


@pytest.mark.skipif(not SETUP_SCRIPTS, reason="no tutorial setup scripts present yet")
@pytest.mark.parametrize("script", SETUP_SCRIPTS, ids=SCRIPT_IDS)
class TestTutorialSetupScript:
    """Per-tutorial validation that setup.sh behaves per the convention."""

    def test_fresh_run_succeeds(self, script: Path) -> None:
        """A fresh run of setup.sh must exit 0."""
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            result = _run_setup(script, workdir)
            assert result.returncode == 0, (
                f"setup.sh failed with exit {result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )

    def test_creates_project_directory(self, script: Path) -> None:
        """Setup must create at least one non-hidden directory."""
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            _run_setup(script, workdir)
            subdirs = _non_hidden_subdirs(workdir)
            assert subdirs, (
                f"setup.sh exited cleanly but created no project directory in {workdir}. "
                f"Did the script forget to mkdir?"
            )

    def test_idempotent_second_run(self, script: Path) -> None:
        """Re-running setup.sh on an already-set-up directory must not error."""
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            first = _run_setup(script, workdir)
            assert first.returncode == 0, (
                f"first run of {script.parent.name} failed "
                f"(returncode={first.returncode})\n"
                f"STDOUT: {first.stdout}\n"
                f"STDERR: {first.stderr}"
            )
            second = _run_setup(script, workdir)
            assert second.returncode == 0, (
                f"second run failed (not idempotent) with exit {second.returncode}\n"
                f"stdout:\n{second.stdout}\n"
                f"stderr:\n{second.stderr}"
            )

    def test_force_flag_wipes_and_recreates(self, script: Path) -> None:
        """--force must wipe the existing project and recreate it."""
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            _run_setup(script, workdir)
            subdirs_before = _non_hidden_subdirs(workdir)
            assert subdirs_before, "setup didn't produce a project directory"

            # Add a sentinel file inside the project directory
            sentinel = subdirs_before[0] / ".sentinel-from-test"
            sentinel.write_text("if this still exists after --force, wipe didn't work")

            result = _run_setup(script, workdir, "--force")
            assert result.returncode == 0, f"--force run failed: {result.stderr}"
            assert not sentinel.exists(), (
                f"--force did not wipe the project directory: {sentinel} still exists"
            )
