"""The observed side effects and the commits of the change, read with git from BASE to HEAD and never typed by the executor.

When git cannot read the change, each section says so; it never shows an empty list as a fact.
"""

from __future__ import annotations

from nwstep.domain.baseline import Baseline
from nwstep.infrastructure.git_diff import GitDiff, GitDiffError


class ChangeFacts:
    SIDE_EFFECTS = "## Observed side effects (git, BASE to HEAD)"
    COMMITS = "## Commits (git log, BASE to HEAD)"

    def __init__(self, baseline: Baseline) -> None:
        self._baseline = baseline

    def lines(self) -> list[str]:
        if not self._baseline.is_available or self._baseline.top is None:
            return self._unverified(self._baseline.reason or "no baseline")
        try:
            diff = GitDiff(
                str(self._baseline.top), str(self._baseline.sha), working=False
            )
            entries = diff.name_status()
            counts = diff.line_counts()
            commits = diff.commits()
        except GitDiffError as error:
            return self._unverified(str(error))
        lines = [self.SIDE_EFFECTS, ""]
        if not entries:
            lines.append("- none: the change touches no file from BASE to HEAD")
        for status, path in entries:
            added, deleted = counts.get(path, (None, None))
            lines.append(f"- {status} {path} ({self._amount(added, deleted)})")
        lines += ["", self.COMMITS, ""]
        lines += [f"- {commit}" for commit in commits] or ["- none"]
        lines.append("")
        return lines

    def _unverified(self, reason: str) -> list[str]:
        return [
            self.SIDE_EFFECTS,
            "",
            f"- not verified: {reason}",
            "",
            self.COMMITS,
            "",
            f"- not verified: {reason}",
            "",
        ]

    @staticmethod
    def _amount(added: int | None, deleted: int | None) -> str:
        if added is None or deleted is None:
            return "binary"
        return f"+{added} -{deleted} lines"
