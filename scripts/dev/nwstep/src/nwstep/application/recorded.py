"""The result of an accepted record: the record, what the executor is offered next, warnings the record carries, the
steps it made stale, and the stale steps it replayed from their kept submissions."""

from __future__ import annotations

from dataclasses import dataclass

from nwstep.domain.record import Record
from nwstep.domain.step import Step


@dataclass(frozen=True)
class Recorded:
    record: Record
    next_step: Step | None
    remaining: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    stale: tuple[str, ...] = ()
    replayed: tuple[Recorded, ...] = ()
