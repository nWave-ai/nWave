"""Exclusive, non-blocking lock for one nWave install destination.

Two concurrent installs into the same destination produce TORN state: a
half-written runtime, a roster that briefly disappears, private agents
rewritten by the other invocation's asset set. That happened twice on
2026-08-21/22 (11:23 and 11:25, an ``install --dev`` starting while another
install was mid-flight; 51 agents written and then swept).

Prose saying "one install at a time" cannot be enforced. This module makes
the concurrent state UNREPRESENTABLE (GDP-0): the second invocation cannot
reach a write, because it cannot take the lock, and it says so LOUD and
immediately rather than waiting (GDP-6 -- never a silent wrong, never an
unbounded wait).

Scope of the lock is the install ROOT, not the machine -- see
:func:`scripts.shared.install_paths.install_lock_path`.

Portability: stdlib only, no shell-out. ``fcntl.flock`` on POSIX,
``msvcrt.locking`` on Windows; both are released by the OS when the holding
process dies, so a crashed or SIGKILLed install leaves no stale lock to
clear by hand.
"""

from __future__ import annotations

import json
import os
import sys
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING

from scripts.shared.install_paths import install_lock_path


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


#: Dedicated exit code for "another install holds the lock". Distinct from the
#: installer's 1 (failed) and 2 (no target host) so a wrapper, a CI step or a
#: lane harness can tell "retry later" apart from "this install is broken".
#: 75 is the conventional EX_TEMPFAIL.
EXIT_INSTALL_LOCK_HELD: int = 75

#: Machine-readable error code, in the vocabulary of ``error_codes.py``.
INSTALL_LOCK_HELD: str = "INSTALL_LOCK_HELD"

_UNKNOWN_HOLDER = "unknown (the other install had not yet written its record)"


class InstallLockHeld(Exception):
    """Raised when another live install already owns this destination.

    Carries the fully formed WHAT / WHY / HOW refusal so every caller emits
    the same operator-facing text; ``str(exc)`` IS the message to print.
    """

    def __init__(self, lock_file: Path, holder: dict[str, object] | None) -> None:
        self.lock_file = lock_file
        self.holder = holder or {}
        super().__init__(_refusal_message(lock_file, self.holder))


def _describe_holder(holder: dict[str, object]) -> str:
    pid = holder.get("pid")
    started_at = holder.get("started_at")
    if pid is None and started_at is None:
        return _UNKNOWN_HOLDER
    targets = holder.get("target_platforms") or "unknown target"
    return f"PID {pid}, started {started_at}, target {targets}"


def _refusal_message(lock_file: Path, holder: dict[str, object]) -> str:
    """WHAT / WHY / HOW, in the shape every nWave refusal owes the operator."""
    return (
        "\n"
        "  X REFUSED: another nWave install is already running.\n"
        "\n"
        f"  WHAT: the install lock {lock_file} is held by another process --\n"
        f"        {_describe_holder(holder)}.\n"
        "        This invocation wrote 0 files.\n"
        "  WHY : two concurrent installs into the same destination produce torn\n"
        "        state -- a half-written runtime, a roster that vanishes, private\n"
        "        agents rewritten by the other run's asset set (incidents\n"
        "        2026-08-21 and 2026-08-22). The lock makes that unrepresentable.\n"
        "  HOW : wait for the running install to finish, then re-run the same\n"
        "        command. If you are verifying an install from a lane, isolate the\n"
        "        destination instead of waiting -- the lock is per-destination:\n"
        "          HOME=<tmp> NWAVE_AGENTS_HOME=<tmp> CLAUDE_CONFIG_DIR=<tmp>/.claude \\\n"
        "            python scripts/install/install_nwave.py --platform claude-code\n"
        "        A lock left by a killed process needs no cleanup: the OS releases\n"
        "        it when the process dies.\n"
    )


def _try_acquire(fd: int) -> bool:
    """Take an exclusive, NON-blocking lock on ``fd``. False when held.

    Never blocks: an install that waits silently for an unbounded time is the
    same operator-visible failure as no lock at all.
    """
    try:
        import fcntl
    except ImportError:  # pragma: no cover - exercised on Windows only
        import msvcrt

        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _release(fd: int) -> None:
    try:
        import fcntl
    except ImportError:  # pragma: no cover - exercised on Windows only
        import msvcrt

        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        return

    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


def _read_holder(lock_file: Path) -> dict[str, object] | None:
    """Best-effort holder record. Never raises -- absence must not mask the refusal."""
    try:
        raw = lock_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _write_holder(fd: int, target_platforms: str) -> None:
    record = json.dumps(
        {
            "pid": os.getpid(),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "target_platforms": target_platforms,
            "argv": " ".join(sys.argv[1:]),
        }
    )
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, record.encode("utf-8"))
    os.fsync(fd)


@contextmanager
def install_lock(
    target_platforms: str = "unknown",
    home: Path | None = None,
) -> Iterator[Path]:
    """Hold the exclusive install lock for one destination for the block's life.

    Args:
        target_platforms: what this invocation installs, recorded in the lock so
            a contender can name the holder rather than guess.
        home: install root override. Default: the destination resolved from
            ``NWAVE_AGENTS_HOME`` / ``HOME``.

    Yields:
        The lock file path.

    Raises:
        InstallLockHeld: another live install owns this destination. Raised
            BEFORE the block runs, so the caller has written nothing.

    Release is guaranteed by ``finally`` -- an exception mid-install, a
    ``KeyboardInterrupt``, or a ``SystemExit`` all unlock on the way out, and
    the OS unlocks anyway if the process is killed outright. The lock FILE is
    deliberately not deleted on release: unlinking it would let a contender
    that already opened it lock a now-orphaned inode.
    """
    lock_file = install_lock_path(home)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    # O_CREAT without O_TRUNC: the contender must not perturb a byte of the
    # holder's record before it knows whether it owns the lock.
    fd = os.open(lock_file, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if not _try_acquire(fd):
            raise InstallLockHeld(lock_file, _read_holder(lock_file))
        _write_holder(fd, target_platforms)
        yield lock_file
    finally:
        _release(fd)
        os.close(fd)
