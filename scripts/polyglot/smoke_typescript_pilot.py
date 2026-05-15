"""Smoke command — run the polyglot TypeScript pilot end-to-end.

Invocation::

    pipenv run python scripts/polyglot/smoke_typescript_pilot.py

Behaviour:

1. ``cd tests/polyglot-pilot/typescript/``.
2. If ``npx`` is absent on PATH: log ``[polyglot-smoke] toolchain absent —
   skipped`` and exit 0 with WARNING. (Fail-open robustness — CI without
   Node should not break unrelated test suites.)
3. ``npm install`` (only if ``node_modules`` absent).
4. ``npx vitest run``.
5. Exit 0 on success; non-zero on failure with the captured stderr.

The script is the single contract Python-side callers depend on. Both
manual human runs and the pytest wrapper at
``tests/polyglot-pilot/test_typescript_smoke.py`` go through it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PILOT_DIR = REPO_ROOT / "tests" / "polyglot-pilot" / "typescript"

# Exit codes — distinguish skip (0) from failure (non-zero) and let callers
# branch on the structured stderr prefix.
EXIT_OK = 0
EXIT_TEST_FAILED = 1
EXIT_TOOLCHAIN_BROKEN = 2  # npm/npx present but exec failed unexpectedly


def _log(message: str) -> None:
    print(f"[polyglot-smoke] {message}", flush=True)


def _toolchain_present() -> bool:
    """Return True iff `npx` is resolvable on PATH."""
    return shutil.which("npx") is not None and shutil.which("npm") is not None


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
        _log("toolchain absent — skipped (npm/npx not on PATH)")
        return EXIT_OK

    node_modules = PILOT_DIR / "node_modules"
    if not node_modules.is_dir():
        _log("installing npm dependencies (one-time per checkout)")
        install_env = os.environ.copy()
        # Keep npm output terse but visible.
        install_env.setdefault("npm_config_fund", "false")
        install_env.setdefault("npm_config_audit", "false")
        install_env.setdefault("npm_config_progress", "false")
        result = subprocess.run(
            ["npm", "install", "--no-fund", "--no-audit"],
            cwd=str(PILOT_DIR),
            check=False,
            text=True,
            env=install_env,
        )
        if result.returncode != 0:
            _log(f"npm install failed (exit {result.returncode})")
            return EXIT_TOOLCHAIN_BROKEN

    _log("running vitest")
    result = _run(["npx", "vitest", "run"], cwd=PILOT_DIR)
    if result.returncode != 0:
        _log(f"vitest reported failures (exit {result.returncode})")
        return EXIT_TEST_FAILED

    _log("OK — polyglot TypeScript pilot GREEN end-to-end")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - script entry point
    sys.exit(main())
