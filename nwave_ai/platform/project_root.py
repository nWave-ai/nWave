"""Project-root anchoring for project-local writers.

A session's working directory moves with ``cd``. A project-local file written
under it scatters one ``.nwave/`` per visited folder. Anchoring walks up from
the working directory to the nearest project marker, so every project-local
writer lands at the same root.

The pure functions take the start path and an injected marker predicate; the
only filesystem reads live in ``has_project_marker``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable

CLAUDE_PROJECT_DIR_ENV = "CLAUDE_PROJECT_DIR"

_NWAVE_MARKER = ".nwave"
_GIT_MARKER = ".git"
_REFUSED_SYSTEM_DIRECTORIES = ("/", "/usr", "/bin", "/etc", "/var", "/tmp")


def nearest_marked_directory(
    start: Path, is_marked: Callable[[Path], bool]
) -> Path | None:
    """Return ``start`` or its nearest ancestor for which ``is_marked`` holds."""
    candidates = (start, *start.parents)
    return next((item for item in candidates if is_marked(item)), None)


def project_root_for(
    start: Path, is_marked: Callable[[Path], bool], claude_project_dir: str | None
) -> Path:
    """Return the project root above ``start``.

    The nearest marked directory wins. Without one, an absolute
    ``CLAUDE_PROJECT_DIR`` names the root. With neither, ``start`` is kept so
    nothing changes outside a project. The environment value is a parameter so
    this function reads no ambient state.
    """
    nearest = nearest_marked_directory(start, is_marked)
    if nearest is not None:
        return nearest
    if claude_project_dir and Path(claude_project_dir).is_absolute():
        return Path(claude_project_dir)
    return start


def has_project_marker(directory: Path) -> bool:
    """True for an existing ``.nwave`` directory or a ``.git`` entry.

    A worktree checkout carries ``.git`` as a file, so any entry counts.
    """
    try:
        return (directory / _NWAVE_MARKER).is_dir() or (
            directory / _GIT_MARKER
        ).exists()
    except OSError:
        return False


def is_refused_project_root(directory: Path) -> bool:
    """Home and system directories never host project-local files."""
    return directory == Path.home() or str(directory) in _REFUSED_SYSTEM_DIRECTORIES


def _is_project_marker(directory: Path) -> bool:
    return not is_refused_project_root(directory) and has_project_marker(directory)


def anchor_to_project_root(start: Path) -> Path:
    """Project root for a working directory; refused directories never mark one.

    A relative start joins the current directory without resolving symlinks, so
    the home refusal still compares the real home path it is given.
    """
    absolute_start = start if start.is_absolute() else Path.cwd() / start
    return project_root_for(
        absolute_start, _is_project_marker, os.environ.get(CLAUDE_PROJECT_DIR_ENV)
    )
