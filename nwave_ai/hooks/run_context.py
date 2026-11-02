"""Hook run context: the declared provenance of an audit event, the UTC clock port and adapter,
and the task-signal file that tracks an active nWave subagent.

Moved verbatim from the removed DES runtime (S5-OQ6 closure of the hook handlers). Only the
closure the handlers reach is kept: the signal path constants, the signal read, and its removal.

Run context is DECLARED, never inferred: it comes from the ``NWAVE_RUN_CONTEXT`` environment
variable alone, and an absent declaration resolves to the explicit ``unknown`` state.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping


__all__ = [
    "DES_SESSION_DIR",
    "DES_TASK_ACTIVE_FILE",
    "RUN_CONTEXT_ENV",
    "UNKNOWN_RUN_CONTEXT",
    "SystemTimeProvider",
    "TimeProvider",
    "read_des_task_signal",
    "remove_des_task_signal",
    "remove_signal",
    "resolve_run_context",
    "signal_file_for",
]

RUN_CONTEXT_ENV = "NWAVE_RUN_CONTEXT"
"""The single environment key a caller declares its run context through."""

UNKNOWN_RUN_CONTEXT = "unknown"
"""Explicit third state for an undeclared context. Never an absent field."""


def resolve_run_context(env: Mapping[str, str]) -> str:
    """Resolve the declared run context, or the explicit unknown state.

    Args:
        env: The environment mapping to read the declaration from. Injected
            rather than read from `os.environ` so the resolution is a pure
            function of its input and testable without process-global state.

    Returns:
        The declared context stripped of surrounding whitespace, or
        `UNKNOWN_RUN_CONTEXT` when the declaration is absent or blank.
    """
    declared = env.get(RUN_CONTEXT_ENV, "").strip()
    return declared or UNKNOWN_RUN_CONTEXT


class TimeProvider(ABC):
    """Driven port: the current UTC time."""

    @abstractmethod
    def now_utc(self) -> datetime:
        """Return the current UTC time."""


class SystemTimeProvider(TimeProvider):
    """Production implementation of time provider. Returns actual system time in UTC."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        return datetime.now(timezone.utc)


# -----------------------------------------------------------------------
# Task signal: the marker of an active nWave subagent
# -----------------------------------------------------------------------
DES_SESSION_DIR = Path(".nwave") / "des"
DES_TASK_ACTIVE_FILE = DES_SESSION_DIR / "des-task-active"


def signal_file_for(session_dir: Path, project_id: str, step_id: str) -> Path:
    """Return the namespaced signal file path for a project/step pair."""
    safe_name = f"{project_id}--{step_id}".replace("/", "_")
    return session_dir / f"des-task-active-{safe_name}"


def read_des_task_signal(
    session_dir: Path,
    task_active_file: Path,
    project_id: str = "",
    step_id: str = "",
) -> dict | None:
    """Read DES task active signal file before removal.

    Tries namespaced file first, falls back to legacy singleton.

    Returns:
        Signal data dict with step_id, project_id, and created_at, or None.
    """
    try:
        # Try namespaced signal first (race-condition resistant)
        if project_id and step_id:
            namespaced = signal_file_for(session_dir, project_id, step_id)
            if namespaced.exists():
                return json.loads(namespaced.read_text())
        # Fallback to legacy singleton
        if task_active_file.exists():
            return json.loads(task_active_file.read_text())
    except Exception:
        # WHAT: signal file vanished between exists() and read (race with
        # another process), or contains malformed JSON.
        # WHY: this is a best-effort read of a transient signal file (see
        # docstring: "Returns ... or None") -- a race/corruption must
        # degrade to "no signal", never raise.
        # HOW: safe to return None below -- caller already treats None as
        # "no active signal".
        pass
    return None


def remove_des_task_signal(
    session_dir: Path,
    task_active_file: Path,
    project_id: str = "",
    step_id: str = "",
) -> None:
    """Remove DES task active signal file(s).

    Called when SubagentStop fires (DES task completed).
    Removes both namespaced and legacy singleton files.
    """
    try:
        if project_id and step_id:
            namespaced = signal_file_for(session_dir, project_id, step_id)
            if namespaced.exists():
                namespaced.unlink()
        if task_active_file.exists():
            task_active_file.unlink()
    except Exception:
        pass  # Signal cleanup must never break the hook


def remove_signal(project_id: str = "", step_id: str = "") -> None:
    """Remove DES task signal using module-level default paths."""
    remove_des_task_signal(DES_SESSION_DIR, DES_TASK_ACTIVE_FILE, project_id, step_id)
