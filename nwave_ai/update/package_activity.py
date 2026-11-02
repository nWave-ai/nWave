"""Coordinate a replaceable package across independently selected config homes."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from nwave_ai.platform.package_manager import (
    detect_running_interpreter_owner,
)
from nwave_ai.platform.session_registry import SessionActivityRegistry


class PackageActivityLease:
    """Shared while a controlled host runs; exclusive during package replacement.

    The lock is a sibling of the virtual environment, not inside the directory
    uv/pipx replace. It is deliberately independent of the selected config home.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None
        self.registry = SessionActivityRegistry(path.parent / f"{path.name}.state")

    @classmethod
    def for_interpreter(
        cls, interpreter: Path | None = None
    ) -> PackageActivityLease | None:
        executable = (interpreter or Path(sys.executable)).absolute()
        owner = detect_running_interpreter_owner(executable)
        if owner not in ("uv", "pipx", "pip") or executable.parent.name != "bin":
            return None
        environment = executable.parent.parent.resolve()
        # A global interpreter has no independently replaceable environment.
        if not (environment / "pyvenv.cfg").is_file():
            return None
        return cls(environment.parent / f".{environment.name}.nwave-activity.lock")

    def acquire(self, *, exclusive: bool, wait_seconds: float = 0.0) -> bool:
        if os.name != "posix":
            return False
        import fcntl

        if self._fd is not None:
            raise RuntimeError("package activity lease is already held")
        fd = os.open(
            self.path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600
        )
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        deadline = time.monotonic() + max(wait_seconds, 0.0)
        try:
            while True:
                try:
                    fcntl.flock(fd, operation | fcntl.LOCK_NB)
                    self._fd = fd
                    return True
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        return False
                    time.sleep(0.05)
        finally:
            if self._fd is None:
                os.close(fd)

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
