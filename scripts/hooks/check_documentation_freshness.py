#!/usr/bin/env python3
"""Check docs/reference/ freshness; auto-regenerate in local hooks, fail in CI.

Usage:
    python scripts/hooks/check_documentation_freshness.py          # local hook
    python scripts/hooks/check_documentation_freshness.py --check  # CI (no writes)

Exit codes:
    0 - Documentation is fresh (or was auto-regenerated locally)
    1 - Regeneration failed or docs are stale (CI mode)
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent.parent
_spec = importlib.util.spec_from_file_location(
    "docgen", _ROOT / "scripts" / "docgen.py"
)
_docgen = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_docgen)  # type: ignore[union-attr]
check_pages = _docgen.check_pages
run_pipeline = _docgen.run_pipeline
write_pages = _docgen.write_pages


def _is_ci() -> bool:
    return "--check" in sys.argv or os.environ.get("CI") == "true"


def main() -> int:
    output_dir = _ROOT / "docs" / "reference"
    ci_mode = _is_ci()

    try:
        pages = run_pipeline(_ROOT, output_dir)
    except Exception as e:
        print(f"ERROR: docgen pipeline failed: {e}", file=sys.stderr)
        return 1

    stale = check_pages(pages, output_dir)
    if not stale:
        print("✓ docs/reference/ is up to date")
        return 0

    if ci_mode:
        print(
            f"ERROR: docs/reference/ has {len(stale)} stale files: {', '.join(stale)}",
            file=sys.stderr,
        )
        print("Run 'python scripts/docgen.py' locally and commit.", file=sys.stderr)
        return 1

    # Local hook: regenerate, stage, and amend
    print(f"Regenerating docs/reference/ ({len(stale)} stale files)...")
    write_pages(pages, output_dir)

    subprocess.run(["git", "add", "docs/reference/"], check=True)
    subprocess.run(
        ["git", "commit", "--amend", "--no-edit"],
        check=True,
    )
    print("✓ docs/reference/ regenerated and amended into commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
