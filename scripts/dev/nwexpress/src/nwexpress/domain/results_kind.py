"""The kinds of problem the repository's results file of a RED can have after the RED run.

Each names one state the file is in: missing, empty or blank, not a readable report, or a report with no failing mapped test.
"""

from __future__ import annotations


class ResultsKind:
    MISSING = "missing"
    EMPTY = "empty"
    UNREADABLE = "unreadable"
    NO_FAILURE = "no-failure"
