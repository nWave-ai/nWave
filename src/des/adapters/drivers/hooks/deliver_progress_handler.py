"""Deliver progress handler - SubagentStop hook for tracking delivery progress.

Integrates with Claude Code's SubagentStop hook event to track which roadmap
steps have been completed. When all steps are done, prints a reminder about
remaining orchestrator phases (3-9) to stderr.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from des.adapters.drivers.hooks.execution_log_resolver import resolve_execution_log_path
from des.adapters.drivers.hooks.subagent_stop_handler import (
    extract_des_context_from_transcript,
)
from des.domain.deliver_progress_tracker import save_progress, track_progress


REMAINING_PHASES_REMINDER = (
    "All {count} delivery steps completed. "
    "Remaining orchestrator phases not yet tracked: "
    "Phase 3 (Refactoring), Phase 4 (Review), Phase 5 (Mutation Testing), "
    "Phase 6 (Integrity Verification), Phase 7 (Finalize), "
    "Phase 8 (Retrospective), Phase 9 (Report)"
)


def _resolve_deliver_paths(cwd: str, project_id: str) -> tuple[Path, Path, Path]:
    """Resolve paths for roadmap, execution-log, and progress files.

    Discovers the docs base from disk (reusing the step 01-01 resolver), so a
    project namespaced under the override base docs/nwave/feature is found
    instead of being silently missed under a hardcoded docs/feature. Wave
    resolution checks deliver/ first, then scans for any single wave subdir
    containing execution-log.json. Falls back to docs/feature/<id>/deliver on
    error so downstream missing-file handling is preserved.
    """
    try:
        exec_log_path = resolve_execution_log_path(project_id, cwd=Path(cwd))
        wave_dir = exec_log_path.parent
    except (FileNotFoundError, ValueError):
        wave_dir = Path(cwd) / "docs" / "feature" / project_id / "deliver"
        exec_log_path = wave_dir / "execution-log.json"
    return (
        wave_dir / "roadmap.json",
        exec_log_path,
        wave_dir / ".develop-progress.json",
    )


def handle_deliver_progress() -> int:
    """Handle deliver progress tracking on SubagentStop.

    Always returns 0 (never blocks). Reads stdin JSON, extracts DES context
    from agent transcript. If non-DES agent, returns immediately. Otherwise
    tracks progress and saves state. When all steps done, prints reminder.
    """
    raw = sys.stdin.read().strip()
    if not raw:
        return 0

    try:
        hook_input = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return 0

    transcript_path = hook_input.get("agent_transcript_path")
    if not transcript_path:
        return 0

    des_context = extract_des_context_from_transcript(transcript_path)
    if des_context is None:
        return 0

    project_id = des_context["project_id"]
    cwd = hook_input.get("cwd", "")

    # Marker-aware effective cwd: validate DES-PROJECT-ROOT marker (if any),
    # use it as the base for path resolution; fall back to hook_input cwd on
    # missing/invalid marker. Rex RCA F-DES-WORKTREE-EXECUTION-LOG-RESOLUTION.
    raw_marker = des_context.get("project_root")
    effective_cwd = cwd
    if raw_marker:
        from des.adapters.drivers.hooks.project_root_validator import (
            validate_project_root,
        )

        validated = validate_project_root(raw_marker, cwd)
        if validated is not None:
            effective_cwd = str(validated)

    roadmap_path, exec_log_path, progress_path = _resolve_deliver_paths(
        effective_cwd, project_id
    )

    if not roadmap_path.exists():
        return 0

    try:
        state = track_progress(roadmap_path, exec_log_path)
        save_progress(state, progress_path)

        # Only remind when there are actual steps completed (not vacuous 0-step case)
        if state.all_steps_done and state.total_steps > 0:
            reminder = REMAINING_PHASES_REMINDER.format(count=state.total_steps)
            # Reminder covers phases 3-9 (all post-execution phases).
            # The finalize gate (check_phase_progress) only enforces 3-5 because
            # phases 6-9 happen during/after finalize itself.
            print(reminder, file=sys.stderr)
    except Exception as exc:
        # Never block — filesystem errors are non-fatal for progress tracking
        print(f"[deliver-progress] non-fatal error: {exc}", file=sys.stderr)

    return 0
