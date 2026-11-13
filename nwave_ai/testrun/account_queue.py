"""The one queue of test runs of an account: tickets under the nWave home.

One queue per nWave home, so per account: two accounts of one machine have two
queues and do not coordinate. Effects only. Every read and write of the queue
directory happens here, inside one exclusive lock; who is next, how many may run and
who is ahead of a waiting run are decided by ``queue_policy``.

Files of the queue directory::

    lock                the mutex of every operation
    events              the last number handed out; arrivals, starts and finishes
                        each take the next one, so their order needs no clock
    tickets/<n>.json    one waiting or running run: its class, the process that
                        holds it, its command, when it arrived and when it started
    tickets/<n>.alive   held locked by the process of that run for its whole life

A run whose process is gone cannot keep its ``.alive`` lock, whatever killed it: the
next process that looks at the queue removes its ticket. A run whose process is
alive keeps its ticket however long it runs: the queue never stops a run, it names
it to the runs that wait behind it. The locks are those of
``nwave_ai.platform.advisory_lock``, shared with the session registry.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from nwave_ai.platform import advisory_lock
from nwave_ai.platform.locations import NWaveLocations
from nwave_ai.platform.result import Failure
from nwave_ai.testrun.queue_policy import (
    Ahead,
    CapacityLimits,
    MachineCapacity,
    Waiting,
    concurrency,
    in_the_way,
    may_start,
)
from nwave_ai.testrun.refusal import Refusal


if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path


QUEUE_DIRECTORY = "test-queue"


@dataclass(frozen=True)
class Arrival:
    """What a run brings to the queue: its class, its order and its command."""

    run_class: str
    rank: int
    aging_seconds: float
    command: tuple[str, ...]


@dataclass(frozen=True)
class Ticket:
    """A run in the queue; ``places`` and ``started_at`` are ``None`` while it waits.

    ``pid`` is the process that holds the ticket. It is ``None`` only for a ticket
    written without one, which is then named as unknown, never guessed.
    """

    number: int
    run_class: str
    rank: int
    aging_seconds: float
    enqueued_at: float
    places: int | None = None
    pid: int | None = None
    command: tuple[str, ...] = ()
    started_at: float | None = None

    def as_document(self) -> dict[str, object]:
        return {
            "ticket": self.number,
            "class": self.run_class,
            "rank": self.rank,
            "aging_seconds": self.aging_seconds,
            "enqueued_at": self.enqueued_at,
            "places": self.places,
            "pid": self.pid,
            "command": list(self.command),
            "started_at": self.started_at,
        }

    def waiting(self, now: float) -> Waiting:
        """This run as the policy orders it: its class, its wait and its threshold."""
        waited = max(0.0, now - self.enqueued_at)
        return Waiting(self.number, self.rank, waited, self.aging_seconds)

    def ahead(self, now: float) -> Ahead:
        """This run as a waiting run sees it: running or waiting, and for how long."""
        running = self.places is not None
        since = self.started_at if running and self.started_at else self.enqueued_at
        return Ahead(
            self.number, self.pid, self.command, running, max(0.0, now - since)
        )


@dataclass(frozen=True)
class Held:
    """A ticket and the open file whose lock says this process is alive."""

    ticket: Ticket
    descriptor: int


@dataclass(frozen=True)
class Started:
    """The run may start: its event number and the places it was admitted under."""

    event: int
    places: int


@dataclass(frozen=True)
class Waits:
    """The run must wait: how many run, how many wait (itself included), who is ahead."""

    running: int
    waiting: int
    ahead: tuple[Ahead, ...] = ()


def queue_directory(
    environment: Mapping[str, str], account_home: Path
) -> Path | Refusal:
    """The queue of the nWave home: ``NWAVE_AGENTS_HOME`` when set, else the account's.

    The location owner is ``NWaveLocations``; a relative override is refused there and
    the refusal is passed on, never joined under an ambient directory.
    """
    located = NWaveLocations.resolve(
        home=account_home,
        repo_root=account_home,
        agents_home_override=environment.get("NWAVE_AGENTS_HOME"),
        claude_config_override=None,
        codex_config_override=None,
    )
    if isinstance(located, Failure):
        return Refusal(
            what=f"the home of the test queue cannot be decided: {located.error}",
            why="every run of the account must wait in the same queue directory",
            how="set NWAVE_AGENTS_HOME to an absolute directory, or unset it",
        )
    return located.unwrap().agents_home / ".nwave" / QUEUE_DIRECTORY


@contextlib.contextmanager
def _locked(directory: Path) -> Iterator[None]:
    """One critical section of the queue."""
    (directory / "tickets").mkdir(parents=True, exist_ok=True)
    descriptor = os.open(directory / "lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        advisory_lock.lock(descriptor)
        yield
    finally:
        advisory_lock.unlock(descriptor)
        os.close(descriptor)


def _write_atomically(path: Path, text: str) -> None:
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _next_event(directory: Path) -> int:
    """The next event number; the caller holds the queue lock."""
    counter = directory / "events"
    try:
        last = int(counter.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        last = 0
    _write_atomically(counter, str(last + 1))
    return last + 1


def _ticket_paths(directory: Path, number: int) -> tuple[Path, Path]:
    tickets = directory / "tickets"
    return tickets / f"{number}.json", tickets / f"{number}.alive"


def _process_is_gone(alive: Path) -> bool:
    """A ticket's process is gone when nobody holds its ``.alive`` lock."""
    try:
        descriptor = os.open(alive, os.O_RDWR)
    except OSError:
        return True
    try:
        free = advisory_lock.try_lock(descriptor)
        if free:
            advisory_lock.unlock(descriptor)
        return free
    finally:
        os.close(descriptor)


