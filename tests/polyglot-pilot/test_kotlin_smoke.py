"""Pytest wrapper around the Kotlin polyglot smoke script.

Marked ``polyglot_smoke`` (custom marker, registered in ``pyproject.toml``).
Behaviour:

- If neither ``./gradlew`` (in the pilot dir) nor ``gradle`` (on PATH) is
  available: SKIPPED (no toolchain).
- Otherwise: subprocess-invokes ``scripts/polyglot/smoke_kotlin_pilot.py``
  and asserts exit 0.

The smoke script itself fails-open on missing toolchain (exit 0 with
WARNING). The test here additionally SKIPs so the test report is honest about
the fact that no actual Kotlin suite ran.

Extension Justification (per nw-quality-framework SKILL):

  WHY-NEW-FILE: tests/polyglot-pilot/test_kotlin_smoke.py
    CLOSEST-EXISTING: tests/polyglot-pilot/test_typescript_smoke.py
    EXTENSION-COST: a single parametrized test (npx vs gradle) would couple
      Node and JVM toolchain probing, the skip messages would lose language
      attribution, and the smoke script paths would have to be parameterised.
    PARALLEL-RATIONALE: per-language smoke wrapper mirrors per-language smoke
      script (sibling pattern); each wrapper is ~30 LOC and toolchain-specific;
      consolidation becomes useful once ≥3 sibling wrappers exist.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "polyglot" / "smoke_kotlin_pilot.py"
PILOT_DIR = REPO_ROOT / "tests" / "polyglot-pilot" / "kotlin"


def _toolchain_available() -> bool:
    wrapper = PILOT_DIR / "gradlew"
    if wrapper.is_file() and os.access(wrapper, os.X_OK):
        return True
    return shutil.which("gradle") is not None


@pytest.mark.polyglot_smoke
@pytest.mark.slow
def test_kotlin_polyglot_pilot_runs_green() -> None:
    """The Kotlin pilot's Kotest suite must run GREEN end-to-end."""
    if not _toolchain_available():
        pytest.skip(
            "Kotlin toolchain (./gradlew or `gradle`) unavailable — "
            "polyglot smoke deferred"
        )

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
            "polyglot Kotlin smoke FAILED\n"
            f"exit={result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
