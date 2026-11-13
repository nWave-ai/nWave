"""Run one test command through the test queue of the account and say what happened.

The shell of the queue: it checks, waits its turn, starts the command, bounds it and
writes the receipt. The decisions are made elsewhere (``queue_policy`` for the turn,
``declaration`` for what the project declared); this module performs the effects in
order and returns every outcome as a value: completed, timed out, not started,
refused or indeterminate. It never raises for one of them.

The time limit bounds the command only. The wait in the queue is measured apart and
is never added to it. The wait has its own declared limit: a run that reaches it
leaves the queue unrun and names the runs ahead of it (indeterminate, never a pass).
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from nwave_ai.testrun import account_queue, capacity, orphan_guard
from nwave_ai.testrun.queue_policy import gave_up
from nwave_ai.testrun.refusal import Refusal


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

    from nwave_ai.testrun.declaration import Declaration, ToolResolution


# Set in the environment of a running command. A run that finds it is already inside
# a place of the queue: waiting again would be waiting for its own parent.
TICKET_VARIABLE = "NWAVE_TEST_QUEUE_TICKET"
RECEIPT_SCHEMA = 1

COMPLETED = "completed"
TIMED_OUT = "timed-out"
NOT_STARTED = "not-started"
REFUSED = "refused"
INDETERMINATE = "indeterminate"

_POLL_SECONDS = 0.05
_CHECK_SECONDS = 60.0
_LONG_IDENTITY = 200


@dataclass(frozen=True)
class RunRequest:
    """One command to run: where, in which class, how long, for which queue."""

    root: Path
    argv: tuple[str, ...]
    run_class: str | None
    time_limit_seconds: float | None
    declaration: Declaration
    queue: Path
    environment: Mapping[str, str]
    capture_output: bool = False


@dataclass(frozen=True)
class Events:
    """The queue's numbers for the arrival, the start and the end of a run."""

    enqueued: int
    started: int
    finished: int


@dataclass(frozen=True)
class Receipt:
    """What ran, on which candidate, how it ended and what it cost."""

    run_class: str
    root: str
    command: tuple[str, ...]
    outcome: str
    exit: int | None = None
    candidate: Mapping[str, object] | None = None
    wait_seconds: float = 0.0
    duration_seconds: float = 0.0
    time_limit_seconds: float | None = None
    peak_memory_kb: int | None = None
    peak_memory_note: str | None = None
    events: Events | None = None
    concurrency: int | None = None
    nested: bool = False
    ticket: int | None = None
    refusal: Refusal | None = None

    def as_document(self) -> dict[str, object]:
        return {
            "schema": RECEIPT_SCHEMA,
            "ticket": self.ticket,
            "class": self.run_class,
            "root": self.root,
            "command": list(self.command),
            "candidate": dict(self.candidate or {}),
            "outcome": self.outcome,
            "exit": self.exit,
            "wait_seconds": round(self.wait_seconds, 3),
            "duration_seconds": round(self.duration_seconds, 3),
            "time_limit_seconds": self.time_limit_seconds,
            "peak_memory_kb": self.peak_memory_kb,
            "peak_memory_note": self.peak_memory_note,
            "events": None if self.events is None else dict(self.events.__dict__),
            "concurrency": self.concurrency,
            "nested": self.nested,
            "refusal": None if self.refusal is None else self.refusal.as_document(),
        }


@dataclass(frozen=True)
class Execution:
    """The receipt of a run and, when it was captured, what the command printed."""

    receipt: Receipt
    output: bytes | None = None


@dataclass(frozen=True)
class _Ended:
    outcome: str
    exit: int | None
    duration_seconds: float
    peak_memory_kb: int | None
    problem: Refusal | None = None
    output: bytes | None = None


def _shown(argv: tuple[str, ...]) -> str:
    return shlex.join(argv)


