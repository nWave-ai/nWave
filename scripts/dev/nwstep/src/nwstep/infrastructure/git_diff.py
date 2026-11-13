"""Facts of the change from BASE, read with git.

Two modes. Working-tree mode (before craft) covers uncommitted and untracked files, so a test
written before the code exists is evidence. Committed mode (after craft) reads BASE to HEAD only.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


class GitDiffError(Exception):
    """A git fact could not be read; the message says why."""


class GitDiff:
    _HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

    def __init__(self, top: str, base: str, working: bool) -> None:
        self._top = top
        self._base = base
        self._working = working
        self._added: dict[str, frozenset[int]] | None = None
        self._untracked: frozenset[str] | None = None

    def names(self) -> frozenset[str]:
        if not self._working:
            output = self._git(
                "diff", "--name-only", "--no-renames", self._base, "HEAD"
            )
            return frozenset(
                line.strip() for line in output.splitlines() if line.strip()
            )
        return frozenset(self._tracked_names() | self._untracked_names())

    def name_status(self) -> list[tuple[str, str]]:
        """Committed mode: each changed path with its status letter (A, M or D), in path order."""
        output = self._git("diff", "--name-status", "--no-renames", self._base, "HEAD")
        entries: list[tuple[str, str]] = []
        for line in output.splitlines():
            status, _, path = line.partition("\t")
            if path:
                entries.append((status.strip(), path.strip()))
        return sorted(entries, key=lambda entry: entry[1])

    def line_counts(self) -> dict[str, tuple[int | None, int | None]]:
        """Committed mode: added and deleted lines per path; None for a binary file, which git does not count."""
        output = self._git("diff", "--numstat", "--no-renames", self._base, "HEAD")
        counts: dict[str, tuple[int | None, int | None]] = {}
        for line in output.splitlines():
            fields = line.split("\t", 2)
            if len(fields) != 3:
                continue
            added, deleted, path = fields
            counts[path] = (
                None if added == "-" else int(added),
                None if deleted == "-" else int(deleted),
            )
        return counts

    def commits(self) -> list[str]:
        """Committed mode: the commits from BASE to HEAD, oldest first, each as 'hash subject'."""
        output = self._git("log", "--reverse", "--format=%h %s", f"{self._base}..HEAD")
        return [line.strip() for line in output.splitlines() if line.strip()]

    def added_lines(self, path: str) -> frozenset[int]:
        if self._added is None:
            self._added = self._parse(self._diff_text())
        if path in self._untracked_names():
            text = self.text(path)
            return (
                frozenset(range(1, len(text.splitlines()) + 1)) if text else frozenset()
            )
        return self._added.get(path, frozenset())

    def text(self, path: str) -> str | None:
        if self._working:
            file = Path(self._top) / path
            if not file.is_file():
                return None
            try:
                return file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return None
        try:
            return self._git("show", f"HEAD:{path}")
        except GitDiffError:
            return None

    def _diff_text(self) -> str:
        pinned = [
            "diff",
            "-U0",
            "--no-renames",
            "--no-ext-diff",
            "--src-prefix=a/",
            "--dst-prefix=b/",
        ]
        if self._working:
            return self._git(*pinned, self._base)
        return self._git(*pinned, self._base, "HEAD")

    def _tracked_names(self) -> set[str]:
        output = self._git("diff", "--name-only", "--no-renames", self._base)
        return {line.strip() for line in output.splitlines() if line.strip()}

    def _untracked_names(self) -> frozenset[str]:
        if self._untracked is None:
            output = self._git("ls-files", "--others", "--exclude-standard")
            self._untracked = frozenset(
                line.strip() for line in output.splitlines() if line.strip()
            )
        return self._untracked

    def _parse(self, text: str) -> dict[str, frozenset[int]]:
        added: dict[str, set[int]] = {}
        current: str | None = None
        for line in text.splitlines():
            if line.startswith("+++ "):
                target = line[len("+++ ") :]
                current = None if target == "/dev/null" else target.removeprefix("b/")
                if current is not None:
                    added.setdefault(current, set())
                continue
            match = self._HUNK.match(line)
            if match is None or current is None:
                continue
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1
            added[current].update(range(start, start + count))
        return {path: frozenset(lines) for path, lines in added.items()}

    def _git(self, *args: str) -> str:
        try:
            completed = subprocess.run(
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
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise GitDiffError(f"git {args[0]} failed: {detail}")
        return completed.stdout.decode("utf-8", errors="replace")
