"""One pass: find every issue that carries a label of the rule, settle each one, print one line per action.

An issue is settled one decision at a time: read it, decide with the pure rule, apply that one
action, and read again. The pass stops when a read decides Nothing. A close or a thank-you is a
claim of silence, so it is confirmed by a second read before its first write: a comment that
arrives in between changes the decision. A failed call stops the pass loudly; the next pass reads
whatever residue the failure left and decides again from it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from scripts.public_issues.action import (
    Action,
    Close,
    DropClosedLabel,
    Nothing,
    RemoveMarker,
    Reopen,
    Thank,
)
from scripts.public_issues.api_error import ApiError
from scripts.public_issues.decide import decide
from scripts.public_issues.github_issue import issue_from_json
from scripts.public_issues.labels import ALL_LABELS, CLOSED_LABEL, MARKER
from scripts.public_issues.messages import REOPENED, REOPENED_BY_COMMENT, THANK_YOU


if TYPE_CHECKING:
    from scripts.public_issues.github_api import GitHubApi
    from scripts.public_issues.issue import Issue
    from scripts.public_issues.run_mode import RunMode


LOOKBACK = timedelta(days=30)
MAX_STEPS = 8
Emit = Callable[[str], None]


def run_sweep(api: GitHubApi, now: datetime, mode: RunMode, emit: Emit) -> None:
    numbers = _candidates(api, now)
    _ensure_labels(api, mode, emit)
    if not numbers:
        emit(
            "nothing to do: no open issue carries fixed-awaiting-reply or "
            "closed-after-silence, and no issue closed in the last 30 days carries either label"
        )
    for number in numbers:
        _settle(api, number, now, mode, emit)


def _candidates(api: GitHubApi, now: datetime) -> list[int]:
    found: set[int] = set()
    for state, label in (
        ("open", MARKER),
        ("open", CLOSED_LABEL),
        ("closed", CLOSED_LABEL),
        ("closed", MARKER),
    ):
        for raw in api.issues_with_label(state, label):
            if state == "closed" and not _closed_recently(raw, now):
                continue
            found.add(int(raw["number"]))
    return sorted(found)


def _ensure_labels(api: GitHubApi, mode: RunMode, emit: Emit) -> None:
    present = api.label_names()
    for name in ALL_LABELS:
        if name in present:
            continue
        if mode.live:
            api.create_label(name)
            emit(f"label {name} created")
        else:
            emit(f"dry run: label {name} is missing and a live run would create it")


def _settle(
    api: GitHubApi, number: int, now: datetime, mode: RunMode, emit: Emit
) -> None:
    for step in range(MAX_STEPS):
        action = _decide_now(api, number, now)
        if isinstance(action, Nothing):
            if step == 0:
                emit(_line(number, action, mode))
            return
        if not mode.live:
            emit(_line(number, action, mode))
            return
        _apply(api, number, action)
        emit(_line(number, action, mode))
    raise ApiError(
        f"issue {number} did not settle in {MAX_STEPS} steps",
        "each step changed the state and the next read asked for another change",
        "read the issue on GitHub and check its labels and comments; no further change was made",
    )


def _decide_now(api: GitHubApi, number: int, now: datetime) -> Action:
    action = decide(_read(api, number), now)
    if isinstance(action, (Close, Thank)):
        # a claim of silence is made again on a fresh read before its first write
        return decide(_read(api, number), now)
    return action


def _apply(api: GitHubApi, number: int, action: Action) -> None:
    if isinstance(action, Close):
        api.add_label(number, CLOSED_LABEL)
        api.set_state(number, "closed", "completed")
    elif isinstance(action, RemoveMarker):
        api.remove_label(number, MARKER)
    elif isinstance(action, Thank):
        api.post_comment(number, THANK_YOU)
    elif isinstance(action, DropClosedLabel):
        api.remove_label(number, CLOSED_LABEL)
    elif isinstance(action, Reopen):
        if action.announce:
            api.post_comment(
                number, REOPENED if action.by_author else REOPENED_BY_COMMENT
            )
        api.set_state(number, "open")


def _read(api: GitHubApi, number: int) -> Issue:
    return issue_from_json(api.issue_json(number), api.comments_json(number))


def _closed_recently(raw: dict[str, Any], now: datetime) -> bool:
    closed_at = raw.get("closed_at")
    if not closed_at:
        return False
    stamp = datetime.fromisoformat(str(closed_at).replace("Z", "+00:00"))
    return stamp >= now - LOOKBACK


def _line(number: int, action: Action, mode: RunMode) -> str:
    if action.verb == "nothing":
        return f"#{number} nothing: {action.reason}"
    state = "applied" if mode.live else "not applied (dry run)"
    return f"#{number} {action.verb} {state}: {action.reason}"
