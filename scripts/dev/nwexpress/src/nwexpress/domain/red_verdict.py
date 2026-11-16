"""The verdict on a RED from its report and the tests the oracle maps to promises.

A RED is accepted when, for every mapped test, the report selects exactly one case for it and that case carries a failure
element: the test ran and failed. A failing body counts as a failure, whether the failing line is an assertion or an
exception raised in the body; no tool can know that the failing line is the intended assertion in any language, and that
judgement belongs to the independent review. The evidence each test gave (its failure type and message) is kept with the
verdict so the reviewer sees why it failed.

Each other reading is a refusal with its kind: no report was written (a compile error, a missing tool or a setup stop
before any test ran), the report is unreadable, a mapped test is absent from it (no test run or a wrong name), a mapped
name's qualifier is carried by none of the cases of its test (a case of another qualifier is another test), a mapped name
selects more than one case (ambiguous: the verdict would rest on whichever case the name reached), a mapped test carries
an error element (its setup or collection failed), or a mapped test carries neither a failure nor an error element
although the command failed (could not be verified). The verdict is pure over the parsed report.
"""

from __future__ import annotations

from dataclasses import dataclass

from nwexpress.domain.red_evidence import Evidence
from nwexpress.domain.red_kind import RedKind
from nwexpress.domain.report_case import ReportCase
from nwexpress.domain.report_outcome import (
    NoReport,
    ReportOutcome,
    UnreadableReport,
)
from nwexpress.domain.report_status import ReportStatus
from nwexpress.domain.test_name import TestName


@dataclass(frozen=True)
class Accepted:
    failing: tuple[str, ...]
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class Refused:
    kind: str
    names: tuple[str, ...]
    cause: str


RedVerdict = Accepted | Refused


def judge(
    outcome: ReportOutcome, mapped: tuple[TestName, ...], command_failed: bool
) -> RedVerdict:
    if isinstance(outcome, NoReport):
        return Refused(RedKind.NO_REPORT, (), "")
    if isinstance(outcome, UnreadableReport):
        return Refused(RedKind.UNREADABLE, (), outcome.reason)
    return _judge_cases(outcome.cases, mapped, command_failed)


def _judge_cases(
    cases: tuple[ReportCase, ...],
    mapped: tuple[TestName, ...],
    command_failed: bool,
) -> RedVerdict:
    absent: list[str] = []
    mismatched: list[tuple[str, tuple[str, ...]]] = []
    ambiguous: list[tuple[str, tuple[str, ...]]] = []
    errored: list[tuple[str, str]] = []
    unverified: list[str] = []
    passed: list[str] = []
    evidence: list[Evidence] = []
    for name in dict.fromkeys(mapped):
        found = name.key_matches(cases)
        if not found:
            absent.append(name.text)
            continue
        selected = name.select(cases)
        if not selected:
            mismatched.append((name.text, tuple(case.full_name for case in found)))
            continue
        if len(selected) > 1:
            ambiguous.append((name.text, tuple(case.full_name for case in selected)))
            continue
        case = selected[0]
        if case.status == ReportStatus.ERRORED:
            errored.append((name.text, case.message))
            continue
        if case.status != ReportStatus.FAILURE:
            if command_failed:
                unverified.append(name.text)
            else:
                passed.append(name.text)
            continue
        evidence.append(
            Evidence(
                name=name.text,
                case=case.name,
                status=ReportStatus.FAILURE,
                kind=case.kind,
                message=case.message,
            )
        )
    if absent:
        return Refused(RedKind.ABSENT, tuple(absent), "")
    if mismatched:
        return Refused(
            RedKind.MISMATCH,
            tuple(text for text, _found in mismatched),
            "; ".join(
                f"{text} does not match {', '.join(found)}"
                for text, found in mismatched
            ),
        )
    if ambiguous:
        return Refused(
            RedKind.AMBIGUOUS,
            tuple(text for text, _found in ambiguous),
            "; ".join(
                f"{text} matches {', '.join(found)}" for text, found in ambiguous
            ),
        )
    if errored:
        return Refused(
            RedKind.ERRORED,
            tuple(name for name, _message in errored),
            "; ".join(f"{name}: {message}" for name, message in errored),
        )
    if unverified:
        return Refused(RedKind.UNVERIFIED, tuple(unverified), "")
    if passed:
        return Refused(RedKind.PASSED, tuple(passed), "")
    if not evidence:
        return Refused(RedKind.ABSENT, (), "no mapped test is declared")
    return Accepted(
        tuple(dict.fromkeys(item.case for item in evidence)), tuple(evidence)
    )
