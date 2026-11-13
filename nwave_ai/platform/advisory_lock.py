"""Exclusive advisory locks on open files: the one idiom of every nWave lock.

Standard library only. ``fcntl.flock`` on POSIX, ``msvcrt.locking`` where ``fcntl``
is absent; the system releases either lock when its holder dies.
"""

from __future__ import annotations

import contextlib
import os
import time


_RETRY_SECONDS = 0.01


def try_lock(descriptor: int) -> bool:
    """Take the lock if it is free; say whether it was taken."""
    try:
        import fcntl
    except ImportError:  # pragma: no cover - Windows only
        import msvcrt

        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def lock(descriptor: int) -> None:
    """Wait for the lock and take it.

    A lock the system refuses to give raises ``OSError``: going on without it would
    look locked while it is not.
    """
    try:
        import fcntl
    except ImportError:  # pragma: no cover - Windows only
        while not try_lock(descriptor):
            time.sleep(_RETRY_SECONDS)
        return
    fcntl.flock(descriptor, fcntl.LOCK_EX)


def unlock(descriptor: int) -> None:
    """Give the lock back; a lock already gone is not an error."""
    try:
        import fcntl
    except ImportError:  # pragma: no cover - Windows only
        import msvcrt

        with contextlib.suppress(OSError):
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        return
    with contextlib.suppress(OSError):
        fcntl.flock(descriptor, fcntl.LOCK_UN)
