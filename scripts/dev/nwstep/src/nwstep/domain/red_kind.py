"""The kinds of refusal a RED can end in. Each names one reading of the report that does not accept the RED."""

from __future__ import annotations


class RedKind:
    NO_REPORT = "no-report"
    UNREADABLE = "unreadable"
    ABSENT = "absent"
    MISMATCH = "qualifier-mismatch"
    AMBIGUOUS = "ambiguous"
    ERRORED = "errored"
    PASSED = "passed"
    UNVERIFIED = "unverified"
