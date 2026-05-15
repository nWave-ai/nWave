"""Pytest wrapper around the Rust polyglot smoke script.

Marked ``polyglot_smoke`` (custom marker, registered in ``pyproject.toml``).
Behaviour:

- If ``cargo`` is absent on PATH: SKIPPED (no toolchain).
- Otherwise: subprocess-invokes ``scripts/polyglot/smoke_rust_pilot.py`` and
  asserts exit 0.

The smoke script itself fails-open on missing toolchain (exit 0 with
WARNING). The test here additionally SKIPs so the test report is honest
about the fact that no actual Rust suite ran.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "polyglot" / "smoke_rust_pilot.py"


@pytest.mark.polyglot_smoke
@pytest.mark.slow
def test_rust_polyglot_pilot_runs_green() -> None:
    """The Rust pilot's cargo test suite must run GREEN end-to-end."""
    if shutil.which("cargo") is None:
        pytest.skip("Rust toolchain (cargo) not on PATH — polyglot smoke deferred")

    assert SMOKE_SCRIPT.is_file(), f"missing smoke script: {SMOKE_SCRIPT}"

    result = subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        pytest.fail(
            "polyglot Rust smoke FAILED\n"
            f"exit={result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
