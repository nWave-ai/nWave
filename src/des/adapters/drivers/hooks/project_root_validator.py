"""Validate DES-PROJECT-ROOT marker values from agent prompts.

The marker carries the worktree-rooted project path so hook handlers can
resolve execution-log against the correct repo when the orchestrator's CWD
differs from the executing worktree (Rex RCA F-DES-WORKTREE-EXECUTION-LOG-
RESOLUTION).

Validation rules (Rex risk-matrix mitigation against path-injection):
  1. Marker value MUST be an absolute path
  2. Path MUST exist
  3. Path MUST be a git work tree
  4. Path MUST share git-common-dir with the fallback cwd (i.e., belong to
     the same repository — direct same-repo OR sibling worktree)

On any validation failure, returns None — callers fall back to hook_input cwd.
Validation is fail-safe: a malformed/malicious marker degrades to the previous
cwd-only behaviour rather than blocking the hook.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _git_common_dir(path: Path) -> str | None:
    """Return resolved git-common-dir for *path*, or None on any failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    # git-common-dir may be relative to cwd; resolve to absolute
    common = Path(raw)
    common = (path / common).resolve() if not common.is_absolute() else common.resolve()
    return str(common)


def validate_project_root(marker_value: str, fallback_cwd: str) -> Path | None:
    """Validate a DES-PROJECT-ROOT marker against the fallback cwd.

    Args:
        marker_value: Raw marker string from agent prompt.
        fallback_cwd: hook_input['cwd'] - the orchestrator's startup CWD.

    Returns:
        Resolved absolute Path on success; None on any validation failure
        (caller falls back to fallback_cwd).
    """
    if not marker_value:
        return None

    candidate = Path(marker_value)

    # Rule 1: absolute path
    if not candidate.is_absolute():
        return None

    # Rule 2: path exists
    if not candidate.exists():
        return None

    # Rule 3: is git work tree
    marker_common = _git_common_dir(candidate)
    if marker_common is None:
        return None

    # Rule 4: shares git-common-dir with fallback cwd (same repo)
    cwd_path = Path(fallback_cwd)
    if not cwd_path.exists():
        return None
    cwd_common = _git_common_dir(cwd_path)
    if cwd_common is None:
        return None

    if marker_common != cwd_common:
        return None

    return candidate.resolve()
