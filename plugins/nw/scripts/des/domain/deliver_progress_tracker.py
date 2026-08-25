"""Deliver progress tracker - tracks delivery-level step completion.

Pure domain logic that cross-references roadmap steps against execution-log
entries to determine how many steps have completed the COMMIT phase.
Provides save/load for persisting progress state between handler invocations.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from des.domain._roadmap_helpers import extract_step_ids as _extract_step_ids
from des.domain.phase_event import PhaseEventParser


@dataclass(frozen=True)
class DeliverProgressState:
    """Immutable snapshot of delivery progress.

    Attributes:
        project_id: Feature/project identifier
        total_steps: Total number of steps in roadmap
        completed_steps: Number of steps with COMMIT phase entries
        completed_step_ids: Step IDs that have COMMIT entries
        pending_step_ids: Step IDs without COMMIT entries
        all_steps_done: True when all steps have COMMIT entries
        phases_completed: Mapping of orchestrator phase name to ISO timestamp
    """

    project_id: str
    total_steps: int
    completed_steps: int
    completed_step_ids: tuple[str, ...] = ()
    pending_step_ids: tuple[str, ...] = ()
    all_steps_done: bool = False
    phases_completed: dict[str, str] = field(default_factory=dict)


def _find_committed_step_ids(execution_log: dict) -> set[str]:
    """Find step IDs whose COMMIT phase was executed.

    Parse through the canonical event parser so both supported formats retain
    the same status semantics.  A recorded but skipped COMMIT is not evidence
    that the step was committed.
    """
    events = PhaseEventParser().parse_all(execution_log.get("events", []))
    return {
        event.step_id
        for event in events
        if event.phase_name == "COMMIT" and event.status == "EXECUTED"
    }


def track_progress(
    roadmap_path: Path, execution_log_path: Path
) -> DeliverProgressState:
    """Track delivery progress by comparing roadmap steps to execution log.

    Reads roadmap.json to extract step IDs, reads execution-log.json to find
    steps with COMMIT phase entries, and computes a progress snapshot.

    If execution-log.json does not exist or is empty, reports 0 completed.
    If roadmap has 0 steps, reports vacuously all done.
    """
    roadmap = json.loads(roadmap_path.read_text(encoding="utf-8"))
    all_step_ids = _extract_step_ids(roadmap)

    committed: set[str] = set()
    if execution_log_path.exists():
        try:
            exec_log = json.loads(execution_log_path.read_text(encoding="utf-8"))
            committed = _find_committed_step_ids(exec_log)
        except (json.JSONDecodeError, OSError):
            committed = set()

    completed_ids = tuple(sid for sid in all_step_ids if sid in committed)
    pending_ids = tuple(sid for sid in all_step_ids if sid not in committed)
    total = len(all_step_ids)
    completed_count = len(completed_ids)
    all_done = total == completed_count

    project_id = roadmap.get("project_id", "")

    return DeliverProgressState(
        project_id=project_id,
        total_steps=total,
        completed_steps=completed_count,
        completed_step_ids=completed_ids,
        pending_step_ids=pending_ids,
        all_steps_done=all_done,
        phases_completed={},
    )


def load_progress(progress_path: Path) -> DeliverProgressState | None:
    """Load progress state from a .develop-progress.json file.

    Returns None if the file is missing or corrupted.
    """
    if not progress_path.exists():
        return None
    try:
        data = json.loads(progress_path.read_text(encoding="utf-8"))
        return DeliverProgressState(
            project_id=data["project_id"],
            total_steps=data["total_steps"],
            completed_steps=data["completed_steps"],
            completed_step_ids=tuple(data.get("completed_step_ids", ())),
            pending_step_ids=tuple(data.get("pending_step_ids", ())),
            all_steps_done=data["all_steps_done"],
            phases_completed=data.get("phases_completed", {}),
        )
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def save_progress(state: DeliverProgressState, progress_path: Path) -> None:
    """Save progress state atomically (write to temp, rename)."""
    data = asdict(state)
    # Convert tuples to lists for JSON serialization
    data["completed_step_ids"] = list(data["completed_step_ids"])
    data["pending_step_ids"] = list(data["pending_step_ids"])

    progress_dir = progress_path.parent
    progress_dir.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(progress_dir), suffix=".tmp", prefix=".progress-"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        Path(tmp_path).replace(progress_path)
    except Exception:
        tmp = Path(tmp_path)
        if tmp.exists():
            tmp.unlink()
        raise
