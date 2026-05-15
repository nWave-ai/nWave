"""Unit tests for deliver progress tracker.

Tests delivery-level progress tracking: roadmap step completion detection,
state persistence (save/load round-trip), and handler behavior for
SubagentStop integration.

Test Budget: 8 behaviors x 2 = 16 max.
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from des.domain.deliver_progress_tracker import (
    DeliverProgressState,
    load_progress,
    save_progress,
    track_progress,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def roadmap_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for roadmap and execution-log files."""
    return tmp_path


def _write_roadmap(directory: Path, steps: list[dict]) -> Path:
    """Write a roadmap.json with the given steps (flat format)."""
    roadmap_path = directory / "roadmap.json"
    roadmap_path.write_text(json.dumps({"steps": steps}))
    return roadmap_path


def _write_execution_log(
    directory: Path, events: list[dict], schema_version: str = "3.0"
) -> Path:
    """Write an execution-log.json with v3.0 structured events."""
    log_path = directory / "execution-log.json"
    log_path.write_text(
        json.dumps({"schema_version": schema_version, "events": events})
    )
    return log_path


def _make_commit_event(step_id: str) -> dict:
    """Create a v3.0 COMMIT event for a step."""
    return {
        "sid": step_id,
        "p": "COMMIT",
        "s": "EXECUTED",
        "d": "PASS",
        "t": "2026-03-16T10:00:00Z",
    }


# ---------------------------------------------------------------------------
# AC1: 3 steps, 2 completed
# ---------------------------------------------------------------------------


class TestTrackProgressPartialCompletion:
    """AC1: 3-step roadmap, 2 with COMMIT entries -> partial completion."""

    def test_reports_correct_totals_and_step_lists(self, roadmap_dir: Path):
        steps = [
            {"id": "01-01"},
            {"id": "01-02"},
            {"id": "01-03"},
        ]
        roadmap_path = _write_roadmap(roadmap_dir, steps)
        events = [_make_commit_event("01-01"), _make_commit_event("01-03")]
        exec_log_path = _write_execution_log(roadmap_dir, events)

        state = track_progress(roadmap_path, exec_log_path)

        assert state.total_steps == 3
        assert state.completed_steps == 2
        assert state.all_steps_done is False
        assert set(state.completed_step_ids) == {"01-01", "01-03"}
        assert state.pending_step_ids == ("01-02",)
        assert state.phases_completed == {}


# ---------------------------------------------------------------------------
# AC2: All steps completed
# ---------------------------------------------------------------------------


class TestTrackProgressAllComplete:
    """AC2: 2-step roadmap, both with COMMIT -> all_steps_done."""

    def test_reports_all_done(self, roadmap_dir: Path):
        steps = [{"id": "01-01"}, {"id": "01-02"}]
        roadmap_path = _write_roadmap(roadmap_dir, steps)
        events = [_make_commit_event("01-01"), _make_commit_event("01-02")]
        exec_log_path = _write_execution_log(roadmap_dir, events)

        state = track_progress(roadmap_path, exec_log_path)

        assert state.total_steps == 2
        assert state.completed_steps == 2
        assert state.all_steps_done is True
        assert state.pending_step_ids == ()


# ---------------------------------------------------------------------------
# AC3: Missing or empty execution log
# ---------------------------------------------------------------------------


class TestTrackProgressMissingLog:
    """AC3: Execution log missing or empty -> 0 completed, no error."""

    def test_missing_execution_log_returns_zero_completed(self, roadmap_dir: Path):
        steps = [{"id": "01-01"}, {"id": "01-02"}]
        roadmap_path = _write_roadmap(roadmap_dir, steps)
        nonexistent_log = roadmap_dir / "execution-log.json"

        state = track_progress(roadmap_path, nonexistent_log)

        assert state.total_steps == 2
        assert state.completed_steps == 0
        assert state.all_steps_done is False

    def test_empty_execution_log_returns_zero_completed(self, roadmap_dir: Path):
        steps = [{"id": "01-01"}]
        roadmap_path = _write_roadmap(roadmap_dir, steps)
        exec_log_path = _write_execution_log(roadmap_dir, events=[])

        state = track_progress(roadmap_path, exec_log_path)

        assert state.completed_steps == 0
        assert state.all_steps_done is False


# ---------------------------------------------------------------------------
# AC4: 0-step roadmap (vacuous)
# ---------------------------------------------------------------------------


class TestTrackProgressEmptyRoadmap:
    """AC4: 0-step roadmap -> vacuously all done."""

    def test_zero_steps_is_vacuously_done(self, roadmap_dir: Path):
        roadmap_path = _write_roadmap(roadmap_dir, steps=[])
        exec_log_path = _write_execution_log(roadmap_dir, events=[])

        state = track_progress(roadmap_path, exec_log_path)

        assert state.total_steps == 0
        assert state.completed_steps == 0
        assert state.all_steps_done is True


