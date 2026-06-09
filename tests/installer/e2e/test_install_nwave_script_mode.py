"""Regression AT for dogfood friction F-05 — installer script-mode invocation.

Defect (RCA: docs/analysis/atdd-pure-dogfooding-friction-2026-05-20.md):
`python scripts/install/install_nwave.py` (bare script-mode invocation —
the form documented in the installer's own `--help` usage line) crashes.
The package-import `try` block fails at the `reviewer_signing_plugin`
import (`ModuleNotFoundError`), falls through to the standalone-fallback
`except` block, which then fails at `from shared.agent_catalog import ...`
(`ModuleNotFoundError: shared` — `shared` is not importable in pure script
mode). `python -m scripts.install.install_nwave` works; the bare-script
form does not. Surfaced when the F-01 commit added a new plugin module.

These are @wiring_e2e regression tests: they run the REAL installer as a
subprocess (not import it), because this is precisely the "fixture passes,
real invocation fails" defect class — the only honest check is the real
script-mode entry point a dogfooding operator actually types.

Expected pre-fix state: `test_script_mode_help_exits_clean` FAILS RED —
the bare-script subprocess exits non-zero with a ModuleNotFoundError
traceback. Classification: MISSING_FUNCTIONALITY — the script-mode
invocation contract (documented in `--help`) is unmet.

Goes GREEN once install_nwave.py is script-mode-robust (both the package
`try` block AND the standalone `except` fallback import successfully when
the file is run as a bare script from the repo root).
"""

import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = [pytest.mark.e2e, pytest.mark.wiring_e2e]

# Repo root: tests/installer/e2e/ -> repo root is three parents up.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "install" / "install_nwave.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the installer as a subprocess from the repo root with a clean argv."""
    return subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_script_mode_help_exits_clean() -> None:
    """Bare-script `--help` (the documented invocation) must exit 0 with usage.

    This is the F-05 regression assertion. On the current tree it FAILS RED:
    the bare-script subprocess exits non-zero and emits a ModuleNotFoundError
    traceback instead of the usage banner.
    """
    result = _run([sys.executable, str(SCRIPT_PATH), "--help"])

    assert "ModuleNotFoundError" not in result.stderr, (
        "F-05 regression: bare-script invocation crashed with a "
        f"ModuleNotFoundError before reaching arg parsing.\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert "Traceback" not in result.stderr, (
        "F-05 regression: bare-script invocation crashed with a traceback.\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert result.returncode == 0, (
        f"Bare-script `--help` exited {result.returncode}, expected 0.\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "usage" in combined or "install" in combined, (
        "Bare-script `--help` produced no recognizable usage/banner text.\n"
        f"--- stdout ---\n{result.stdout}"
    )


def test_module_mode_help_exits_clean() -> None:
    """Module-mode `--help` must exit 0 — pins the currently-working form.

    `python -m scripts.install.install_nwave --help` works today. This test
    guards against a regression that would break BOTH invocation forms.
    """
    result = _run([sys.executable, "-m", "scripts.install.install_nwave", "--help"])

    assert "Traceback" not in result.stderr, (
        "Module-mode `--help` crashed with a traceback.\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert result.returncode == 0, (
        f"Module-mode `--help` exited {result.returncode}, expected 0.\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )


def test_script_mode_dry_run_reaches_real_logic() -> None:
    """Bare-script `--dry-run` must exit past the import block into real logic.

    `--dry-run` exercises the installer beyond argument parsing — it imports
    every plugin and runs the pipeline in no-write mode. A clean exit proves
    the script-mode import path resolves ALL modules (both the package `try`
    block and the standalone `except` fallback), not just argparse.
    """
    result = _run([sys.executable, str(SCRIPT_PATH), "--dry-run"])

    assert "ModuleNotFoundError" not in result.stderr, (
        "F-05 regression: bare-script `--dry-run` crashed on a module import.\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert result.returncode == 0, (
        f"Bare-script `--dry-run` exited {result.returncode}, expected 0.\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
