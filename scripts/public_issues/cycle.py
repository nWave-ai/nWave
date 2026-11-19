"""The silence cycle an issue is in: which maintainer comment started the silence, and what came after.

Comments are ordered by their position in the issue (GitHub's own order, ascending id), never by
their timestamp: GitHub stamps whole seconds, so two comments can share a second. Timestamps
measure the 36 hours of silence and, on a closed issue, place its close instant: a maintainer
comment after that instant is not the fix that started the silence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.public_issues.messages import REOPEN_BODIES, THANK_YOU


if TYPE_CHECKING:
    from scripts.public_issues.comment import Comment
    from scripts.public_issues.issue import Issue


@dataclass(frozen=True)
class Cycle:
    anchor: Comment
    thanked: bool
    replies: tuple[Comment, ...]
    announced: bool
    by_author: bool


def cycle_of(issue: Issue) -> Cycle | None:
    comments = issue.comments
    maintainers = [i for i, c in enumerate(comments) if _is_maintainer(c)]
    thanks = [i for i, c in enumerate(comments) if _is_ours(c, (THANK_YOU,))]
    anchor_at = _anchor_of(issue, maintainers, thanks)
    if anchor_at is None:
        return None
    replies = [
        (i, c) for i, c in enumerate(comments) if i > anchor_at and _is_person(c)
    ]
    announced = bool(replies) and any(
        i > replies[-1][0] and _is_ours(c, REOPEN_BODIES)
        for i, c in enumerate(comments)
    )
    return Cycle(
        anchor=comments[anchor_at],
        thanked=any(t >= anchor_at for t in thanks),
        replies=tuple(c for _, c in replies),
        announced=announced,
        by_author=any(c.author.login == issue.author.login for _, c in replies),
    )


def _anchor_of(issue: Issue, maintainers: list[int], thanks: list[int]) -> int | None:
    """The comment the silence is measured from: the fix reply that started it.

    An open issue is being worked on, so its latest maintainer comment started the silence, and
    a re-fix after a reopen is the latest one. A closed issue that has our thank-you was closed
    at its close instant: a maintainer comment after that instant is chatter and must not restart
    the silence, or the thank-you already posted would be posted again. When no maintainer
    comment precedes the close, our thank-you stands in as the anchor. Without a thank-you the
    latest maintainer comment is the anchor, as it always was.
    """
    if issue.is_open or not thanks:
        return maintainers[-1] if maintainers else None
    if issue.closed_at is not None:
        before_close = [
            i for i in maintainers if issue.comments[i].created_at <= issue.closed_at
        ]
    else:
        # a closed issue without a close instant: the latest thank-you bounds the close
        before_close = [i for i in maintainers if i < thanks[-1]]
    if before_close:
        return before_close[-1]
    return thanks[-1]


def _is_maintainer(comment: Comment) -> bool:
    return not comment.author.is_bot and comment.author.is_maintainer


def _is_person(comment: Comment) -> bool:
    return not comment.author.is_bot and not comment.author.is_maintainer


def _is_ours(comment: Comment, bodies: tuple[str, ...]) -> bool:
    return comment.author.is_bot and comment.body in bodies
