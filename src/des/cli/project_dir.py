"""Worktree-stable project-directory resolution for DES CLI commands."""

from __future__ import annotations

import subprocess
from pathlib import Path


def resolve_project_dir(project_dir: str | Path, *, cwd: Path | None = None) -> Path:
    """Resolve a project directory without coupling it to the caller's subdirectory.

    Absolute paths denote themselves. Relative paths denote the same location
    from every directory in one git worktree: ``worktree_root / project_dir``.
    Outside a git worktree, resolution retains the conventional cwd-relative
    behaviour.
    """
    candidate = Path(project_dir)
    if candidate.is_absolute():
        return candidate

    effective_cwd = cwd or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=effective_cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return effective_cwd / candidate

    worktree_root = result.stdout.strip()
    if result.returncode != 0 or not worktree_root:
        return effective_cwd / candidate
    return Path(worktree_root) / candidate
