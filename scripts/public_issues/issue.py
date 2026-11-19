"""One issue as the silence rule reads it: its state, labels, author and comments.

The comments are in the order GitHub assigned them (ascending id); the position of a comment is
its order, so no decision needs a timestamp except the elapsed time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from datetime import datetime

    from scripts.public_issues.author import Author
    from scripts.public_issues.comment import Comment


@dataclass(frozen=True)
class Issue:
    number: int
    is_open: bool
    author: Author
    labels: frozenset[str]
    comments: tuple[Comment, ...]
    closed_at: datetime | None = None

    def has_label(self, name: str) -> bool:
        return name in self.labels
