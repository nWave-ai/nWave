"""Pytest wrapper around the TypeScript polyglot smoke script.

Marked ``polyglot_smoke`` (custom marker, registered in ``pyproject.toml``).
Behaviour:

- If ``npx`` is absent on PATH: SKIPPED (no toolchain).
- Otherwise: subprocess-invokes ``scripts/polyglot/smoke_typescript_pilot.py``
  and asserts exit 0.

The smoke script itself fails-open on missing toolchain (exit 0 with
WARNING). The test here additionally SKIPs so the test report is honest
about the fact that no actual TypeScript suite ran.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "polyglot" / "smoke_typescript_pilot.py"


@pytest.mark.polyglot_smoke
@pytest.mark.slow
def test_typescript_polyglot_pilot_runs_green() -> None:
    """The TypeScript pilot's vitest suite must run GREEN end-to-end."""
    if shutil.which("npx") is None or shutil.which("npm") is None:
        pytest.skip("Node toolchain (npm/npx) not on PATH — polyglot smoke deferred")

    assert SMOKE_SCRIPT.is_file(), f"missing smoke script: {SMOKE_SCRIPT}"

    result = subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        pytest.fail(
            "polyglot TypeScript smoke FAILED\n"
            f"exit={result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
