"""Names the candidate of a handoff with git: the commit HEAD is at, and whether the work tree differs from it.

git is optional. Whatever stops it from answering (git not on PATH, no repository, no commit
yet, no answer within the bound) becomes an Unnamed candidate that keeps the reason: nothing is
raised and nothing is assumed. The workspace directory is left out, by the rule the packet's reader
owns: its files change with each record and are not the candidate, so both give one candidate one name.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from nwstep.domain.prereview import Candidate, Committed, Modified, Unnamed
from nwstep.infrastructure.candidate_reader import changed_paths


class CandidateGit:
    TIMEOUT_S = 60

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

    def read(self, root: Path) -> Candidate:
        top = self._git(root, "rev-parse", "--show-toplevel")
        if isinstance(top, Unnamed):
            return top
        head = self._git(root, "rev-parse", "--verify", "HEAD^{commit}")
        if isinstance(head, Unnamed):
            return head
        status = self._git(root, "status", "--porcelain", "-z", "--untracked-files=all")
        if isinstance(status, Unnamed):
            return status
        changed = changed_paths(status, Path(top.strip()), self._workspace)
        return Modified(head.strip()) if changed else Committed(head.strip())

    @staticmethod
    def _git(root: Path, *arguments: str) -> str | Unnamed:
        try:
            done = subprocess.run(
                ["git", *arguments],
                cwd=root,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                encoding="utf-8",
                errors="surrogateescape",
                timeout=CandidateGit.TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return Unnamed(
                f"git {arguments[0]} gave no answer in {CandidateGit.TIMEOUT_S}s"
            )
        except OSError as error:
            return Unnamed(f"git could not start: {error.strerror or error}")
        if done.returncode != 0:
            message = " ".join(done.stderr.split()) or "no message"
            return Unnamed(f"git {arguments[0]} exited {done.returncode}: {message}")
        return done.stdout
