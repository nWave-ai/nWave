"""The packet's reading of the commits that carry a release type and change only documents.

A thin shell: it reads the commits from the recorded base to HEAD with git, decides with domain/release_commit, and
returns the refusal the packet raises. Nothing is written here; the packet raises the refusal before it writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwexpress.domain import release_commit
from nwexpress.domain.refusal import Refusal
from nwexpress.infrastructure.git_refs import GitRefs


if TYPE_CHECKING:
    from pathlib import Path

    from nwexpress.domain.release_commit import Commit


WHY = (
    "a repository that derives its version from conventional commits turns feat into a minor release and fix, perf "
    "and refactor into patch releases (CLAUDE.md, Before you commit); a commit that changes only documents or evidence "
    f"is {release_commit.DOCUMENT_TYPE} or chore, so it must not carry a release type"
)


def read_commits(root: Path, base: str) -> tuple[Commit, ...]:
    """The commits from the base to HEAD, oldest first, each with its short hash, subject and changed paths.

    Raises GitDiffError when git cannot answer; nothing is returned as an empty list in that case.
    """
    git = GitRefs(str(root), base)
    return tuple(
        release_commit.Commit(
            git.short(full), git.subject(full), tuple(git.files(full))
        )
        for full in git.commits()
    )


def refusal(commits: tuple[Commit, ...], root: Path) -> Refusal | None:
    """The refusal that names every commit carrying a release type over documents only; None when there is none."""
    refused = tuple(commit for commit in commits if release_commit.refusable(commit))
    if not refused:
        return None
    listing = "; ".join(
        f"{commit.short} '{commit.subject}' (use {release_commit.DOCUMENT_TYPE})"
        for commit in refused
    )
    return Refusal(
        what=f"{len(refused)} commit(s) carry a release type but change only documents: {listing}",
        why=WHY,
        how=release_commit.rewrite_text(str(root), refused),
    )
