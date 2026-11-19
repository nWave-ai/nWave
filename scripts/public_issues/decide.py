"""The silence rule: one issue and one moment in, exactly one action out. Pure: no clock, no I/O.

The decision reconciles the state it finds. It never assumes that an earlier pass finished:
every intermediate state that a failed call can leave is an input with its own branch.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from scripts.public_issues.action import (
    Action,
    Close,
    DropClosedLabel,
    Nothing,
    RemoveMarker,
    Reopen,
    Thank,
)
from scripts.public_issues.cycle import cycle_of
from scripts.public_issues.labels import CLOSED_LABEL, KEEP_OPEN, MARKER


if TYPE_CHECKING:
    from scripts.public_issues.issue import Issue


SILENCE_WINDOW = timedelta(hours=36)


def decide(issue: Issue, now: datetime) -> Action:
    if issue.is_open:
        return _decide_open(issue, now)
    return _decide_closed(issue, now)


def _decide_open(issue: Issue, now: datetime) -> Action:
    marker = issue.has_label(MARKER)
    if issue.has_label(CLOSED_LABEL) and (not marker or issue.has_label(KEEP_OPEN)):
        return DropClosedLabel(
            "the issue is open and no close is pending: the stale closed-after-silence "
            "label is removed"
        )
    if not marker:
        return Nothing(
            "no fixed-awaiting-reply marker: the rule does not touch this issue"
        )
    if issue.has_label(KEEP_OPEN):
        return Nothing("keep-open is set: the rule never closes this issue")
    cycle = cycle_of(issue)
    if cycle is None:
        return Nothing("the marker is set but no maintainer has commented: left alone")
    if cycle.replies:
        return RemoveMarker(
            "a person who is not a maintainer commented after our last comment: "
            "the conversation is alive, so the marker is removed"
        )
    silence = now - cycle.anchor.created_at
    if silence >= SILENCE_WINDOW:
        return Close(
            f"the reporter stayed silent for {_describe(silence)} after our last comment; "
            "36 hours is the limit"
        )
    return Nothing(
        f"silent for {_describe(silence)} after our last comment; 36 hours are needed"
    )


def _decide_closed(issue: Issue, now: datetime) -> Action:
    if not issue.has_label(CLOSED_LABEL):
        return Nothing(
            "closed without closed-after-silence: closed by hand or not by this rule"
        )
    cycle = cycle_of(issue)
    if cycle is None:
        return Nothing(
            "closed-after-silence without a maintainer comment: nothing to compare with"
        )
    if cycle.replies:
        who = "the reporter" if cycle.by_author else "a person who is not the reporter"
        return Reopen(
            f"{who} commented after the reply that started the silence",
            by_author=cycle.by_author,
            announce=not cycle.announced,
        )
    if cycle.thanked:
        if issue.has_label(MARKER):
            return RemoveMarker(
                "the thank-you is already posted: the leftover marker is removed"
            )
        return Nothing("nobody has commented since the reply that started the silence")
    silence = now - cycle.anchor.created_at
    if silence >= SILENCE_WINDOW:
        return Thank(
            "the close is missing its thank-you and the silence holds: it is posted"
        )
    return Nothing(
        f"closed with the label; the thank-you waits until {_describe(SILENCE_WINDOW)} "
        f"of silence (now {_describe(silence)})"
    )


def _describe(delta: timedelta) -> str:
    minutes = max(0, int(delta.total_seconds() // 60))
    return f"{minutes // 60} h {minutes % 60:02d} min"
