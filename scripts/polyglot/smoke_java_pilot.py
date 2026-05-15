"""Smoke command — run the polyglot Java pilot end-to-end.

Invocation::

    pipenv run python scripts/polyglot/smoke_java_pilot.py

Behaviour:

1. ``cd tests/polyglot-pilot/java/``.
2. If neither ``mvn`` nor ``./mvnw`` is resolvable: log ``[polyglot-smoke]
   toolchain absent — skipped`` and exit 0 with WARNING. (Fail-open
   robustness — CI without Java/Maven should not break unrelated suites.)
3. ``mvn test`` (or ``./mvnw test`` if local wrapper is present).
4. Exit 0 on success; non-zero on failure with the captured stderr.

The script is the single contract Python-side callers depend on. Both
manual human runs and the pytest wrapper at
``tests/polyglot-pilot/test_java_smoke.py`` go through it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PILOT_DIR = REPO_ROOT / "tests" / "polyglot-pilot" / "java"

# Exit codes — distinguish skip (0) from failure (non-zero).
EXIT_OK = 0
EXIT_TEST_FAILED = 1
EXIT_TOOLCHAIN_BROKEN = 2  # maven present but exec failed unexpectedly


def _log(message: str) -> None:
    print(f"[polyglot-smoke] {message}", flush=True)


def _resolve_maven(pilot_dir: Path) -> list[str] | None:
    """Return the command to invoke Maven, or None if no toolchain available.

    Prefers a local ``./mvnw`` wrapper (Unix) or ``mvnw.cmd`` (Windows) inside
    the pilot directory so projects can pin a wrapper version. Falls back to
    ``mvn`` on PATH.
    """
    if os.name == "nt":
        wrapper = pilot_dir / "mvnw.cmd"
        if wrapper.is_file():
            return [str(wrapper)]
    else:
        wrapper = pilot_dir / "mvnw"
        if wrapper.is_file() and os.access(wrapper, os.X_OK):
            return [str(wrapper)]
    mvn = shutil.which("mvn")
    if mvn is not None:
        return [mvn]
    return None


def _java_present() -> bool:
    """Return True iff a `java` runtime is resolvable on PATH."""
    return shutil.which("java") is not None


def main() -> int:
    if not PILOT_DIR.is_dir():
        _log(f"pilot directory missing: {PILOT_DIR}")
        return EXIT_TOOLCHAIN_BROKEN

    if not _java_present():
        _log("toolchain absent — skipped (java not on PATH)")
        return EXIT_OK

    mvn_cmd = _resolve_maven(PILOT_DIR)
    if mvn_cmd is None:
        _log("toolchain absent — skipped (neither mvn nor ./mvnw resolvable)")
        return EXIT_OK

    _log(f"running {' '.join(mvn_cmd)} test")
    # Keep maven output terse but visible. Surefire prints test summary.
    env = os.environ.copy()
    env.setdefault("MAVEN_OPTS", "-Xmx512m")
    result = subprocess.run(
        [*mvn_cmd, "-B", "test"],
        cwd=str(PILOT_DIR),
        check=False,
        text=True,
        capture_output=False,
        env=env,
    )
    if result.returncode != 0:
        _log(f"maven reported failures (exit {result.returncode})")
        return EXIT_TEST_FAILED

    _log("OK — polyglot Java pilot GREEN end-to-end")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())
