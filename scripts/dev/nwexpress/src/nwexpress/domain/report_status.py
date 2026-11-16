"""The status one testcase of an open JUnit report carries: passed, failure, error or skipped.

A failure is an assertion that did not hold; an error is a setup, collection or teardown that did not complete.
Both are read from the report's own elements, never from a runner's console line.
"""

from __future__ import annotations


class ReportStatus:
    PASSED = "passed"
    FAILURE = "failure"
    ERRORED = "error"
    SKIPPED = "skipped"
