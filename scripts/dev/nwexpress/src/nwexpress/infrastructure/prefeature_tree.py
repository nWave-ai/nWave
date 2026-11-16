"""Materialises the pre-feature tree from git for one step.

The tree of the base commit is written with git archive into a folder the caller names. When the with-block ends
normally (the step is recorded) the folder and its archive are removed. When the block is refused, the folder stays
until the next run of the same step replaces it, so the refusal can be inspected; the refusal message says so. When
the block is interrupted, or the tree cannot be written, the folder is removed. An empty base tree has nothing to
archive and yields an empty folder.
"""

from __future__ import annotations

import shutil
import subprocess
import tarfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from nwexpress.domain.refusal import Refusal

if TYPE_CHECKING:
    from nwexpress.domain.baseline import Baseline


@contextmanager
def materialized_tree(baseline: Baseline, target: Path) -> Iterator[Path]:
    """The base commit's tree in target, valid inside the with-block; see the module note for what remains on exit."""
    if baseline.top is None or baseline.sha is None:
        raise Refusal(
            what=f"the pre-feature tree cannot be read: {baseline.reason}",
            why="a RED or probe run needs the code as it was before the change, and no base commit is on record",
            how="initialize the workspace again from a revision that names a commit of the repository",
        )
    archive = target.with_name(target.name + ".tar")
    _remove(target)
    _remove(archive)
    try:
        _unpack(baseline, archive, target)
    except BaseException:
        _remove(archive)
        _remove(target)
        raise
    try:
        yield target
    except Refusal:
        _remove(archive)
        raise
    except BaseException:
        _remove(archive)
        _remove(target)
        raise
    _remove(archive)
    _remove(target)


def _unpack(baseline: Baseline, archive: Path, target: Path) -> None:
    target.mkdir(parents=True)
    listed = _git(baseline, "ls-tree", "-r", "--name-only", baseline.sha or "")
    if listed.returncode != 0:
        raise Refusal(
            what=f"git ls-tree of {baseline.sha} failed: {_detail(listed)}",
            why="the RED or probe run needs the pre-feature tree, and git could not list it",
            how=f"check that git -C {baseline.top} ls-tree {baseline.sha} succeeds, then run the step again",
        )
    if not listed.stdout.strip():
        return
    completed = _git(
        baseline, "archive", "--format=tar", "-o", str(archive), baseline.sha or ""
    )
    if completed.returncode != 0:
        raise Refusal(
            what=f"git archive of {baseline.sha} failed: {_detail(completed)}",
            why="the RED or probe run needs the pre-feature tree, and git could not write it",
            how=f"check that git -C {baseline.top} archive {baseline.sha} succeeds, then run the step again",
        )
    with tarfile.open(archive) as members:
        members.extractall(target, filter="data")


def _git(baseline: Baseline, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(baseline.top), *arguments],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=300,
        check=False,
    )


def _detail(completed: subprocess.CompletedProcess[bytes]) -> str:
    return completed.stderr.decode("utf-8", errors="replace").strip() or "no message"


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()
