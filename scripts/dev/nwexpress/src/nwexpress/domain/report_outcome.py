"""The outcome of reading a command's open JUnit XML report: its testcases, an unreadable report, or no report.

JUnit XML is the open format that many runners emit natively. A testcase with a failure element failed an
assertion; one with an error element did not complete its setup; a testcase absent from the report did not run.
The parse reads only that format, so no runner's console line is ever read.
"""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass

from nwexpress.domain.report_case import ReportCase
from nwexpress.domain.report_status import ReportStatus

SUITE_ROOTS = ("testsuites", "testsuite")


@dataclass(frozen=True)
class ReadReport:
    cases: tuple[ReportCase, ...]


@dataclass(frozen=True)
class UnreadableReport:
    reason: str


@dataclass(frozen=True)
class NoReport:
    pass


ReportOutcome = ReadReport | UnreadableReport | NoReport


def parse_report(text: str) -> ReportOutcome:
    """The testcases of a JUnit XML document, or the reason it is not one; pure over its text."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        return UnreadableReport(f"the XML does not parse: {error}")
    if root.tag not in SUITE_ROOTS:
        return UnreadableReport(
            f"the root element is '{root.tag}', not a JUnit '{SUITE_ROOTS[0]}' or '{SUITE_ROOTS[1]}'"
        )
    return ReadReport(tuple(_case(node) for node in root.iter("testcase")))


def _case(node: ElementTree.Element) -> ReportCase:
    status, kind, message = _status(node)
    return ReportCase(
        name=node.get("name") or node.get("classname") or "",
        seconds=_seconds(node.get("time")),
        status=status,
        kind=kind,
        message=message,
        classname=node.get("classname") or "",
    )


def _status(node: ElementTree.Element) -> tuple[str, str, str]:
    for tag, status in (
        ("error", ReportStatus.ERRORED),
        ("failure", ReportStatus.FAILURE),
        ("skipped", ReportStatus.SKIPPED),
    ):
        child = node.find(tag)
        if child is not None:
            return (
                status,
                child.get("type") or "",
                child.get("message") or (child.text or "").strip(),
            )
    return ReportStatus.PASSED, "", ""


def _seconds(text: str | None) -> float:
    try:
        return float(text) if text else 0.0
    except ValueError:
        return 0.0
