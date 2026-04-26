"""Worktree-aware resolution of the shared ``.git/hooks`` directory.

Single source of truth for both attribution install and uninstall paths.
Per RCA ``docs/analysis/rca-attribution-plugin-worktree-isolation.md``
Branch C, the same hooks-dir resolution logic existed in three places
(two in ``attribution_utils``, one in a sibling test fixture) and the
production callers picked the wrong git API (``--show-toplevel``) while
the sibling test had the right one (``--git-common-dir``). Extracting
the helper collapses the surface to one definition that all callers
share.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def resolve_hooks_dir() -> Path:
    """Return the absolute path to the shared ``.git/hooks`` directory.

    Works in both regular checkouts and linked worktrees by invoking
    ``git rev-parse --git-common-dir`` — the worktree-aware analogue of
    ``--show-toplevel``. In a linked worktree, ``.git`` is a pointer
    *file* (not a directory), so any caller that joins ``.git/hooks``
    onto the worktree top-level resolves to a non-existent path. The
    common-dir path resolves instead to the SHARED ``.git`` directory of
    the main checkout, which is also the right policy target — the
    ``prepare-commit-msg`` trailer applies to all branches and worktrees,
    not per-worktree.

    Pure function (only side effect: subprocess invocation against the
    surrounding git repo). No global state, no caching, no ``os.chdir``.
    Lets ``subprocess.CalledProcessError`` and friends propagate to the
    caller — the existing call sites already handle them.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    common_dir = Path(result.stdout.strip())
    # Some git versions return a path relative to cwd (notably for the
    # main worktree where the common dir is just ``.git``). Resolve to
    # absolute so callers can ``mkdir(parents=True)`` and chdir freely
    # without losing the reference.
    return (common_dir / "hooks").resolve()
