"""Read the file paths of a project tree once, for the selector.

Effects only. The selector is a pure function of the paths this module lists: the files of
this tree. In a repository whose root holds its own version-control entry, the tree is what git lists: its
tracked files and its untracked files that are not ignored, so a git-ignored output (a build, a cache, a
local test folder) and a nested working copy (a directory with its own version-control entry, another tree)
are not part of it. git is not a runtime dependency: where git is absent, does not answer within its bound,
or fails, the tree is walked instead, which includes git-ignored output and leaves out nested working copies,
and one warning on standard error says why. A folder with no version-control entry of its own is walked
without asking git, and prints nothing. In every case hidden directories and the directories the project
declares in ``selection.ignore`` are left out, and symbolic links to directories are not followed. The text of
a file is read by the command the project declares.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nwave_ai.testrun.declaration import SelectionRules

# Git variables that would point the listing at another repository or index than the root's own.
_GIT_LOCATION = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
_GIT_TIMEOUT_SECONDS = 60


def read_project(root: Path, rules: SelectionRules) -> frozenset[str]:
    """Every file path of the tree under ``root``, tree-relative and with forward slashes."""
    listed, unanswered = _git_listing(root)
    if listed is None:
        if unanswered is not None:
            print(
                f"WARNING: git could not list the files of this repository ({unanswered}); "
                "the tree was walked instead, which includes git-ignored output and leaves "
                "out nested working copies.",
                file=sys.stderr,
            )
        listed = _walked(root, rules)
    ignored = set(rules.ignore)
    return frozenset(path for path in listed if _in_tree(path, ignored))


def _in_tree(path: str, ignored: set[str]) -> bool:
    """Whether a path lies in the tree: no hidden or declared-ignored directory on its way."""
    directories = path.split("/")[:-1]
    return not any(part.startswith(".") or part in ignored for part in directories)


def _git_listing(root: Path) -> tuple[frozenset[str] | None, str | None]:
    """What git lists for the repository whose top is ``root``, as ``(listing, None)``.

    ``(None, None)`` when ``root`` holds no version-control entry of its own: git is not asked, and the walk answers.
    ``(None, reason)`` when ``root`` is a repository and git could not answer: the walk answers, and ``reason``
    says why.
    """
    if not os.path.lexists(root / ".git"):
        return None, None
    try:
        top = _git(root, "rev-parse", "--show-toplevel")
        if top.returncode != 0:
            return None, f"git exited with status {top.returncode}"
        if not Path(top.stdout.strip()).samefile(root):
            return None, "this folder is not the top of the repository git found"
        listed = _git(
            root, "ls-files", "-z", "--cached", "--others", "--exclude-standard"
        )
    except subprocess.TimeoutExpired:
        return None, f"git did not answer within {_GIT_TIMEOUT_SECONDS:g} seconds"
    except FileNotFoundError:
        return None, "git is not on the search path"
    except OSError as error:
        return None, f"git could not be run: {error.strerror or error}"
    if listed.returncode != 0:
        return None, f"git exited with status {listed.returncode}"
    return (
        frozenset(
            path
            for path in listed.stdout.split("\0")
            if path and os.path.isfile(os.path.join(root, path))
        ),
        None,
    )


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """One git call in ``root``, with the location variables cleared and a bound on its time."""
    environment = {k: v for k, v in os.environ.items() if k not in _GIT_LOCATION}
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        env=environment,
        stdin=subprocess.DEVNULL,
        timeout=_GIT_TIMEOUT_SECONDS,
        check=False,
    )


def _walked(root: Path, rules: SelectionRules) -> frozenset[str]:
    """Every file under ``root`` by walking it, not entering hidden, declared-ignored or nested-checkout folders."""
    files: set[str] = set()
    ignored = set(rules.ignore)
    for directory, names, file_names in os.walk(root):
        names[:] = sorted(
            name
            for name in names
            if not name.startswith(".")
            and name not in ignored
            and not os.path.lexists(os.path.join(directory, name, ".git"))
        )
        inside = os.path.relpath(directory, root).replace(os.sep, "/")
        for name in file_names:
            files.add(name if inside == "." else f"{inside}/{name}")
    return frozenset(files)
