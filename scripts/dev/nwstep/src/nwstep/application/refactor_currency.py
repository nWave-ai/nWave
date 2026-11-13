"""Whether the commits a refactor record names are still the last commits that change code, read from git now.

A commit that changes only documents does not change the code the refactor judged, so it does not make the refactor
stale. Any other commit after the named refactor commits does.

What it proves: the named commits are the last code commits from the pre-feature commit to HEAD, as of now.
What it does not prove: that the refactor itself is right; only that the code judged is the code that exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nwstep.domain.document_paths import is_document_only
from nwstep.infrastructure.git_diff import GitDiffError
from nwstep.infrastructure.git_refs import GitRefs


REFACTOR_STEP = "refactor"
REFACTOR_FIELD = "post_refactor_commits"


@dataclass(frozen=True)
class RefactorCurrency:
    state: str  # "current", "stale" or "could-not-verify"
    reason: str

    @property
    def stale(self) -> bool:
        return self.state == "stale"

    @property
    def label(self) -> str:
        return f"{self.state}: {self.reason}"


def code_history(git: GitRefs) -> list[str]:
    """The commits from the base to HEAD, oldest first, that change at least one code file."""
    return [
        commit for commit in git.commits() if not is_document_only(git.files(commit))
    ]


def named_refactor_commits(records: list[Any]) -> list[str] | None:
    """The commit names of the latest refactor record, or None when no refactor record names any."""
    for record in reversed(records):
        if record.step == REFACTOR_STEP and REFACTOR_FIELD in record.values:
            return [str(name) for name in record.values[REFACTOR_FIELD]]
    return None


def check(git: GitRefs, names: list[str]) -> RefactorCurrency:
    """Compares the named refactor commits with the last code commits of the history, read from git now."""
    try:
        resolved = [git.resolve(name) for name in names]
        if not names or any(commit is None for commit in resolved):
            return RefactorCurrency(
                "stale",
                "the refactor record names a commit that does not exist in the repository",
            )
        history = git.commits()
        last_named = resolved[-1]
        if last_named not in history:
            return RefactorCurrency(
                "stale", "the named refactor commit is not in the history"
            )
        code = code_history(git)
        if code[-len(resolved) :] != resolved:
            last = code[-1] if code else None
            return RefactorCurrency(
                "stale",
                f"a commit after the refactor changed code: the last code commit is {last[:10] if last else 'none'}, not the named refactor commit",
            )
        skipped = [
            commit
            for commit in history[history.index(last_named) + 1 :]
            if is_document_only(git.files(commit))
        ]
        return RefactorCurrency(
            "current",
            f"the named refactor commits are still the last code commits; {len(skipped)} document-only commit(s) after them are ignored",
        )
    except GitDiffError as error:
        return RefactorCurrency("could-not-verify", str(error))
