"""Repository-root resolver for the project ``.nwave/config.json``.

Authority: docs/product/architecture/brief.md#Repository-Rooted Configuration
Across Git Worktrees.

A git worktree checkout carries a ``.git`` FILE bearing ``gitdir:``
indirection rather than a ``.git`` DIRECTORY. Configuration must follow the
REPOSITORY, so a worktree has to ascend to the common root that owns the
tracked ``.git`` directory before deriving ``.nwave/config.json``.

Boundary: a DRIVEN ADAPTER, not a pure domain function -- it opens and reads
real files (the ``.git`` marker, then the ``commondir`` pointer inside the
worktree administrative directory it names), which is actual filesystem I/O.
The domain siblings this module used to sit beside, ``nwave_root.
resolve_nwave_root`` and ``repo_path_resolver.resolve_repo_root``, read ONLY
an environment variable and ``Path.cwd()`` -- never a file's CONTENTS -- and
are a different, genuinely pure class of function. It lives under
``adapters/driven/config/`` rather than ``adapters/driven/git/`` because its
sole purpose and sole consumer is resolving ``DESConfig``'s project config
path (co-located with ``des_config.py``), and every existing module under
``adapters/driven/git/`` shells out to the real ``git`` binary via
subprocess -- placing a module there that deliberately never does would
misleadingly suggest a git-binary dependency this resolver exists to avoid.
Still total and read-only, still no subprocess (the ``git`` binary is
explicitly forbidden as the mechanism, so the resolution stays portable to a
Python >=3.10 runtime with no git on PATH), still zero writes.

Failure algebra: EVERY unresolved branch degrades to the pre-fix identity --
``start`` returned unchanged -- and never to a fabricated root. Composed with
``DESConfig``'s existing fail-open cascade, the observable terminal for all of
those branches is the ordinary canonical-default behaviour.
"""

from __future__ import annotations

from pathlib import Path


_GITDIR_PREFIX = "gitdir:"


def resolve_repository_config_root(start: Path) -> Path:
    """Return the directory whose ``.nwave/config.json`` governs ``start``.

    (a) ``start/.git`` is a DIRECTORY, or absent -> return ``start``
        UNCHANGED. This is the exhaustive ordinary-checkout case at any
        working-directory depth: only a true checkout root carries a ``.git``
        entry at all, so a subdirectory keeps reading its own location exactly
        as it did before this resolver existed.

    (b) ``start/.git`` is a FILE -> follow git's own ``gitdir:`` marker to the
        per-worktree administrative directory, read the ``commondir`` file
        inside it, and return the parent of the resolved common ``.git``
        directory -- the repository root.

    Total: never raises, never writes.
    """
    marker = start / ".git"
    try:
        if not marker.is_file():
            return start
        contents = marker.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        return start

    worktree_git_dir = _resolve_gitdir_marker(contents, marker.parent)
    if worktree_git_dir is None:
        return start

    common_git_dir = _resolve_common_dir(worktree_git_dir)
    if common_git_dir is None:
        return start

    repository_root = common_git_dir.parent
    try:
        if not repository_root.is_dir():
            return start
    except OSError:
        return start
    return repository_root


def _resolve_gitdir_marker(contents: str, marker_parent: Path) -> Path | None:
    """The ``gitdir: <path>`` target, resolved against the marker's parent."""
    first_line = contents.splitlines()[0] if contents.splitlines() else ""
    if not first_line.startswith(_GITDIR_PREFIX):
        return None
    target_text = first_line[len(_GITDIR_PREFIX) :].strip()
    if not target_text:
        return None
    target = Path(target_text)
    if not target.is_absolute():
        target = marker_parent / target
    try:
        resolved = target.resolve()
        if not resolved.is_dir():
            return None
    except (OSError, ValueError, RuntimeError):
        return None
    return resolved


def _resolve_common_dir(worktree_git_dir: Path) -> Path | None:
    """The common ``.git`` directory named by git's own ``commondir`` file."""
    commondir_file = worktree_git_dir / "commondir"
    try:
        if not commondir_file.is_file():
            return None
        commondir_text = commondir_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        return None

    lines = commondir_text.splitlines()
    common_text = lines[0].strip() if lines else ""
    if not common_text:
        return None
    common = Path(common_text)
    if not common.is_absolute():
        common = worktree_git_dir / common
    try:
        resolved = common.resolve()
        if not resolved.is_dir():
            return None
    except (OSError, ValueError, RuntimeError):
        return None
    return resolved
