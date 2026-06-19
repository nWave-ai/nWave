#!/usr/bin/env python3
"""Unconditional e2e pre-push wrapper.

Invokes the e2e pytest suite on EVERY push, regardless of branch.

Decision (Ale 2026-05-19): e2e tests run on every push — branch
conditional gates are removed. Previous version checked the LOCAL
branch via ``git branch --show-current`` (gap: pushes like
``git push origin feature:master`` bypassed the gate). Subsequent
fix used destination refs; superseded again by unconditional
execution because any push must be safe — feature branches today
were not running e2e and shipped CI-red work to master via refspec
push.

Hook entry preserved (`scripts/hooks/run_e2e_if_master.py`) for
config-stability; file name is now historical, behavior is
unconditional.
"""

from __future__ import annotations

import subprocess
import sys


# Color codes (consistent with sibling scripts in scripts/hooks/).
BLUE = "\033[0;34m"
NC = "\033[0m"


def main(argv: list[str] | None = None) -> int:
    """Pre-push entry point. Returns exit code for the shell.

    Runs e2e SMOKE subset unconditionally per Ale 2026-05-19 mandate.
    """
    if argv is None:
        argv = sys.argv[1:]

    print(
        f"{BLUE}run_e2e_if_master: unconditional e2e on push — invoking "
        f"pytest -m 'e2e and e2e_smoke' (smoke subset)...{NC}"
    )
    # Pre-push runs the e2e SMOKE subset (4 critical-path files).
    # Full e2e remains gated by CI on PR. Decision ref:
    # docs/analysis/test-perf-research-2026-05-03.md (#1 ROI).
    cmd = [
        "uv",
        "run",
        "pytest",
        "-m",
        "e2e and e2e_smoke",
        "-n",
        "auto",
        "--dist=loadfile",
        "--tb=short",
        "-q",
        *argv,
    ]
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
