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
import subprocess
from pathlib import Path


LOG_FILENAME = "execution-log.json"

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

    for log_path in _git_listed_logs(root):
        if log_path.parent == excluded:
            continue
        if feature_id is not None and _feature_id_of(log_path) != feature_id:
            continue
        found.append(log_path)
        if len(found) >= limit:
            break

    return sorted(found)


def _git_listed_logs(root: Path) -> list[Path]:
    """Return every ``execution-log.json`` git accounts for under *root*.

    Enumeration is delegated to ``git ls-files`` rather than walking the tree
    against a hand-maintained set of directory names to skip. That list would
    be a second, worse copy of the repository's own ``.gitignore``: it would
    miss whatever a given project ignores (``.direnv``, ``.turbo``, a vendored
    SDK) and would need editing every time a new build tool appeared. Git
    already knows precisely which paths belong to the project, so it is asked.

    ``--cached --others --exclude-standard`` covers tracked files plus
    untracked ones git would not ignore, which is exactly the set a DELIVER log
    can legitimately live in. A log inside an ignored directory is deliberately
    not reported: it is not part of the audit trail this diagnostic exists to
    protect.

    Fail-open: if git cannot answer, the caller degrades to naming no siblings
    rather than blocking on a diagnostic.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                f"*{LOG_FILENAME}",
                LOG_FILENAME,
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    if result.returncode != 0:
        return []

    return [
        (root / relative).resolve()
        for relative in result.stdout.split("\0")
        if relative
    ]
