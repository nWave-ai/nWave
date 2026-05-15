"""Pytest wrapper around the Java polyglot smoke script.

Marked ``polyglot_smoke`` (custom marker, registered in ``pyproject.toml``).
Behaviour:

- If ``java`` and (``mvn`` OR ``./mvnw``) are not present: SKIPPED.
- Otherwise: subprocess-invokes ``scripts/polyglot/smoke_java_pilot.py``
  and asserts exit 0.

The smoke script itself fails-open on missing toolchain (exit 0 with
WARNING). The test here additionally SKIPs so the test report is honest
about the fact that no actual Java suite ran.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "polyglot" / "smoke_java_pilot.py"
PILOT_DIR = REPO_ROOT / "tests" / "polyglot-pilot" / "java"


def _maven_available() -> bool:
    if shutil.which("mvn") is not None:
        return True
    if os.name == "nt":
        wrapper = PILOT_DIR / "mvnw.cmd"
        return wrapper.is_file()
    wrapper = PILOT_DIR / "mvnw"
    return wrapper.is_file() and os.access(wrapper, os.X_OK)


@pytest.mark.polyglot_smoke
@pytest.mark.slow
def test_java_polyglot_pilot_runs_green() -> None:
    """The Java pilot's mvn test suite must run GREEN end-to-end."""
    if shutil.which("java") is None:
        pytest.skip("Java runtime not on PATH — polyglot smoke deferred")
    if not _maven_available():
        pytest.skip("Neither `mvn` nor `./mvnw` available — polyglot smoke deferred")

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
            "polyglot Java smoke FAILED\n"
            f"exit={result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
