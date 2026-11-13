"""Commit facts of the change from BASE, read with git: the commits oldest first, the files one commit touches,
and a commit's tree exported to a directory so that a command can run against it.

Every failure raises GitDiffError with the reason; nothing is returned as an empty fact.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import tarfile
from pathlib import Path

from nwstep.infrastructure.git_diff import GitDiffError


class GitRefs:
    def __init__(self, top: str, base: str) -> None:
        self._top = top
        self._base = base

    def commits(self) -> list[str]:
        """Full hashes of the commits from BASE to HEAD, oldest first."""
        return self._lines("rev-list", "--reverse", f"{self._base}..HEAD")

    def resolve(self, revision: str) -> str | None:
        """The full hash of a commit, or None when the revision names no commit."""
        if revision.startswith("-"):
            return None
        completed = self._run(
            "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}"
        )
        if completed.returncode != 0:
            return None
        return completed.stdout.decode("utf-8").strip()

    def subject(self, commit: str) -> str:
        return self._text("log", "-1", "--format=%s", commit).strip()

    def parent(self, commit: str) -> str | None:
        """The first parent, or None for a root commit."""
        return self.resolve(f"{commit}^")

    def files(self, commit: str) -> list[str]:
        return self._lines(
            "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", commit
        )

    def export(self, commit: str, target: Path) -> Path:
        """The tree of the commit, unpacked into target (replaced when it exists)."""
        archive = self._run("archive", "--format=tar", commit)
        if archive.returncode != 0:
            detail = archive.stderr.decode("utf-8", errors="replace").strip()
            raise GitDiffError(f"git archive of {commit} failed: {detail}")
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tree:
            tree.extractall(target, filter="data")
        return target

    def _lines(self, *args: str) -> list[str]:
        return [line.strip() for line in self._text(*args).splitlines() if line.strip()]

    def _text(self, *args: str) -> str:
        completed = self._run(*args)
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise GitDiffError(
                f"git {args[0]} failed: {detail or 'exit ' + str(completed.returncode)}"
            )
        return completed.stdout.decode("utf-8", errors="replace")

    def _run(self, *args: str) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(
                ["git", "-C", self._top, *args],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                timeout=300,
                check=False,
            )
        except OSError as error:
            raise GitDiffError(
                f"git cannot be run: {error.strerror or error}"
            ) from None
