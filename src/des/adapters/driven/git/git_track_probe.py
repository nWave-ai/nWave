"""git check-ignore probe (ADR-AG-004 (d)).

The behavioural probe proving the dual-layer gitignore reasoning, not just the
string edit. Returns whether the marker is TRACKABLE (i.e. NOT ignored by git)
after the gitignore fix, by invoking the real ``git check-ignore``.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


def is_tracked(project_root: Path, target: Path) -> bool:
    """Return True iff ``git check-ignore`` reports ``target`` as NOT ignored.

    ``git check-ignore`` exits 0 when the path IS ignored, 1 when it is NOT
    ignored, and 128 on error (e.g. not a repository). A path that is not
    ignored is trackable, so ``is_tracked`` returns True only on exit code 1.
    """
    try:
        result = subprocess.run(
            ["git", "check-ignore", str(target)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 1
