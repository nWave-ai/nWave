"""Runs the pre-review checks the candidate declares when a step that asks for them is recorded.

Read, decide, write: the declaration file and the candidate are read, each declared command is
started once in the candidate, and the receipt is returned for the record. A declared check that
did not exit 0 is a refusal raised before the record is written, so nothing is recorded.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from nwstep.domain import prereview
from nwstep.domain.refusal import Refusal


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from nwstep.domain.journal import Journal
    from nwstep.domain.step import Step
    from nwstep.infrastructure.candidate_git import CandidateGit
    from nwstep.infrastructure.command_runner import CommandRunner


class PrereviewRun:
    def __init__(self, runner: CommandRunner, candidates: CandidateGit) -> None:
        self._runner = runner
        self._candidates = candidates

    def receipt(
        self,
        step: Step,
        root: Path,
        journal: Journal,
        keep: Callable[[str, str], Path],
    ) -> dict[str, Any]:
        """The receipt of this record; `keep` stores the full output of one check and returns where."""
        path = root / prereview.FILE
        declared = prereview.parse(self._text(path), str(path))
        candidate = self._candidates.read(root)
        results = [self._check(step, check, root, keep) for check in declared.checks]
        refusal = prereview.blocked(results)
        if refusal is not None:
            raise refusal
        earlier = [
            record.values[prereview.KEY]
            for record in journal.records
            if prereview.KEY in record.values
        ]
        fate = prereview.remote_request(declared, candidate, earlier)
        return prereview.receipt(candidate, results, self._remote(fate, root))

    def _check(
        self,
        step: Step,
        check: prereview.Check,
        root: Path,
        keep: Callable[[str, str], Path],
    ) -> prereview.CheckResult:
        outcome = self._runner.run(list(check.command), root)
        kept = keep(f"{step.id}.{prereview.KEY}.{check.name}", outcome.output)
        return prereview.CheckResult(check, outcome, str(kept))

    def _remote(
        self,
        fate: prereview.Request | prereview.Kept | prereview.Withheld | None,
        root: Path,
    ) -> dict[str, Any] | None:
        if fate is None:
            return None
        if not isinstance(fate, prereview.Request):
            return fate.as_value()
        outcome = self._runner.run(
            list(fate.command),
            root,
            {**os.environ, prereview.CANDIDATE_VARIABLE: fate.commit},
        )
        return fate.observed(outcome)

    @staticmethod
    def _text(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError) as error:
            raise Refusal(
                what=f"{path} cannot be read: {error}", why=prereview.WHY_DECLARED
            ) from None
