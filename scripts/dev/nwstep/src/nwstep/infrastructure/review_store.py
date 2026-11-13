"""Reads and appends the review log of a workspace: one JSON line per frozen candidate, verdict or finding.

The caller holds the workspace lock while it reads, decides and appends. A workspace without the file has an
empty log, so a workspace created before the review existed reads as it always did.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from nwstep.domain import review
from nwstep.domain.refusal import Refusal
from nwstep.domain.review import ReviewLog


if TYPE_CHECKING:
    from nwstep.domain.review import Event
    from nwstep.infrastructure.workspace import Workspace


def read(workspace: Workspace) -> ReviewLog:
    path = workspace.review_path
    if not path.is_file():
        return ReviewLog()
    events: list[Event] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            event = review.from_value(value) if isinstance(value, dict) else None
            if event is None:
                raise ValueError(
                    f"line {number} is not a packet, a verdict or a finding"
                )
            events.append(event)
    except (OSError, UnicodeDecodeError, ValueError, TypeError) as error:
        raise Refusal(
            what=f"the review log {path} cannot be read: {error}",
            why="the findings, the frozen candidates and the verdicts of this run are read from that file; a damaged file would let a verdict or a finding be lost silently",
            how=f"restore {path} from a copy, or repair the named line; nothing is written until it reads",
        ) from None
    return ReviewLog(tuple(events))


def append(workspace: Workspace, event: Event) -> None:
    line = json.dumps(review.to_value(event), sort_keys=True)
    with workspace.review_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