def _observe(argv: tuple[str, ...], root: Path) -> tuple[str | None, str | None]:
    """Run a declared read-only command; give its output, or why there is none."""
    try:
        done = subprocess.run(
            list(argv),
            cwd=root,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=_CHECK_SECONDS,
            check=False,
        )
    except OSError as error:
        return None, f"it could not start ({error.strerror or error})"
    except subprocess.TimeoutExpired:
        return None, f"it did not end within {_CHECK_SECONDS:.0f} s"
    if done.returncode != 0:
        return None, f"it exited {done.returncode}"
    return done.stdout.decode("utf-8", errors="replace"), None


def resolution_refusal(root: Path, check: ToolResolution | None) -> Refusal | None:
    """Refuse when the tool under test resolves outside the tree, or cannot be seen."""
    if check is None:
        return None
    tree = root.resolve()
    command = _shown(check.argv)
    printed, problem = _observe(check.argv, root)
    paths = [line.strip() for line in (printed or "").splitlines() if line.strip()]
    if problem is None and not paths:
        problem = "it printed no path"
    if problem is not None:
        return Refusal(
            what=(
                "where the tool under test resolves could not be checked: "
                f"`{command}` in {tree}: {problem}"
            ),
            why=(
                "a check that cannot decide must not count as a pass: the run could "
                "test code that is not this tree's"
            ),
            how=(
                f"run `{command}` in {tree} and make it print the path the tool "
                "resolves to, or correct tool_resolution in the declaration"
            ),
        )
    outside = [
        path
        for path in paths
        if tree not in ((tree / path).resolve(), *(tree / path).resolve().parents)
    ]
    if not outside:
        return None
    return Refusal(
        what=(
            "the tool under test resolves outside the tree under test: "
            f"{', '.join(outside)} is not inside {tree}"
        ),
        why=(
            "the run would test code that is not this tree's; the known case is an "
            "editable installation that points at another checkout"
        ),
        how=(
            f"{check.repair or 'install the tool from this tree'}; then check with "
            f"`{command}` in {tree}"
        ),
    )


def read_candidate(
    root: Path,
    readers: Mapping[str, tuple[str, ...]],
    notify: Callable[[str], None],
) -> dict[str, object]:
    """The identity of the candidate as the project declares how to read it.

    A reader that fails is said out loud and recorded as unavailable; the run goes on.
    """
    candidate: dict[str, object] = {}
    for name, argv in readers.items():
        printed, problem = _observe(argv, root)
        if problem is not None:
            reason = f"`{_shown(argv)}`: {problem}"
            notify(f"NOTE: candidate identity '{name}' is unavailable: {reason}")
            candidate[name] = {"unavailable": reason}
            continue
        value = (printed or "").strip()
        if len(value) > _LONG_IDENTITY or "\n" in value:
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
            value = f"sha256:{digest} ({len(value.splitlines())} lines)"
        candidate[name] = value
    return candidate


def _stop(process: subprocess.Popen) -> None:
    """End the command and everything it started."""
    if orphan_guard.AVAILABLE:
        orphan_guard.stop_group(process.pid)
        return
    with contextlib.suppress(OSError):
        process.kill()


def _peak_kb(max_rss: int) -> int:
    # The kernel reports kilobytes, except Darwin, which reports bytes.
    return max_rss // 1024 if sys.platform == "darwin" else max_rss


def _await(
    process: subprocess.Popen, limit: float | None
) -> tuple[int | None, int | None]:
    """Wait for the command up to its limit; give its exit and its peak memory.

    The exit is ``None`` when the limit ended the command. Where the platform gives
    per-child resource usage (``os.wait4``) the peak is the command's own.
    """
    if not hasattr(os, "wait4"):
        try:
            return process.wait(timeout=limit), None
        except subprocess.TimeoutExpired:
            _stop(process)
            process.wait()
            return None, None
    reaped: list[tuple[int, object]] = []

    def reap() -> None:
        _pid, status, usage = os.wait4(process.pid, 0)
        reaped.append((status, usage))

    waiter = threading.Thread(target=reap, daemon=True)
    waiter.start()
    waiter.join(limit)
    in_time = not waiter.is_alive()
    if not in_time:
        _stop(process)
        waiter.join()
    status, usage = reaped[0]
    # wait4 has reaped the child: tell Popen, so that it never waits for it again.
    process.returncode = os.waitstatus_to_exitcode(status)
    return (process.returncode if in_time else None), _peak_kb(int(usage.ru_maxrss))


