"""Smoke command — run the polyglot Rust pilot end-to-end.

Invocation::

    pipenv run python scripts/polyglot/smoke_rust_pilot.py

Behaviour:

1. ``cd tests/polyglot-pilot/rust/``.
2. If ``cargo`` is absent on PATH: log ``[polyglot-smoke] toolchain absent —
   skipped`` and exit 0 with WARNING. (Fail-open robustness — CI without
   Rust should not break unrelated test suites.)
3. ``cargo test`` (compiles + runs integration tests).
4. Exit 0 on success; non-zero on failure with the captured stderr.

The script is the single contract Python-side callers depend on. Both
manual human runs and the pytest wrapper at
``tests/polyglot-pilot/test_rust_smoke.py`` go through it.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PILOT_DIR = REPO_ROOT / "tests" / "polyglot-pilot" / "rust"

# Exit codes — distinguish skip (0) from failure (non-zero) and let callers
# branch on the structured stderr prefix.
EXIT_OK = 0
EXIT_TEST_FAILED = 1
EXIT_TOOLCHAIN_BROKEN = 2  # cargo present but exec failed unexpectedly


def _log(message: str) -> None:
    print(f"[polyglot-smoke] {message}", flush=True)


def _toolchain_present() -> bool:
    """Return True iff `cargo` is resolvable on PATH."""
    return shutil.which("cargo") is not None


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a command in cwd, streaming stdout+stderr to the parent."""
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=False,
    )


def main() -> int:
    if not PILOT_DIR.is_dir():
        _log(f"pilot directory missing: {PILOT_DIR}")
        return EXIT_TOOLCHAIN_BROKEN

    if not _toolchain_present():
        _log("toolchain absent — skipped (cargo not on PATH)")
        return EXIT_OK

    _log("running cargo test")
    result = _run(["cargo", "test", "--quiet"], cwd=PILOT_DIR)
    if result.returncode != 0:
        _log(f"cargo test reported failures (exit {result.returncode})")
        return EXIT_TEST_FAILED

    _log("OK — polyglot Rust pilot GREEN end-to-end")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())