def _read_ticket(path: Path) -> Ticket | None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        pid, started_at = document.get("pid"), document.get("started_at")
        return Ticket(
            number=int(document["ticket"]),
            run_class=str(document["class"]),
            rank=int(document["rank"]),
            aging_seconds=float(document["aging_seconds"]),
            enqueued_at=float(document["enqueued_at"]),
            places=None if document["places"] is None else int(document["places"]),
            pid=None if pid is None else int(pid),
            command=tuple(str(word) for word in document.get("command", ())),
            started_at=None if started_at is None else float(started_at),
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def live_tickets(directory: Path) -> tuple[Ticket, ...]:
    """The tickets whose process is alive; the caller holds the queue lock.

    A ticket whose process is gone is removed here: it holds no place and no turn.
    """
    alive: list[Ticket] = []
    for record in sorted((directory / "tickets").glob("*.json")):
        lock_file = record.with_suffix(".alive")
        ticket = _read_ticket(record)
        if ticket is None or _process_is_gone(lock_file):
            record.unlink(missing_ok=True)
            lock_file.unlink(missing_ok=True)
            continue
        alive.append(ticket)
    return tuple(alive)


def enqueue(directory: Path, arrival: Arrival) -> Held:
    """Join the queue: take the next number and hold the lock that says "alive".

    The ticket names this process and its command, so that a run waiting behind it
    can say who holds the queue. The arrival time is read inside the lock, as
    ``session_registry`` stamps its records: the wait of a run never includes the
    wait for the lock itself.
    """
    with _locked(directory):
        number = _next_event(directory)
        record, lock_file = _ticket_paths(directory, number)
        descriptor = os.open(lock_file, os.O_RDWR | os.O_CREAT, 0o600)
        advisory_lock.lock(descriptor)
        ticket = Ticket(
            number,
            arrival.run_class,
            arrival.rank,
            arrival.aging_seconds,
            time.time(),
            pid=os.getpid(),
            command=arrival.command,
        )
        _write_atomically(record, json.dumps(ticket.as_document()))
    return Held(ticket, descriptor)


def try_start(
    directory: Path, held: Held, limits: CapacityLimits, machine: MachineCapacity
) -> Started | Waits:
    """Start if this run is the head of the line and a place is free, else wait."""
    with _locked(directory):
        now = time.time()
        tickets = live_tickets(directory)
        running = [ticket for ticket in tickets if ticket.places is not None]
        waiting = [ticket.waiting(now) for ticket in tickets if ticket.places is None]
        mine = next(run for run in waiting if run.ticket == held.ticket.number)
        places = concurrency(limits, machine, len(running))
        running_places = [ticket.places for ticket in running if ticket.places]
        if not may_start(mine, waiting, running_places, places):
            blocking = in_the_way(mine, waiting, [run.number for run in running])
            return Waits(
                running=len(running),
                waiting=len(waiting),
                ahead=tuple(
                    ticket.ahead(now) for ticket in tickets if ticket.number in blocking
                ),
            )
        event = _next_event(directory)
        record, _lock_file = _ticket_paths(directory, held.ticket.number)
        started = replace(held.ticket, places=places, started_at=now)
        _write_atomically(record, json.dumps(started.as_document()))
        return Started(event, places)


def finish(directory: Path, held: Held) -> int:
    """Leave the queue, waiting or running; return the event number of leaving."""
    with _locked(directory):
        event = _next_event(directory)
        record, lock_file = _ticket_paths(directory, held.ticket.number)
        record.unlink(missing_ok=True)
        advisory_lock.unlock(held.descriptor)
        with contextlib.suppress(OSError):
            os.close(held.descriptor)
        lock_file.unlink(missing_ok=True)
    return event
