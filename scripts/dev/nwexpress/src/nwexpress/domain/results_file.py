"""The repository's results file of a RED, judged after the RED run: the evidence the commit carries.

The RED runs on the pre-feature tree, so its report is never written into the repository. The results path names a
repository file, and that file is what the commit keeps as the proof that the mapped tests failed on the base. It is
refused when it is missing, when it holds no bytes or only whitespace, when it is not a readable JUnit report, or when
no mapped test failed in it: a RED report with no failing mapped test is not a RED. The judgement is the RED verdict's own
(red_verdict.judge, command failed), so the same mapped tests decide both. Pure over the bytes; the shell reads the file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nwexpress.domain.red_kind import RedKind
from nwexpress.domain.red_verdict import Refused, judge
from nwexpress.domain.report_outcome import parse_report
from nwexpress.domain.results_kind import ResultsKind
from nwexpress.domain.results_problem import ResultsProblem


if TYPE_CHECKING:
    from nwexpress.domain.test_name import TestName


def judge_results(
    data: bytes | None, mapped: tuple[TestName, ...]
) -> ResultsProblem | None:
    """None when the file is a report in which every mapped test failed; otherwise the problem it has."""
    if data is None:
        return ResultsProblem(ResultsKind.MISSING, "")
    if not data.strip():
        return ResultsProblem(
            ResultsKind.EMPTY, "0 bytes" if not data else "only whitespace"
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        return ResultsProblem(
            ResultsKind.UNREADABLE, f"the file cannot be read as text: {error}"
        )
    verdict = judge(parse_report(text), mapped, command_failed=True)
    if not isinstance(verdict, Refused):
        return None
    if verdict.kind == RedKind.UNREADABLE:
        return ResultsProblem(ResultsKind.UNREADABLE, verdict.cause)
    names = ", ".join(verdict.names) or "none"
    return ResultsProblem(
        ResultsKind.NO_FAILURE,
        f"the mapped test(s) {names} are not reported as failed ({verdict.kind})",
    )
