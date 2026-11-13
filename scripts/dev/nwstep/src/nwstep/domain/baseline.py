"""The pre-feature tree a workspace was initialized with, or the loud reason there is none.

The commit steps and the identity that make the exported tree a repository are pure data: the effect adapter runs them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GitIdentity:
    name: str
    email: str


PRE_FEATURE_IDENTITY = GitIdentity(name="nwstep", email="nwstep@localhost")


def identity_environment(
    identity: GitIdentity = PRE_FEATURE_IDENTITY,
) -> dict[str, str]:
    """Environment variables that give the commit the identity whatever the process environment holds.

    Environment variables take precedence over git configuration, so the identity is passed both ways.
    """
    return {
        "GIT_AUTHOR_NAME": identity.name,
        "GIT_AUTHOR_EMAIL": identity.email,
        "GIT_COMMITTER_NAME": identity.name,
        "GIT_COMMITTER_EMAIL": identity.email,
    }


def pre_feature_commit_steps(
    sha: str, identity: GitIdentity = PRE_FEATURE_IDENTITY
) -> tuple[tuple[str, ...], ...]:
    """The git calls, in order, that turn an unpacked tree into one commit of its own.

    Hooks and the user's signing requirement are switched off for this commit only, so no user
    configuration decides whether the pre-feature commit exists. The empty template keeps the
    user's hook templates out of the new repository.
    """
    commit_configuration = (
        "-c",
        f"user.name={identity.name}",
        "-c",
        f"user.email={identity.email}",
        "-c",
        "commit.gpgSign=false",
        "-c",
        f"core.hooksPath={os.devnull}",
    )
    return (
        ("init", "--quiet", "--template="),
        ("add", "--force", "--all"),
        (
            *commit_configuration,
            "commit",
            "--quiet",
            "--allow-empty",
            "--message",
            f"pre-feature tree of {sha}",
        ),
    )


@dataclass(frozen=True)
class Baseline:
    top: str | None
    sha: str | None
    directory: str | None
    reason: str | None

    @classmethod
    def available(cls, top: str, sha: str, directory: str) -> Baseline:
        return cls(top=top, sha=sha, directory=directory, reason=None)

    @classmethod
    def unavailable(cls, reason: str) -> Baseline:
        return cls(top=None, sha=None, directory=None, reason=reason)

    @property
    def is_available(self) -> bool:
        return self.reason is None

    def unverifiable_for(self, root: Path) -> str | None:
        """Why the differential cannot run for a record in this root; None when it can."""
        if self.reason is not None:
            return self.reason
        if self.top is None or Path(self.top).resolve() != root.resolve():
            return f"the record root {root} is not the repository {self.top} that the pre-feature tree was taken from"
        if self.directory is None or not Path(self.directory).is_dir():
            return (
                f"the pre-feature tree {self.directory} is missing from the workspace"
            )
        return None

    def tree(self) -> Path:
        if self.directory is None:
            raise ValueError("an unavailable baseline has no tree")
        return Path(self.directory)

    def to_value(self) -> dict[str, Any]:
        return {
            "top": self.top,
            "sha": self.sha,
            "directory": self.directory,
            "reason": self.reason,
        }

    @classmethod
    def from_value(cls, value: dict[str, Any]) -> Baseline:
        return cls(
            top=value["top"],
            sha=value["sha"],
            directory=value["directory"],
            reason=value["reason"],
        )
