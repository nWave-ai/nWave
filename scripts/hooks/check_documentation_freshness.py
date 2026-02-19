#!/usr/bin/env python3
"""Pre-push hook: regenerate docs/reference/ if stale, amend the push commit.

Usage (called by pre-push hook):
    python scripts/hooks/check_documentation_freshness.py

Exit codes:
    0 - Documentation is fresh (or was auto-regenerated)
    1 - Regeneration failed
"""

import importlib.util
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


def main() -> int:
    output_dir = _ROOT / "docs" / "reference"

    try:
        pages = run_pipeline(_ROOT, output_dir)
    except Exception as e:
        print(f"ERROR: docgen pipeline failed: {e}", file=sys.stderr)
        return 1

    stale = check_pages(pages, output_dir)
    if not stale:
        print("✓ docs/reference/ is up to date")
        return 0

    # Regenerate
    print(f"Regenerating docs/reference/ ({len(stale)} stale files)...")
    write_pages(pages, output_dir)

    # Stage and amend
    subprocess.run(["git", "add", "docs/reference/"], check=True)
    subprocess.run(
        ["git", "commit", "--amend", "--no-edit"],
        check=True,
    )
    print("✓ docs/reference/ regenerated and amended into commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
