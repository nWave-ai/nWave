"""One comment on an issue: who wrote it and when."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from datetime import datetime

    from scripts.public_issues.author import Author


@dataclass(frozen=True)
class Comment:
    author: Author
    created_at: datetime
    body: str = ""
