"""The commit the nwstep checkout is at, or None when that checkout is not a git repository or git cannot run."""

from __future__ import annotations

from nwstep.infrastructure.git_diff import GitDiffError
from nwstep.infrastructure.git_refs import GitRefs
from nwstep.infrastructure.package_paths import PackagePaths


class CheckoutCommit:
    @staticmethod
    def read() -> str | None:
        # A venv inside a user's repository would otherwise resolve that repository's commit by
        # walking up from the package; the nwstep checkout must own its own .git.
        if not (PackagePaths.REPOSITORY / ".git").exists():
            return None
        try:
            return GitRefs(str(PackagePaths.REPOSITORY), "HEAD").resolve("HEAD")
        except GitDiffError:
            return None
