#!/usr/bin/env python3
"""Hook wiring: collect test suite runtime telemetry after pytest runs.

Called as a post-step from pre-commit / pre-push hooks. Captures the
pytest output already produced, parses wall-clock and test count, and
appends one JSONL entry to the telemetry log.

Contract:
  - NEVER fails commit/push (always exits 0).
  - Observation-only: no threshold enforcement.
  - Accepts pytest stdout+stderr via stdin OR --output-file flag.

Typical usage in validate_tests.py (called after subprocess.run):

    from scripts.hooks.test_runtime_observe import observe_runtime
    observe_runtime(test_output, scope="unit", project_root=Path("."))
"""

from __future__ import annotations

import sys
from pathlib import Path


def observe_runtime(
    pytest_output: str,
    scope: str,
    project_root: Path,
) -> None:
    """Parse pytest_output and append one telemetry entry.

    Silently ignores all errors — this is observation infrastructure,
    not a correctness gate.
    """
    try:
        # Import here to avoid hard-dependency at import time
        from scripts.observability.test_runtime_collector import collect

        collect(pytest_output, scope=scope, project_root=project_root)
    except Exception:
        # Observation must never block the pipeline
        pass


def main() -> int:
    """Standalone invocation: reads pytest output from stdin."""
    try:
        pytest_output = sys.stdin.read()
        project_root = Path.cwd()
        observe_runtime(pytest_output, scope="all", project_root=project_root)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