# What a run says, whatever the cause, when nothing would stop its command.
_UNWATCHED = "if the process of this run is killed, its command keeps running"


def _not_started(program: str, reason: str) -> _Ended:
    problem = Refusal(
        what=f"could not start {program}: {reason}",
        why="a command that never started ran no test",
        how="check that the program of the command exists and can be run",
    )
    return _Ended(NOT_STARTED, None, 0.0, None, problem)


def _supervised(
    request: RunRequest, streams: Mapping[str, object], notify: Callable[[str], None]
) -> _Ended | None:
    """Run the command under its supervisor; ``None``, said out loud, without one."""
    if not orphan_guard.AVAILABLE:
        notify(f"NOTE: this platform has no process groups: {_UNWATCHED}")
        return None
    try:
        result = orphan_guard.run(request.argv, request.time_limit_seconds, **streams)
    except OSError as error:
        reason = error.strerror or error
        notify(
            f"NOTE: the supervisor of the command could not start ({reason}): "
            f"{_UNWATCHED}"
        )
        return None
    if isinstance(result, orphan_guard.NotStarted):
        return _not_started(request.argv[0], result.reason)
    if isinstance(result, orphan_guard.Lost):
        problem = Refusal(
            what="the supervisor of the command ended without saying how the "
            "command ended; the command was stopped",
            why="the exit of the command is unknown, so this is neither a pass "
            "nor a failure",
            how="run the command again",
        )
        return _Ended(INDETERMINATE, None, 0.0, None, problem)
    if result.stopped:
        return _Ended(TIMED_OUT, None, result.seconds, _peak_kb(result.max_rss))
    exit_code = os.waitstatus_to_exitcode(result.status)
    return _Ended(COMPLETED, exit_code, result.seconds, _peak_kb(result.max_rss))


def _direct(request: RunRequest, streams: Mapping[str, object]) -> _Ended:
    """Run the command as a child of this process: nothing outlives this process
    to stop it."""
    began = time.monotonic()
    try:
        process = subprocess.Popen(
            list(request.argv), start_new_session=os.name == "posix", **streams
        )
    except OSError as error:
        return _not_started(request.argv[0], error.strerror or str(error))
    try:
        exit_code, peak = _await(process, request.time_limit_seconds)
    finally:
        if process.returncode is None:
            _stop(process)
    outcome = TIMED_OUT if exit_code is None else COMPLETED
    return _Ended(outcome, exit_code, time.monotonic() - began, peak)


def _run_command(
    request: RunRequest, ticket: str, notify: Callable[[str], None]
) -> _Ended:
    with contextlib.ExitStack() as stack:
        sink = (
            stack.enter_context(tempfile.TemporaryFile())
            if request.capture_output
            else None
        )
        streams = {
            "cwd": request.root,
            "env": {**request.environment, TICKET_VARIABLE: ticket},
            "stdin": subprocess.DEVNULL if request.capture_output else None,
            "stdout": sink,
            "stderr": subprocess.STDOUT if request.capture_output else None,
        }
        ended = _supervised(request, streams, notify) or _direct(request, streams)
        if sink is None:
            return ended
        sink.seek(0)
        return replace(ended, output=sink.read())


def _wait_for_a_place(
    request: RunRequest,
    held: account_queue.Held,
    arrived: float,
    notify: Callable[[str], None],
) -> account_queue.Started | account_queue.Waits:
    """Ask for a place until one is given or the declared wait limit is reached."""
    queue = request.declaration.queue
    told = False
    while True:
        machine, notes = capacity.read_machine()
        attempt = account_queue.try_start(request.queue, held, queue.limits, machine)
        if isinstance(attempt, account_queue.Started):
            return attempt
        if time.monotonic() - arrived >= queue.max_wait_seconds:
            return attempt
        if not told:
            told = True
            if queue.limits.max_concurrent > 1:
                for note in notes:
                    notify(note)
            notify(
                f"waiting: ticket {held.ticket.number}, class "
                f"{held.ticket.run_class}, {attempt.running} running, "
                f"{attempt.waiting} waiting; gives up after "
                f"{queue.max_wait_seconds:g} s"
            )
        time.sleep(_POLL_SECONDS)


