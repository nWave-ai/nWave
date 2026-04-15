"""DES task signal file management.

Manages the lifecycle of signal files that track active DES subagents:
- Create signal when PreToolUse allows a DES-validated Task
- Read signal for correlation data before subagent completion
- Remove signal when SubagentStop fires

Signal files live in .nwave/des/ and support both namespaced (per project/step)
and legacy singleton formats for backward compatibility.

Two API levels:
- Low-level functions take explicit path parameters (for composition flexibility)
- Module-level constants + convenience wrappers use default paths (the single
  patch point for tests — patch DES_SESSION_DIR / DES_TASK_ACTIVE_FILE here)

Extracted from claude_code_hook_adapter.py as part of P4 decomposition.
"""

import json
import uuid
from pathlib import Path

from des.domain.nwave_dir_gitignore import ensure_nwave_gitignore


# -----------------------------------------------------------------------
# Default path constants — the single patch point for tests
# -----------------------------------------------------------------------
DES_SESSION_DIR = Path(".nwave") / "des"
DES_TASK_ACTIVE_FILE = DES_SESSION_DIR / "des-task-active"
DES_DELIVER_SESSION_FILE = DES_SESSION_DIR / "deliver-session.json"


# -----------------------------------------------------------------------
# Low-level functions (explicit path parameters)
# -----------------------------------------------------------------------


def signal_file_for(session_dir: Path, project_id: str, step_id: str) -> Path:
    """Return the namespaced signal file path for a project/step pair."""
    safe_name = f"{project_id}--{step_id}".replace("/", "_")
    return session_dir / f"des-task-active-{safe_name}"


def create_des_task_signal(
    session_dir: Path,
    task_active_file: Path,
    step_id: str = "",
    project_id: str = "",
) -> str:
    """Create DES task active signal file, namespaced by project/step.

    Called when PreToolUse allows a DES-validated Task.
    Indicates a DES subagent is currently running.

    Returns:
        task_correlation_id (UUID4 string) for correlating events across hooks.
        Returns empty string if signal creation fails.
    """
    task_correlation_id = str(uuid.uuid4())
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        ensure_nwave_gitignore(session_dir)
        from datetime import datetime, timezone

        signal = json.dumps(
            {
                "step_id": step_id,
                "project_id": project_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "task_correlation_id": task_correlation_id,
            }
        )
        sf = signal_file_for(session_dir, project_id, step_id)
        sf.write_text(signal)
        # Also write legacy singleton for backward compatibility
        task_active_file.write_text(signal)
    except Exception:
        pass  # Signal creation must never break the hook
    return task_correlation_id


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


# -----------------------------------------------------------------------
# Convenience wrappers using module-level path constants
# -----------------------------------------------------------------------
# Handler modules call these instead of passing paths explicitly.
# Tests patch DES_SESSION_DIR / DES_TASK_ACTIVE_FILE on this module.


def create_signal(step_id: str = "", project_id: str = "") -> str:
    """Create DES task signal using module-level default paths."""
    return create_des_task_signal(
        DES_SESSION_DIR, DES_TASK_ACTIVE_FILE, step_id, project_id
    )


def read_signal(project_id: str = "", step_id: str = "") -> dict | None:
    """Read DES task signal using module-level default paths."""
    return read_des_task_signal(
        DES_SESSION_DIR, DES_TASK_ACTIVE_FILE, project_id, step_id
    )


def remove_signal(project_id: str = "", step_id: str = "") -> None:
    """Remove DES task signal using module-level default paths."""
    remove_des_task_signal(DES_SESSION_DIR, DES_TASK_ACTIVE_FILE, project_id, step_id)
