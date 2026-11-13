"""One case as written: 'ID | ARGV | EXPECT', its argv run without a shell and the expectation it must meet."""

from __future__ import annotations

import shlex

from nwstep.domain.baseline_check import BaselineCheck
from nwstep.domain.case_expectation import CaseExpectation
from nwstep.domain.case_result import CaseResult
from nwstep.domain.command_outcome import CommandOutcome
from nwstep.domain.protection_check import ProtectionCheck


class CaseSpec:
    def __init__(
        self, identifier: str, argv: tuple[str, ...], expectation: CaseExpectation
    ) -> None:
        self.identifier = identifier
        self.argv = argv
        self.expectation = expectation

    @classmethod
    def parse(cls, text: str) -> CaseSpec:
        head, separator, rest = text.partition("|")
        argv_text, second, expect_text = rest.rpartition("|")
        identifier = head.strip()
        if not separator or not second or not identifier or not argv_text.strip():
            raise ValueError("a case is written 'ID | ARGV | EXPECT'")
        try:
            argv = tuple(shlex.split(argv_text))
        except ValueError as error:
            raise ValueError(f"argv is not a valid command line: {error}") from None
        if not argv:
            raise ValueError("argv is empty")
        return cls(identifier, argv, CaseExpectation.parse(expect_text))

    def judge(
        self,
        outcome: CommandOutcome,
        baseline: BaselineCheck,
        protection: ProtectionCheck,
    ) -> CaseResult:
        return CaseResult(
            identifier=self.identifier,
            argv=self.argv,
            expectation=self.expectation.text,
            kind=self.expectation.kind,
            held=self.expectation.holds(outcome),
            observed=self.expectation.observed(outcome),
            exit_code=outcome.exit_code,
            output_tail=outcome.output_tail[-CaseResult.TAIL_LINES :],
            baseline=baseline,
            protection=protection,
        )