def _memory_note(ended: _Ended) -> str | None:
    if ended.peak_memory_kb is not None or ended.problem is not None:
        return None
    return "this platform gives no resource usage of a finished child process"


def execute(request: RunRequest, notify: Callable[[str], None]) -> Execution:
    """Check, wait for a place, run the command within its limit, give the receipt."""
    queue = request.declaration.queue
    run_class = request.run_class or queue.last_class()
    rank = queue.rank(run_class)
    base = Receipt(
        run_class=run_class,
        root=str(request.root.resolve()),
        command=request.argv,
        outcome=REFUSED,
        time_limit_seconds=request.time_limit_seconds,
    )
    if rank is None:
        refusal = Refusal(
            what=f"the class '{run_class}' is not declared",
            why="the queue orders runs by the classes the project declares",
            how=f"use one of the declared classes: {', '.join(queue.classes)}",
        )
        return Execution(replace(base, refusal=refusal))
    refusal = resolution_refusal(request.root, request.declaration.tool_resolution)
    if refusal is not None:
        return Execution(replace(base, refusal=refusal))

    inherited = request.environment.get(TICKET_VARIABLE)
    if inherited is not None:
        candidate = read_candidate(request.root, request.declaration.candidate, notify)
        ended = _run_command(request, inherited, notify)
        ticket = int(inherited) if inherited.isdigit() else None
        return _completed(replace(base, nested=True, ticket=ticket), ended, candidate)
    arrival = account_queue.Arrival(run_class, rank, queue.aging_seconds, request.argv)
    return _through_the_queue(request, base, arrival, notify)


def _unusable_queue(queue: Path, error: OSError) -> Refusal:
    return Refusal(
        what=f"the test queue {queue} cannot be used: {error}",
        why="a run that cannot join the queue would be neither ordered nor "
        "counted among the runs of the account",
        how=f"make {queue} a directory this account can write, on a "
        "file system with file locks, or point NWAVE_AGENTS_HOME at one",
    )


def _through_the_queue(
    request: RunRequest,
    base: Receipt,
    arrival: account_queue.Arrival,
    notify: Callable[[str], None],
) -> Execution:
    """Join the queue, run in turn or give up at the wait limit, always leave it."""
    arrived = time.monotonic()
    try:
        held = account_queue.enqueue(request.queue, arrival)
    except OSError as error:
        refusal = _unusable_queue(request.queue, error)
        return Execution(replace(base, refusal=refusal))
    turn = None
    try:
        attempt = _wait_for_a_place(request, held, arrived, notify)
        waited = time.monotonic() - arrived
        if isinstance(attempt, account_queue.Started):
            turn = (
                read_candidate(request.root, request.declaration.candidate, notify),
                _run_command(request, str(held.ticket.number), notify),
            )
    finally:
        finished = account_queue.finish(request.queue, held)
    queued = replace(base, ticket=held.ticket.number, wait_seconds=waited)
    if isinstance(attempt, account_queue.Waits):
        limit = request.declaration.queue.max_wait_seconds
        refusal = gave_up(waited, limit, attempt.ahead)
        return Execution(replace(queued, outcome=INDETERMINATE, refusal=refusal))
    candidate, ended = turn
    admitted = replace(
        queued,
        events=Events(held.ticket.number, attempt.event, finished),
        concurrency=attempt.places,
    )
    return _completed(admitted, ended, candidate)


def _completed(
    base: Receipt, ended: _Ended, candidate: Mapping[str, object]
) -> Execution:
    receipt = replace(
        base,
        outcome=ended.outcome,
        exit=ended.exit,
        candidate=candidate,
        duration_seconds=ended.duration_seconds,
        peak_memory_kb=ended.peak_memory_kb,
        peak_memory_note=_memory_note(ended),
        refusal=ended.problem,
    )
    return Execution(receipt, ended.output)
