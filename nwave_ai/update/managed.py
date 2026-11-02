"""Start a host only after admission, and retain activity until proven teardown."""

from __future__ import annotations

import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nwave_ai.platform.session_registry import (
    MANAGED_SESSION_ENV,
    SessionActivityRegistry,
    session_key,
)
from nwave_ai.platform.update_timing import UPDATE_TIMING
from nwave_ai.update.package_activity import PackageActivityLease
from nwave_ai.update.permissions import controlled_launch_permission, update_permissions


if TYPE_CHECKING:
    from collections.abc import Callable


HOST_COMMANDS = {
    "claude-code": "claude",
    "codex": "codex",
    "opencode": "opencode",
    "copilot": "copilot",
}


@dataclass(frozen=True)
class WrapperRegistration:
    key: str
    owner_token: str
    host: str

    def belongs_to(self, registry: SessionActivityRegistry) -> bool:
        identity = f"managed:{self.host}"
        return secrets.compare_digest(
            self.key, session_key(identity, self.owner_token)
        ) and any(
            record.key == self.key and record.host == identity and not record.problem
            for record in registry.sessions()
        )


def _group_exists(group: int) -> bool:
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False


def _run_child(executable: str, arguments: list[str], key: str) -> tuple[int, bool]:
    environment = dict(os.environ, **{MANAGED_SESSION_ENV: key})
    try:
        process = subprocess.Popen(
            [executable, *arguments], env=environment, start_new_session=True
        )
    except OSError as exc:
        print(f"Host could not start: {exc}", file=sys.stderr)
        return 127, True
    previous: dict[int, object] = {}
    interrupted_at: float | None = None
    killed_at: float | None = None

    def forward(signum: int, _frame: object) -> None:
        nonlocal interrupted_at
        interrupted_at = interrupted_at or time.monotonic()
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            pass

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, forward)
        while True:
            try:
                code = process.wait(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                now = time.monotonic()
                if interrupted_at is not None and now - interrupted_at >= 5.0:
                    if killed_at is None:
                        os.killpg(process.pid, signal.SIGKILL)
                        killed_at = now
                    elif now - killed_at >= 3.0:
                        return 1, False
        deadline = time.monotonic() + 1.0
        while _group_exists(process.pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        return (code if code >= 0 else 128 - code), not _group_exists(process.pid)
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def run_host(host: str, arguments: list[str], *, update: Callable[..., int]) -> int:
    """Public controlled-launch entry; no shell or process exists before admission."""
    if host not in HOST_COMMANDS or os.name != "posix":
        print(
            "Controlled launch requires POSIX and one of: " + ", ".join(HOST_COMMANDS),
            file=sys.stderr,
        )
        return 1
    executable = shutil.which(HOST_COMMANDS[host])
    if executable is None:
        print(
            f"Host command {HOST_COMMANDS[host]!r} is not installed or not on PATH.",
            file=sys.stderr,
        )
        return 1
    registry = SessionActivityRegistry.selected()
    if registry is None:
        print(
            "Cannot establish the selected session registry; host not started.",
            file=sys.stderr,
        )
        return 1
    package = PackageActivityLease.for_interpreter()
    registries = [registry] + ([package.registry] if package is not None else [])
    token = secrets.token_hex(32)
    registration = WrapperRegistration(
        session_key(f"managed:{host}", token), token, host
    )
    child_started = False
    safe_to_clear = True
    try:
        # Publish activity in the shared package scope before releasing admission.
        if package is not None and not package.acquire(
            exclusive=False, wait_seconds=UPDATE_TIMING.admission_seconds
        ):
            print(
                "Package replacement is still active; host not started. Retry after recovery.",
                file=sys.stderr,
            )
            return 1
        try:
            for selected in registries:
                with selected.exclusive(UPDATE_TIMING.admission_seconds) as acquired:
                    if not acquired or selected.update_in_progress() is not None:
                        print(
                            "Update state is busy or incomplete; host not started. Run nwave-ai update --check for recovery.",
                            file=sys.stderr,
                        )
                        return 1
                    selected.register(
                        host=f"managed:{host}",
                        session_id=token,
                        cwd=str(Path.cwd()),
                        source="managed-startup",
                    )
        finally:
            if package is not None:
                package.close()
        check, install = update_permissions()
        if check:
            from nwave_ai.update.activity import ReplacementLease

            install_requested = install and controlled_launch_permission()
            startup_lease = ReplacementLease(
                registration, check_only=not install_requested
            )
            try:
                refusal = (
                    startup_lease.before_replacement(host)
                    if install_requested
                    else startup_lease.before_check()
                )
                if refusal is not None:
                    print(
                        f"Automatic update skipped: {refusal.cause}. {refusal.recovery}",
                        file=sys.stderr,
                    )
                else:
                    arguments_for_update = (
                        ["--yes", "--root", str(Path.cwd())]
                        if install_requested
                        else ["--check"]
                    )
                    update(
                        arguments_for_update,
                        wrapper_registration=registration,
                        replacement_lease=startup_lease,
                    )
            finally:
                startup_lease.close()
        # A failed replacement must not be hidden by starting the host afterwards.
        if any(selected.update_in_progress() is not None for selected in registries):
            print(
                "Update is incomplete; host not started. Follow the reported recovery command.",
                file=sys.stderr,
            )
            return 1
        if package is not None and not package.acquire(
            exclusive=False, wait_seconds=UPDATE_TIMING.admission_seconds
        ):
            print("Package admission timed out; host not started.", file=sys.stderr)
            return 1
        # Recheck after acquiring the lifetime lease; another update may have run.
        if any(selected.update_in_progress() is not None for selected in registries):
            print("Package recovery is required; host not started.", file=sys.stderr)
            return 1
        child_started = True
        safe_to_clear = False
        code, safe_to_clear = _run_child(executable, arguments, registration.key)
        return code
    except (OSError, ValueError) as exc:
        print(
            f"Controlled launch stopped: {exc}. Session {registration.key} may need confirmed recovery.",
            file=sys.stderr,
        )
        return 1
    finally:
        if safe_to_clear:
            for selected in registries:
                try:
                    with selected.exclusive(10.0) as acquired:
                        if acquired and registration.belongs_to(selected):
                            selected.deregister(registration.key)
                except OSError:
                    pass  # Retaining a stale record is safer than guessing closure.
        elif child_started:
            print(
                f"Session {registration.key} teardown is uncertain; its record remains. Close remaining work before `nwave-ai update sessions close {registration.key} --confirm-closed`.",
                file=sys.stderr,
            )
        if package is not None:
            package.close()
