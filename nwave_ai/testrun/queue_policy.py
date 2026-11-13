"""The decisions of the test queue: who is next, how many may run, who is ahead.

Pure. The queue of the account (``account_queue``) asks these functions while it holds
its lock; nothing here reads a clock, a file or the machine. A waiting run carries its
own class rank and aging threshold, written by the project that enqueued it, so every
process that looks at the same queue names the same head whatever its own declaration.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nwave_ai.testrun.refusal import Refusal


if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class Waiting:
    """A run that waits: arrival number, class rank (0 goes first), wait and threshold."""

    ticket: int
    rank: int
    waited_seconds: float
    aging_seconds: float

    def aged(self) -> bool:
        """A run of a later class that has waited at least its threshold."""
        return self.rank > 0 and self.waited_seconds >= self.aging_seconds


@dataclass(frozen=True)
class CapacityLimits:
    """What a project declares a run needs; the defaults are the declared fallbacks."""

    max_concurrent: int = 1
    cores_per_run: float = 1.0
    memory_per_run_mb: int = 2048


@dataclass(frozen=True)
class MachineCapacity:
    """What was detected on the machine; ``None`` means it could not be detected."""

    cores: int | None
    available_memory_mb: int | None


def head_of_line(waiting: Sequence[Waiting]) -> Waiting | None:
    """The run that starts next: the oldest aged run, else class rank then arrival."""
    if not waiting:
        return None
    aged = [run for run in waiting if run.aged()]
    if aged:
        return min(aged, key=lambda run: run.ticket)
    return min(waiting, key=lambda run: (run.rank, run.ticket))


def concurrency(limits: CapacityLimits, machine: MachineCapacity, running: int) -> int:
    """How many runs may run at once: ceiling, cores and memory, never fewer than one.

    Memory already used by the ``running`` runs is no longer available, so the memory
    bound counts them plus the runs that still fit. An undetected fact gives one.
    """
    if machine.cores is None or machine.available_memory_mb is None:
        return 1
    by_cores = int(machine.cores // limits.cores_per_run)
    by_memory = running + machine.available_memory_mb // limits.memory_per_run_mb
    return max(1, min(limits.max_concurrent, by_cores, by_memory))


def may_start(
    candidate: Waiting,
    waiting: Sequence[Waiting],
    running_places: Sequence[int],
    places: int,
) -> bool:
    """Only the head of the line starts, and only into a free place.

    ``running_places`` holds, per running run, the number of runs it allows beside
    itself included; the lowest of them and of the candidate's own ``places`` decides,
    so one queue serves projects with different ceilings.
    """
    if candidate != head_of_line(waiting):
        return False
    return len(running_places) < min([places, *running_places])


_SHOWN_COMMAND = 160


@dataclass(frozen=True)
class Ahead:
    """A run another run waits behind: its process, its command and for how long."""

    ticket: int
    pid: int | None
    command: tuple[str, ...]
    running: bool
    age_seconds: float

    def process(self) -> str:
        return "process unknown" if self.pid is None else f"pid {self.pid}"

    def shown(self) -> str:
        """One line, whatever the command holds, short enough to read."""
        command = " ".join(shlex.join(self.command).split()) or "command unknown"
        if len(command) > _SHOWN_COMMAND:
            command = command[: _SHOWN_COMMAND - 3] + "..."
        state = "running for" if self.running else "waiting for"
        return (
            f"ticket {self.ticket}, {self.process()}, {state} "
            f"{self.age_seconds:.0f} s: {command}"
        )


def in_the_way(
    candidate: Waiting, waiting: Sequence[Waiting], running: Sequence[int]
) -> tuple[int, ...]:
    """The tickets a waiting run waits behind: the running runs, else the head.

    With nothing running, a run that is not the head of the line waits for the head
    to take its turn; the head itself waits behind nobody.
    """
    if running:
        return tuple(running)
    head = head_of_line(waiting)
    return () if head is None or head == candidate else (head.ticket,)


def gave_up(
    waited_seconds: float, limit_seconds: float, ahead: Sequence[Ahead]
) -> Refusal:
    """Why a run left the queue unrun, who was ahead of it, and how to free the queue."""
    named = "; ".join(run.shown() for run in ahead) or "no run that could be named"
    processes = ", ".join(run.process() for run in ahead if run.pid is not None)
    return Refusal(
        what=(
            f"the run waited {waited_seconds:.1f} s for a place, reached the limit "
            f"queue.max_wait_seconds of {limit_seconds:g} s and did not start; "
            f"ahead of it: {named}"
        ),
        why=(
            "no test ran, so this is neither a pass nor a failure; a run that never "
            "ends keeps its place, and the queue does not stop another run"
        ),
        how=(
            f"if a run ahead is stuck, stop its process ({processes or 'see above'}): "
            "its place is free as soon as that process is gone; if it is only long, "
            "declare a larger queue.max_wait_seconds; then run this command again"
        ),
    )
