"""The next state of a run, and the block a successful record or replay prints last.

next_state classifies the state once; next_block and the shell render from that kind.
Pure derivation: no I/O, the shell prints the lines.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NextKind(str, Enum):
    READY = "ready"
    COMPLETE = "complete"
    WAITING = "waiting"


@dataclass(frozen=True)
class NextState:
    kind: NextKind


def next_state(next_step_id: str | None, remaining: tuple[str, ...]) -> NextState:
    if next_step_id is not None:
        return NextState(NextKind.READY)
    if not remaining:
        return NextState(NextKind.COMPLETE)
    return NextState(NextKind.WAITING)


def next_block(
    next_step_id: str | None, remaining: tuple[str, ...], command: str
) -> tuple[str, ...]:
    kind = next_state(next_step_id, remaining).kind
    if kind is NextKind.READY:
        return (
            f"next step: {next_step_id}",
            f"ask for it with: {command}",
        )
    if kind is NextKind.COMPLETE:
        return (
            "next step: handoff (all steps recorded)",
            f"confirm with: {command}",
        )
    return (
        f"no step is ready; waiting on: {', '.join(remaining)}",
        f"ask again with: {command}",
    )