# ---------------------------------------------------------------------------
# AC5: Handler prints phases 3-9 when all steps done
# ---------------------------------------------------------------------------


class TestHandlerAllStepsDone:
    """AC5: Handler with all steps done -> stderr contains phases 3-9."""

    def test_stderr_contains_remaining_phase_numbers(self, roadmap_dir: Path):
        from des.adapters.drivers.hooks.deliver_progress_handler import (
            handle_deliver_progress,
        )

        # Setup roadmap and execution log with all steps done
        steps = [{"id": "01-01"}]
        _write_roadmap(roadmap_dir, steps)
        events = [_make_commit_event("01-01")]
        _write_execution_log(roadmap_dir, events)

        # Build a minimal transcript with DES markers
        transcript_path = roadmap_dir / "transcript.jsonl"
        transcript_content = json.dumps(
            {
                "message": {
                    "role": "user",
                    "content": (
                        "<!-- DES-VALIDATION : required -->\n"
                        "<!-- DES-PROJECT-ID : test-project -->\n"
                        "<!-- DES-STEP-ID : 01-01 -->\n"
                    ),
                }
            }
        )
        transcript_path.write_text(transcript_content + "\n")

        hook_input = json.dumps(
            {
                "agent_transcript_path": str(transcript_path),
                "cwd": str(roadmap_dir),
            }
        )

        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(hook_input)),
            patch("sys.stderr", stderr_capture),
            patch(
                "des.adapters.drivers.hooks.deliver_progress_handler"
                "._resolve_deliver_paths",
                return_value=(
                    roadmap_dir / "roadmap.json",
                    roadmap_dir / "execution-log.json",
                    roadmap_dir / ".develop-progress.json",
                ),
            ),
        ):
            exit_code = handle_deliver_progress()

        assert exit_code == 0
        stderr_output = stderr_capture.getvalue()
        for phase_num in ["3", "4", "5", "6", "7", "8", "9"]:
            assert phase_num in stderr_output, (
                f"Phase {phase_num} not found in stderr: {stderr_output}"
            )


# ---------------------------------------------------------------------------
# AC6: Non-DES agent -> return 0, no progress file
# ---------------------------------------------------------------------------


class TestHandlerNonDesAgent:
    """AC6: Non-DES agent -> return 0, no progress file written."""

    def test_non_des_returns_zero_without_progress_file(self, roadmap_dir: Path):
        from des.adapters.drivers.hooks.deliver_progress_handler import (
            handle_deliver_progress,
        )

        # Transcript without DES markers
        transcript_path = roadmap_dir / "transcript.jsonl"
        transcript_content = json.dumps(
            {"message": {"role": "user", "content": "Just a regular task"}}
        )
        transcript_path.write_text(transcript_content + "\n")

        hook_input = json.dumps(
            {
                "agent_transcript_path": str(transcript_path),
                "cwd": str(roadmap_dir),
            }
        )

        progress_file = roadmap_dir / ".develop-progress.json"
        with patch("sys.stdin", StringIO(hook_input)):
            exit_code = handle_deliver_progress()

        assert exit_code == 0
        assert not progress_file.exists()


# ---------------------------------------------------------------------------
# AC7: Empty stdin -> return 0 without error
# ---------------------------------------------------------------------------


class TestHandlerEmptyStdin:
    """AC7: Empty stdin -> return 0."""

    def test_empty_stdin_returns_zero(self):
        from des.adapters.drivers.hooks.deliver_progress_handler import (
            handle_deliver_progress,
        )

        with patch("sys.stdin", StringIO("")):
            exit_code = handle_deliver_progress()

        assert exit_code == 0


# ---------------------------------------------------------------------------
# AC8: Round-trip save/load
# ---------------------------------------------------------------------------


class TestProgressRoundTrip:
    """AC8: save then load preserves state including phases_completed."""

    def test_round_trip_preserves_state(self, roadmap_dir: Path):
        state = DeliverProgressState(
            project_id="test-project",
            total_steps=3,
            completed_steps=2,
            completed_step_ids=("01-01", "01-03"),
            pending_step_ids=("01-02",),
            all_steps_done=False,
            phases_completed={"phase_3": "2026-03-16T10:00:00Z"},
        )
        progress_path = roadmap_dir / ".develop-progress.json"

        save_progress(state, progress_path)
        loaded = load_progress(progress_path)

        assert loaded is not None
        assert loaded.project_id == state.project_id
        assert loaded.total_steps == state.total_steps
        assert loaded.completed_steps == state.completed_steps
        assert loaded.completed_step_ids == state.completed_step_ids
        assert loaded.pending_step_ids == state.pending_step_ids
        assert loaded.all_steps_done == state.all_steps_done
        assert loaded.phases_completed == state.phases_completed

    def test_load_missing_file_returns_none(self, roadmap_dir: Path):
        result = load_progress(roadmap_dir / "nonexistent.json")
        assert result is None
