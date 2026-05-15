"""Smoke command — run the polyglot Kotlin pilot end-to-end.

Invocation::

    pipenv run python scripts/polyglot/smoke_kotlin_pilot.py

Behaviour:

1. ``cd tests/polyglot-pilot/kotlin/``.
2. Detect ``gradlew`` (preferred) or ``gradle`` on PATH. If neither is present:
   log ``[polyglot-smoke] toolchain absent — skipped`` and exit 0. (Fail-open
   robustness — CI without a JVM/Gradle toolchain must not break unrelated
   test suites.)
3. ``./gradlew test`` (or ``gradle test`` as fallback).
4. Exit 0 on success; non-zero on failure with the captured stderr.

The script is the single contract Python-side callers depend on. Both manual
human runs and the pytest wrapper at
``tests/polyglot-pilot/test_kotlin_smoke.py`` go through it.

Extension Justification (per nw-quality-framework SKILL):

  WHY-NEW-FILE: scripts/polyglot/smoke_kotlin_pilot.py
    CLOSEST-EXISTING: scripts/polyglot/smoke_typescript_pilot.py
    EXTENSION-COST: would require a generic toolchain-dispatch refactor
      (npx vs gradle, npm-install vs gradle deps, env-vars, exit codes) — out
      of scope for Epic 3.
    PARALLEL-RATIONALE: per-language smoke is the established polyglot pattern
      (TS shipped Epic 2B, C# pending); each script is ~100 LOC and
      toolchain-specific; convergence to a shared dispatcher becomes worthwhile
      once ≥3 sibling scripts exist.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PILOT_DIR = REPO_ROOT / "tests" / "polyglot-pilot" / "kotlin"

# Exit codes — distinguish skip (0) from failure (non-zero) and let callers
# branch on the structured stderr prefix.
EXIT_OK = 0
EXIT_TEST_FAILED = 1
EXIT_TOOLCHAIN_BROKEN = 2  # gradle present but exec failed unexpectedly


def _log(message: str) -> None:
    print(f"[polyglot-smoke] {message}", flush=True)


def _resolve_gradle(pilot_dir: Path) -> list[str] | None:
    """Return the command-prefix used to invoke Gradle.

    Preference order:
      1. ``./gradlew`` in the pilot dir (preferred — pins the wrapper version)
      2. ``gradle`` on PATH (fallback for CI images without a wrapper checked in)

    Returns None if neither is available — signal for fail-open SKIP.
    """
    wrapper = pilot_dir / "gradlew"
    if wrapper.is_file() and os.access(wrapper, os.X_OK):
        return [str(wrapper)]
    if shutil.which("gradle") is not None:
        return ["gradle"]
    return None


def main() -> int:
    if not PILOT_DIR.is_dir():
        _log(f"pilot directory missing: {PILOT_DIR}")
        return EXIT_TOOLCHAIN_BROKEN

    gradle_cmd = _resolve_gradle(PILOT_DIR)
    if gradle_cmd is None:
        _log("toolchain absent — skipped (no ./gradlew and no `gradle` on PATH)")
        return EXIT_OK

    _log(f"running: {' '.join(gradle_cmd)} test")
    result = subprocess.run(
        [*gradle_cmd, "test", "--no-daemon", "--console=plain"],
        cwd=str(PILOT_DIR),
        check=False,
        text=True,
        capture_output=False,
    )
    if result.returncode != 0:
        _log(f"gradle reported failures (exit {result.returncode})")
        return EXIT_TEST_FAILED

    _log("OK — polyglot Kotlin pilot GREEN end-to-end")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())
