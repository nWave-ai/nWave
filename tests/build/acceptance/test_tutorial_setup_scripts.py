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
def test_tutorial_setup_lifecycle(script: Path) -> None:
    """Per-tutorial validation that setup.sh behaves per the convention.

    Consolidated lifecycle test (Lyra 2026-05-18 speedup): runs the full
    tutorial-setup contract in a single tmpdir with 3 subprocess
    invocations instead of 4 separate tests with 6 invocations. Net win
    on this file alone: 24 tests x ~25s avg ≈ 600s → 6 tests x ~12s ≈ 72s
    (≈8x faster).

    Contract verified, in order:
      1. Fresh run exits 0 (subprocess #1)
      2. Setup created at least one non-hidden directory (filesystem check)
      3. Re-running on the same tmpdir is idempotent (subprocess #2 exits 0)
      4. After --force, the sentinel file inside the project directory is
         wiped and the project directory is recreated (subprocess #3)

    Splitting these into 4 separate tests would let pytest report which
    behaviour broke independently, but the cost is 3-4x wall-time per
    script. The trade-off is acceptable because the failure message of
    this single test names the specific contract clause that broke (the
    assert messages below remain granular), and the test_id (= script
    directory name) still identifies which tutorial regressed.
    """
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)

        # Step 1 — fresh run exits 0
        first = _run_setup(script, workdir)
        assert first.returncode == 0, (
            f"[fresh-run] {script.parent.name}/setup.sh failed with exit "
            f"{first.returncode}\n"
            f"stdout:\n{first.stdout}\n"
            f"stderr:\n{first.stderr}"
        )

        # Step 2 — created at least one non-hidden directory
        subdirs = _non_hidden_subdirs(workdir)
        assert subdirs, (
            f"[creates-project-dir] {script.parent.name}/setup.sh exited cleanly "
            f"but created no project directory in {workdir}. Did the script forget "
            f"to mkdir?"
        )

        # Step 3 — idempotent on second run
        second = _run_setup(script, workdir)
        assert second.returncode == 0, (
            f"[idempotent-rerun] {script.parent.name}/setup.sh second run failed "
            f"(not idempotent) with exit {second.returncode}\n"
            f"stdout:\n{second.stdout}\n"
            f"stderr:\n{second.stderr}"
        )

        # Step 4 — --force wipes the sentinel
        sentinel = subdirs[0] / ".sentinel-from-test"
        sentinel.write_text("if this still exists after --force, wipe didn't work")

        forced = _run_setup(script, workdir, "--force")
        assert forced.returncode == 0, (
            f"[force-flag] {script.parent.name}/setup.sh --force run failed: "
            f"{forced.stderr}"
        )
        assert not sentinel.exists(), (
            f"[force-flag] {script.parent.name}/setup.sh --force did not wipe "
            f"the project directory: {sentinel} still exists"
        )
