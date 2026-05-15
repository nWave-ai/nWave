"""Phase 2 scaffold — git-diff-based delta path selector for nightly mutation runs.

Status: SCAFFOLD (not wired into any workflow yet). Phase 2 implements.
Owner: nw-platform-architect.

Contract (D-3, D-20):
- Input: git revision range (default HEAD~1..HEAD).
- Output: newline-separated *.py paths under src/des/, scripts/install/, nwave_ai/.
- Empty output → workflow takes no-op success branch (D-5).
"""

import sys


def select_changed_paths(revision_range: str = "HEAD~1..HEAD") -> list[str]:
    """Return changed *.py paths within mutation scope for the given revision range."""
    raise NotImplementedError(
        "Phase 2 scaffold — implement when wiring nightly workflow"
    )


if __name__ == "__main__":
    rev = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1..HEAD"
    paths = select_changed_paths(rev)
    for p in paths:
        print(p)
