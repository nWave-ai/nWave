"""Starts the command of a run and stops it when the run's own process is gone.

A run that is killed outright cannot stop the command it started. So the run does
not start the command itself: it starts this supervisor, in a session of its own and
holding a pipe to it, and the supervisor starts the command in a process group of
its own. From before the command exists, one living process knows its group. When
the pipe closes (the run reached the command's time limit, was asked to end, or
disappeared) the supervisor stops the group. On a second pipe it reports that the
command started, then how it ended, or that it could not be started.

What this does not cover: a command that leaves its process group is not stopped,
and when the run and its supervisor are both killed nothing stops the command.
Process groups and per-child resource usage are needed (POSIX); elsewhere
``AVAILABLE`` is false and the caller runs the command itself and says so out loud.

Run as a program (``orphan_guard.py CONTROL REPORT COMMAND ...``), this file is the
supervisor; it needs nothing but the standard library, so it starts whatever the
environment of the run holds.
"""

from __future__ import annotations

import contextlib
import json
import os
import select
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping


AVAILABLE = os.name == "posix" and hasattr(os, "wait4")
_TIMED_OUT = object()


@dataclass(frozen=True)
class Ran:
    """The command started and ended; ``stopped`` when the supervisor ended it."""

    status: int
    max_rss: int
    seconds: float
    stopped: bool


@dataclass(frozen=True)
class NotStarted:
    """The command could not be started, and why."""

    reason: str


@dataclass(frozen=True)
class Lost:
    """The supervisor ended without a report; the command, if any, was stopped."""


def stop_group(group: int) -> None:
    """End every process of a process group; a group that is gone is not an error.

    Only POSIX has process groups; elsewhere the supervisor (POSIX-only) stops nothing."""
    if os.name == "posix":
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(group, signal.SIGKILL)


def outcome_of(documents: list[Mapping[str, object]]) -> Ran | NotStarted | Lost:
    """Pure: what the reports of a supervisor, in order, say about the command."""
    for document in documents:
        if "error" in document:
            return NotStarted(str(document["error"]))
        if "status" in document:
            return Ran(
                int(document["status"]),
                int(document["max_rss"]),
                float(document["seconds"]),
                bool(document["stopped"]),
            )
    return Lost()


class _Reports:
    """The reports of one supervisor, read line by line with a time limit."""

    def __init__(self, descriptor: int) -> None:
        self._descriptor = descriptor
        self._pending = b""

    def next(self, timeout: float | None) -> object:
        """The next report, ``None`` at the end of the pipe, or ``_TIMED_OUT``."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while b"\n" not in self._pending:
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                return _TIMED_OUT
            readable, _, _ = select.select([self._descriptor], [], [], remaining)
            if not readable:
                return _TIMED_OUT
            chunk = os.read(self._descriptor, 4096)
            if not chunk:
                return None
            self._pending += chunk
        line, _, self._pending = self._pending.partition(b"\n")
        return json.loads(line)

    def close(self) -> None:
        os.close(self._descriptor)


class _Control:
    """This run's end of the pipe that keeps the command running; closed once."""

    def __init__(self, descriptor: int) -> None:
        self._descriptor: int | None = descriptor

    def release(self) -> None:
        """Close the pipe: the supervisor stops whatever of the command still runs."""
        if self._descriptor is not None:
            os.close(self._descriptor)
            self._descriptor = None


def _start(
    argv: tuple[str, ...], streams: Mapping[str, object]
) -> tuple[subprocess.Popen, _Control, _Reports]:
    """Start the supervisor of ``argv`` with the two pipes that tie it to this run."""
    if not sys.executable:
        raise OSError("the path of the running interpreter is unknown")
    control_read, control_write = os.pipe()
    report_read, report_write = os.pipe()
    try:
        supervisor = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-S",
                __file__,
                str(control_read),
                str(report_write),
                *argv,
            ],
            pass_fds=(control_read, report_write),
            start_new_session=True,
            **streams,
        )
    except OSError:
        os.close(control_write)
        os.close(report_read)
        raise
    finally:
        os.close(control_read)
        os.close(report_write)
    return supervisor, _Control(control_write), _Reports(report_read)


def run(
    argv: tuple[str, ...], limit: float | None, **streams: object
) -> Ran | NotStarted | Lost:
    """Run ``argv`` under a supervisor, for at most ``limit`` seconds once it started.

    ``streams`` are the working directory, the environment and the standard streams
    of the command. Raises ``OSError`` when the supervisor itself cannot start.
    """
    supervisor, control, reports = _start(argv, streams)
    seen: list[Mapping[str, object]] = []
    try:
        report = reports.next(None)
        while isinstance(report, dict):
            seen.append(report)
            report = reports.next(limit if "started" in report else None)
            if report is _TIMED_OUT:
                control.release()
                report = reports.next(None)
    finally:
        control.release()
        reports.close()
        supervisor.wait()
    outcome = outcome_of(seen)
    if isinstance(outcome, Lost):
        for document in seen:
            if "started" in document:
                stop_group(int(document["started"]))
    return outcome


def _supervise(control: int, report: int, argv: list[str]) -> None:
    """The supervisor: start the command, stop its group when the pipe closes."""

    def tell(document: Mapping[str, object]) -> None:
        with contextlib.suppress(OSError):
            os.write(report, (json.dumps(document) + "\n").encode())

    began = time.monotonic()
    try:
        command = subprocess.Popen(argv, start_new_session=True)
    except OSError as error:
        tell({"error": error.strerror or str(error)})
        return
    tell({"started": command.pid})
    reaped: dict[str, int] = {}
    woken_read, woken_write = os.pipe()

    def reap() -> None:
        _pid, status, usage = os.wait4(command.pid, 0)
        reaped.update(status=status, max_rss=int(usage.ru_maxrss))
        os.close(woken_write)

    reaper = threading.Thread(target=reap, daemon=True)
    reaper.start()
    readable, _, _ = select.select([control, woken_read], [], [])
    stopped = woken_read not in readable
    if stopped:
        stop_group(command.pid)
    reaper.join()
    tell({**reaped, "seconds": time.monotonic() - began, "stopped": stopped})


def main(arguments: list[str]) -> int:
    """``CONTROL REPORT COMMAND ...``: the two pipe descriptors, then the command."""
    for ignored in (signal.SIGINT, signal.SIGTERM):
        signal.signal(ignored, signal.SIG_IGN)
    if os.name != "nt":
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
    _supervise(int(arguments[0]), int(arguments[1]), arguments[2:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
