"""Discover sibling ``execution-log.json`` files within a git worktree (issue #79).

``--project-dir`` is resolved implicitly against the *process* CWD by every DES
log CLI. When an agent ``cd``s into a monorepo subdirectory mid-DELIVER, the same
relative string denotes a different absolute directory, and the log silently
forks into two divergent files.

This module supplies the evidence for a LOUD failure rather than a silent fork:
it locates the git worktree root of a target directory and enumerates the
``execution-log.json`` files already present under it. Re-anchoring relative
paths to the worktree root is deliberately NOT done here — that would change
behaviour for callers who legitimately pass a subdirectory-relative path.

Worktree resolution uses ``git rev-parse --show-toplevel``, which in a linked
worktree returns that worktree's own root (not the main checkout), matching the
containment boundary DELIVER runs in.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


LOG_FILENAME = "execution-log.json"

#: Directories never worth walking for a DELIVER log; pruning keeps the scan
#: bounded on large monorepos.
PRUNED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".next",
        "dist",
        "build",
        "target",
        "vendor",
    }
)

#: Upper bound on reported siblings — the diagnostic needs a name, not a census.
MAX_REPORTED_LOGS = 10


def _nearest_existing_dir(start: Path) -> Path | None:
    """Return *start* or its closest existing ancestor directory."""
    candidate = start if start.is_dir() else start.parent
    for path in [candidate, *candidate.parents]:
        if path.is_dir():
            return path
    return None


def worktree_root(start: Path) -> Path | None:
    """Return the git worktree root containing *start*, or None.

    Fail-open: any git failure (not a repository, git absent, timeout) yields
    None, and callers degrade to their previous behaviour.
    """
    probe = _nearest_existing_dir(start.absolute())
    if probe is None:
        return None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(probe),
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
    return Path(raw).resolve()


def _feature_id_of(log_path: Path) -> str | None:
    """Return the ``feature_id`` recorded in *log_path*, or None if unreadable."""
    try:
        data = json.loads(log_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    feature_id = data.get("feature_id")
    return feature_id if isinstance(feature_id, str) else None


def find_sibling_logs(
    target_dir: Path,
    feature_id: str | None = None,
    limit: int = MAX_REPORTED_LOGS,
) -> list[Path]:
    """Return ``execution-log.json`` files under *target_dir*'s worktree root.

    The log directly inside *target_dir* is excluded — the caller already knows
    about that one; what matters is the log living somewhere ELSE in the same
    worktree.

    Args:
        target_dir: The ``--project-dir`` the caller resolved.
        feature_id: When given, only logs recording this feature id are returned.
        limit: Maximum number of paths to return.

    Returns:
        Sorted absolute paths, empty when the worktree root cannot be resolved.
    """
    root = worktree_root(target_dir)
    if root is None:
        return []

    excluded = target_dir.absolute().resolve()
    found: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if name not in PRUNED_DIRECTORY_NAMES
        )
        if LOG_FILENAME not in filenames:
            continue
        current = Path(dirpath).resolve()
        if current == excluded:
            continue
        log_path = current / LOG_FILENAME
        if feature_id is not None and _feature_id_of(log_path) != feature_id:
            continue
        found.append(log_path)
        if len(found) >= limit:
            break

    return sorted(found)
