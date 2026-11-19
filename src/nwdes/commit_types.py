"""Conventional commit types, the kinds of path a commit stages, and the rule that picks a type.

This module imports nothing from nwdes. The commit rule (commits) and the command help and role
bundles (grammar, prompts) all read the one table here, so the type a record commit takes is
stated once.
"""

from __future__ import annotations

from enum import Enum


class CommitType(str, Enum):
    Feature = "feat"
    Fix = "fix"
    Docs = "docs"
    Style = "style"
    Refactor = "refactor"
    Performance = "perf"
    Test = "test"
    Build = "build"
    CI = "ci"
    Chore = "chore"
    Revert = "revert"


class PathKind(str, Enum):
    """What one selected path is for the commit type rule."""

    Record = "record"
    Document = "document"
    Test = "test"
    Code = "code"


RELEASE_TYPES = frozenset(
    (CommitType.Feature, CommitType.Fix, CommitType.Performance, CommitType.Refactor)
)
RECORD_TYPE = CommitType.Chore
DOCUMENT_TYPE = CommitType.Docs


def picked_type(kinds: frozenset[PathKind]) -> CommitType | None:
    """The type nwdes picks for a selection of run records and rendered documents; None when it stages product code or tests."""
    if not kinds or not kinds <= {PathKind.Record, PathKind.Document}:
        return None
    return DOCUMENT_TYPE if kinds == {PathKind.Document} else RECORD_TYPE
