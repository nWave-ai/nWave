"""Reads GitHub's issue and comment objects into the rule's types. The only place raw fields are named."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from scripts.public_issues.api_error import ApiError
from scripts.public_issues.author import Author
from scripts.public_issues.comment import Comment
from scripts.public_issues.issue import Issue


def issue_from_json(
    raw_issue: dict[str, Any], raw_comments: list[dict[str, Any]]
) -> Issue:
    try:
        return Issue(
            number=int(raw_issue["number"]),
            is_open=raw_issue["state"] == "open",
            author=_author(
                raw_issue["user"], raw_issue.get("author_association", "NONE")
            ),
            labels=frozenset(label["name"] for label in raw_issue.get("labels", [])),
            comments=tuple(_comment(raw) for raw in _in_id_order(raw_comments)),
            closed_at=_time(raw_issue["closed_at"])
            if raw_issue.get("closed_at")
            else None,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ApiError(
            f"issue {raw_issue.get('number', '?')} has a field the rule cannot read",
            f"the field is missing or has another shape: {error}",
            "check the issue in GitHub; the rule takes no action on it in this pass",
        ) from error


def _in_id_order(raw_comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(raw_comments, key=lambda raw: int(raw["id"]))


def _comment(raw: dict[str, Any]) -> Comment:
    return Comment(
        author=_author(raw["user"], raw.get("author_association", "NONE")),
        created_at=_time(raw["created_at"]),
        body=str(raw.get("body") or ""),
    )


def _author(user: dict[str, Any], association: str) -> Author:
    return Author(
        login=str(user["login"]),
        association=str(association),
        account_type=str(user.get("type", "User")),
    )


def _time(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))
