#!/usr/bin/env python3
"""Check docs/reference/ freshness; fail loudly on stale.

Usage:
    python scripts/hooks/check_documentation_freshness.py          # local hook
    python scripts/hooks/check_documentation_freshness.py --check  # CI (alias)

Exit codes:
    0 - Documentation is fresh
    1 - Pipeline error or docs are stale

Local and CI behavior are identical: stale state fails the push with a clear
remediation message. The previous "silent regenerate + git commit --amend"
local mode was removed because it composed unsafely with write_pages's prior
shutil.rmtree-based regeneration — silently deleting hand-authored files in
docs/reference/ from the pushed commit. See
docs/analysis/rca-pre-push-hook-untracked-deletion-2026-05-06.md.
"""

import importlib.util
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

    print(
        f"ERROR: docs/reference/ has {len(stale)} stale files: {', '.join(stale)}",
        file=sys.stderr,
    )
    print("Run the following to bring docs/reference/ up to date:", file=sys.stderr)
    print("  python scripts/docgen.py", file=sys.stderr)
    print("  git add docs/reference/", file=sys.stderr)
    print("  git commit --amend --no-edit  # or a fresh commit", file=sys.stderr)
    print("Then retry your push.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
