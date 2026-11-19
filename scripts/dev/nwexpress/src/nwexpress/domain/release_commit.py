"""Commits that carry a release type but change only documents: the pure rules the packet refusal applies.

A conventional commit type feat, fix, perf or refactor makes the version that a repository derives from its commits a
release (CLAUDE.md, "Before you commit"). A commit that changes only documents, or evidence under docs/, is docs; the
packet refuses to freeze a candidate whose commits from the recorded base to HEAD are release-typed and documents only.

Values only: no git, file or process is read here. The reader lives in the application and infrastructure layers.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

from nwexpress.domain.document_paths import is_document_only


RELEASE_TYPES: tuple[str, ...] = ("feat", "fix", "perf", "refactor")
DOCUMENT_TYPE = "docs"
_HEADER = re.compile(r"([a-z]+)(?:\([^()]*\))?!?:")


@dataclass(frozen=True)
class Commit:
    """A commit between the base and HEAD: its short hash, its subject and the paths it changes."""

    short: str
    subject: str
    paths: tuple[str, ...]


def release_type(subject: str) -> str | None:
    """The conventional type token of the subject when it is a release type, otherwise None.

    The token is read only from the start of the subject, before its scope, its bang or its colon: feature: and
    feat add notes name no release type.
    """
    match = _HEADER.match(subject)
    if match is None or match.group(1) not in RELEASE_TYPES:
        return None
    return match.group(1)


def refusable(commit: Commit) -> bool:
    """True when the commit names a release type and every path it changes is a document.

    A commit that changes no path is never refusable: is_document_only needs at least one path.
    """
    return release_type(commit.subject) is not None and is_document_only(
        list(commit.paths)
    )


def rewrite_text(root: str, commits: tuple[Commit, ...]) -> str:
    """One git command that rewrites the subject of each named commit to the docs type, in the repository at root.

    The commits are the refusable ones, oldest first. The todo editor marks only those commits as reword, and the
    message editor replaces the release type at the start of each reworded subject; no other commit or file changes.
    The command rebases from the parent of the oldest named commit, so the later commits are replayed with their trees.
    """
    selections = " ".join(
        f"-e 's/^pick {commit.short} /reword {commit.short} /'" for commit in commits
    )
    types = "|".join(RELEASE_TYPES)
    return (
        f'GIT_SEQUENCE_EDITOR="sed -i {selections}" '
        f"GIT_EDITOR=\"sed -i -E '1s/^({types})([(!:])/{DOCUMENT_TYPE}\\2/'\" "
        f"git -C {shlex.quote(root)} rebase -i {commits[0].short}^"
    )
