"""Records the base commit of a workspace: the repository's top and the commit the revision names.

Nothing is copied: the tree of the base commit is read from git by the steps that need it (see prefeature_tree). Every
failure is returned as an unavailable Baseline with its reason; nothing is passed silently.
"""

from __future__ import annotations

from pathlib import Path

from nwexpress.domain.baseline import Baseline
from nwexpress.infrastructure import worktree_git
from nwexpress.infrastructure.commit_hooks_git import GitHooksError, toplevel


class BaselineExport:
    def create(self, root: Path, rev: str) -> Baseline:
        if rev.startswith("-"):
            return Baseline.unavailable(f"'{rev}' is not a revision")
        top = toplevel(root)
        if top is None:
            return Baseline.unavailable(f"{root} is not inside a git repository")
        sha = worktree_git.resolve_commit(top, rev)
        if sha is None:
            return Baseline.unavailable(f"'{rev}' is not a commit of {top}")
        try:
            worktree_git.common_directory(top)
        except GitHooksError as error:
            return Baseline.unavailable(f"git cannot read {top}: {error}")
        return Baseline.available(top=str(top), sha=sha)
