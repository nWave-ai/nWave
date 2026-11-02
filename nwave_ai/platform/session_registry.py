"""Global host-session activity registry and exclusive update lock.

One installation root (the selected agents home) is shared by every repository
and worktree that uses it. An automatic update replaces that shared package and
host framework, so local repository cleanliness cannot prove that no wave is
running elsewhere. This registry records every host session announced by the
installed ``SessionStart`` hook and removes it on ``SessionEnd``.

IDLE IS POSITIVE EVIDENCE. ``evaluate_idle`` answers ``Idle`` only when:

* the one-time operator acknowledgement that sessions older than the registry
  are closed is present and complete;
* every registry entry parses as a known session record; and
* no registered session other than the caller's own remains.

Anything unknown, malformed or incomplete answers ``NotIdle``. Stale entries
are never cleared by guessing from a PID or modification time; the operator
closes them explicitly (``nwave-ai update sessions close KEY
--confirm-closed``).

SERIALIZATION. One exclusive lock file serializes an update's idle decision and
its whole mutation with every registration. The installer's own install lock
is not reused: the update runs the installer as a child process that takes the
install lock itself, and a second open of the same lock file would refuse it.

Portability: stdlib only. ``fcntl.flock`` on POSIX, ``msvcrt.locking`` on
Windows; the OS releases either lock when its holder dies.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator


SCHEMA_VERSION = 1
LEGACY_CONFIRMATION = "old-unregistered-sessions-closed"
MANAGED_SESSION_ENV = "NWAVE_MANAGED_SESSION_KEY"
_KEY_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_ENTRY_PATTERN = re.compile(r"^([0-9a-f]{32})\.json$")

#: Residual risk stated wherever the acknowledgement is requested or recorded.
ATTESTATION_RISK = (
    "unregistered sessions, disabled hooks and detached work are not observable; "
    "closing older work rests on your confirmation, and automatic installation "
    "requires the separate commitment to use controlled launch for future sessions"
)


@dataclass(frozen=True)
class Idle:
    """Positive evidence that no other host session holds the installation."""


@dataclass(frozen=True)
class NotIdle:
    """Idle could not be established; ``reason`` and ``recovery`` explain why."""

    reason: str
    recovery: str


@dataclass(frozen=True)
class SessionRecord:
    """One registry entry as read from disk; ``problem`` marks a malformed one."""

    key: str
    host: str = ""
    cwd: str = ""
    registered_at: str = ""
    problem: str = ""


def session_key(host: str, session_id: str) -> str:
    """Return the stable registry key for one host session identity."""
    return hashlib.sha256(f"{host}\0{session_id}".encode()).hexdigest()[:32]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _try_lock(fd: int) -> bool:
    try:
        import fcntl
    except ImportError:  # pragma: no cover - Windows only
        import msvcrt

        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(fd: int) -> None:
    try:
        import fcntl
    except ImportError:  # pragma: no cover - Windows only
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


class SessionActivityRegistry:
    """File registry of live host sessions for one selected agents home."""

    def __init__(self, agents_home: Path) -> None:
        self._root = agents_home / ".nwave" / "activity"

    @classmethod
    def selected(cls) -> SessionActivityRegistry | None:
        """Resolve the registry for the selected agents home, or None if invalid."""
        from nwave_ai.platform.locations import NWaveLocations
        from nwave_ai.platform.result import Failure

        located = NWaveLocations.resolve(
            home=Path.home(),
            repo_root=Path.cwd(),
            agents_home_override=os.environ.get("NWAVE_AGENTS_HOME"),
            claude_config_override=os.environ.get("CLAUDE_CONFIG_DIR"),
            codex_config_override=os.environ.get("CODEX_HOME"),
        )
        if isinstance(located, Failure):
            return None
        return cls(located.unwrap().agents_home)

    @property
    def root(self) -> Path:
        return self._root

    @property
    def _sessions(self) -> Path:
        return self._root / "sessions"

    @property
    def _acknowledgement(self) -> Path:
        return self._root / "legacy-sessions-closed.json"

    @property
    def lock_file(self) -> Path:
        return self._root / "update.lock"

    @property
    def in_progress_path(self) -> Path:
        return self._root / "update-in-progress.json"

    def update_in_progress(self) -> dict[str, object] | None:
        """Read interruption evidence without hiding malformed or unreadable state."""
        try:
            document = json.loads(self.in_progress_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return {"problem": f"the update marker cannot be read: {exc}"}
        if not isinstance(document, dict):
            return {"problem": "the update marker is not an object"}
        return document

    def record_update(self, document: dict[str, object]) -> None:
        """Durably replace interruption evidence while holding ``exclusive``."""
        self._root.mkdir(parents=True, exist_ok=True)
        temporary = self._root / f".update-{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(document, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.in_progress_path)
            self._sync_directory()
        finally:
            temporary.unlink(missing_ok=True)

    def clear_completed_update(self) -> None:
        """Remove evidence only after the recovery/application verified every stage."""
        self.in_progress_path.unlink()
        self._sync_directory()

    def _sync_directory(self) -> None:
        if os.name != "nt":
            fd = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    @contextmanager
    def exclusive(self, wait_seconds: float) -> Iterator[bool]:
        """Hold the update/registration lock; yield False if not acquired in time."""
        self._root.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_file, os.O_RDWR | os.O_CREAT, 0o644)
        acquired = False
        try:
            deadline = time.monotonic() + max(wait_seconds, 0.0)
            acquired = _try_lock(fd)
            while not acquired and time.monotonic() < deadline:
                time.sleep(0.05)
                acquired = _try_lock(fd)
            yield acquired
        finally:
            if acquired:
                _unlock(fd)
            os.close(fd)

    def _write_json(self, target: Path, document: dict[str, object]) -> None:
        staging = self._root / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = staging / f"{target.name}.{uuid.uuid4().hex}"
        temporary.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
        temporary.replace(target)

    def register(
        self, *, host: str, session_id: str | None, cwd: str, source: str
    ) -> str:
        """Write one session record; the caller decides whether to hold the lock."""
        identity = session_id or f"unidentified-{uuid.uuid4().hex}"
        key = session_key(host, identity)
        self._write_json(
            self._sessions / f"{key}.json",
            {
                "schema-version": SCHEMA_VERSION,
                "key": key,
                "host": host,
                "host_session_identified": bool(session_id),
                "cwd": cwd,
                "source": source,
                "registered_at": _now(),
            },
        )
        return key

    def deregister(self, key: str) -> bool:
        """Remove one session record; True if it existed."""
        if not _KEY_PATTERN.match(key):
            return False
        try:
            (self._sessions / f"{key}.json").unlink()
            return True
        except FileNotFoundError:
            return False

    def acknowledge_legacy_sessions_closed(self) -> None:
        """Record the one-time operator confirmation that older sessions are closed."""
        self._write_json(
            self._acknowledgement,
            {
                "schema-version": SCHEMA_VERSION,
                "confirmation": LEGACY_CONFIRMATION,
                "confirmed_at": _now(),
                "residual_risk": ATTESTATION_RISK,
            },
        )

    def legacy_acknowledgement_problem(self) -> str:
        """Return '' when the acknowledgement is complete, else what is wrong."""
        try:
            document = json.loads(self._acknowledgement.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return "the one-time confirmation that older unregistered sessions are closed is absent"
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return f"the older-session confirmation cannot be read ({exc})"
        if (
            not isinstance(document, dict)
            or document.get("schema-version") != SCHEMA_VERSION
            or document.get("confirmation") != LEGACY_CONFIRMATION
            or not isinstance(document.get("confirmed_at"), str)
        ):
            return "the older-session confirmation is incomplete or has an unknown form"
        return ""

    def sessions(self) -> tuple[SessionRecord, ...]:
        """Read every registry entry; unknown or malformed entries carry a problem."""
        if not self._sessions.exists():
            return ()
        records: list[SessionRecord] = []
        for path in sorted(self._sessions.iterdir()):
            match = _ENTRY_PATTERN.match(path.name)
            if match is None or not path.is_file():
                records.append(
                    SessionRecord(key=path.name, problem="unknown registry entry")
                )
                continue
            key = match.group(1)
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                continue
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                records.append(
                    SessionRecord(key=key, problem=f"unreadable entry ({exc})")
                )
                continue
            if (
                not isinstance(document, dict)
                or document.get("schema-version") != SCHEMA_VERSION
                or document.get("key") != key
                or not isinstance(document.get("host"), str)
                or not isinstance(document.get("cwd"), str)
                or not isinstance(document.get("registered_at"), str)
            ):
                records.append(SessionRecord(key=key, problem="malformed entry"))
                continue
            records.append(
                SessionRecord(
                    key=key,
                    host=document["host"],
                    cwd=document["cwd"],
                    registered_at=document["registered_at"],
                )
            )
        return tuple(records)

    def close_session(self, key: str) -> bool:
        """Remove one entry, well-formed or not, after operator attestation."""
        if "/" in key or "\\" in key or key in ("", ".", ".."):
            return False
        path = self._sessions / (key if not _KEY_PATTERN.match(key) else f"{key}.json")
        try:
            if path.is_dir() and not path.is_symlink():
                return False
            path.unlink()
            return True
        except FileNotFoundError:
            return False

    def evaluate_idle(
        self,
        *,
        own_key: str,
        require_legacy_confirmation: bool = True,
    ) -> Idle | NotIdle:
        """Decide global idle for an update requested by session ``own_key``.

        The caller must hold ``exclusive`` so no registration can interleave.
        """
        recovery_list = (
            "run `nwave-ai update sessions` to list registered sessions; close each "
            "listed session in its host, or, only when you know it already ended, run "
            "`nwave-ai update sessions close KEY --confirm-closed`; then retry"
        )
        if self._root.exists() and not self._root.is_dir():
            return NotIdle(
                f"the activity registry {self._root} is not a directory", recovery_list
            )
        problem = (
            self.legacy_acknowledgement_problem() if require_legacy_confirmation else ""
        )
        if problem:
            return NotIdle(
                f"{problem}, so unknown older work may still be active",
                "close every host session that started before this registry, then run "
                "`nwave-ai update consent install on --confirm-old-sessions-closed`",
            )
        try:
            records = self.sessions()
        except OSError as exc:
            return NotIdle(
                f"the activity registry cannot be read ({exc})", recovery_list
            )
        malformed = [record for record in records if record.problem]
        if malformed:
            names = ", ".join(
                f"{record.key} ({record.problem})" for record in malformed
            )
            return NotIdle(f"unknown activity is registered: {names}", recovery_list)
        if own_key not in {record.key for record in records}:
            return NotIdle(
                "the requesting session is not registered, so its own activity is unknown",
                "restart the host session so SessionStart registers it, then retry",
            )
        others = [record for record in records if record.key != own_key]
        if others:
            names = ", ".join(
                f"{record.key} ({record.host} in {record.cwd}, since {record.registered_at})"
                for record in others
            )
            return NotIdle(
                f"other host sessions are active and may be running a wave: {names}",
                recovery_list,
            )
        return Idle()
