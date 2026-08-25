"""Unit tests for deliver progress tracker.

Tests delivery-level progress tracking: roadmap step completion detection,
state persistence (save/load round-trip), and handler behavior for
SubagentStop integration.

Test Budget: 9 behaviors x 2 = 18 max.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

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
    directory: Path, events: list[dict | str], schema_version: str = "3.0"
) -> Path:
    """Write an execution-log.json with structured or legacy events."""
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


def test_issue_99_skipped_commit_remains_pending_until_executed(
    tmp_path: Path,
) -> None:
    """Only real public COMMIT/EXECUTED evidence completes a roadmap step."""
    repository_root = Path.cwd()
    plugin_root = tmp_path / "plugin"
    build = subprocess.run(
        [
            "/usr/bin/python3.12",
            "scripts/build_plugin.py",
            "--output-dir",
            str(plugin_root),
        ],
        cwd=repository_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    hook = plugin_root / "scripts" / "des-hook"
    assert hook.is_file()

    def fresh_project(tag: str) -> dict[str, Path]:
        project = Path(tempfile.mkdtemp(prefix=f"{tag}-", dir=tmp_path))
        for command in (
            ["git", "init", "--quiet"],
            ["git", "config", "user.name", "Issue 99 Oracle"],
            ["git", "config", "user.email", "issue99@example.invalid"],
        ):
            configured = subprocess.run(
                command,
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )
            assert configured.returncode == 0, configured.stderr
        nwave_config = project / ".nwave" / "local-config.json"
        nwave_config.parent.mkdir()
        nwave_config.write_text(json.dumps({"enabled_for_repo": True}))
        deliver = project / "docs" / "feature" / "issue-99" / "deliver"
        deliver.mkdir(parents=True)
        transcript = project / "transcript.jsonl"
        transcript.write_text(
            json.dumps(
                {
                    "message": {
                        "role": "user",
                        "content": (
                            "<!-- DES-VALIDATION : required -->\n"
                            "<!-- DES-PROJECT-ID : issue-99 -->\n"
                            "<!-- DES-STEP-ID : 01-01 -->\n"
                        ),
                    }
                }
            )
            + "\n"
        )
        return {
            "project": project,
            "local_config": nwave_config,
            "deliver": deliver,
            "transcript": transcript,
            "roadmap": deliver / "roadmap.json",
            "log": deliver / "execution-log.json",
            "progress": deliver / ".develop-progress.json",
        }

    def write_roadmap(paths: dict[str, Path], ids: list[str]) -> None:
        paths["roadmap"].write_text(
            json.dumps({"steps": [{"id": sid} for sid in ids]})
        )

    def write_log(paths: dict[str, Path], events: list[object]) -> None:
        paths["log"].write_text(
            json.dumps({"schema_version": "3.0", "events": events})
        )

    def run_hook(
        paths: dict[str, Path],
        *,
        raw_input: str | None = None,
        extra_pythonpath: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        hook_input = raw_input
        if hook_input is None:
            hook_input = json.dumps(
                {
                    "hook_event_name": "SubagentStop",
                    "stop_hook_active": False,
                    "session_id": "issue-99-oracle",
                    "agent_transcript_path": str(paths["transcript"]),
                    "cwd": str(paths["project"]),
                }
            )
        environment = os.environ.copy()
        environment["PATH"] = (
            f"{Path(sys.executable).parent}{os.pathsep}"
            f"{environment.get('PATH', '')}"
        )
        if extra_pythonpath is None:
            environment.pop("PYTHONPATH", None)
        else:
            environment["PYTHONPATH"] = str(extra_pythonpath)
        return subprocess.run(
            [str(hook), "deliver-progress"],
            cwd=paths["project"],
            input=hook_input,
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )

    def reminder_present(stderr: str) -> bool:
        lines = [line.strip() for line in stderr.splitlines()]
        return all(
            f"Phase {phase}" in stderr
            or any(
                line.startswith((f"{phase}. ", f"{phase}) "))
                for line in lines
            )
            for phase in range(3, 10)
        )

    assert not reminder_present("unrelated diagnostics: 3 4 5 6 7 8 9")

    def assert_snapshot(
        paths: dict[str, Path],
        result: subprocess.CompletedProcess[str],
        roadmap_ids: list[str],
        completed: set[str],
    ) -> bytes:
        expected_completed = [sid for sid in roadmap_ids if sid in completed]
        expected_pending = [sid for sid in roadmap_ids if sid not in completed]
        assert result.returncode == 0
        assert (paths["project"] / ".git").is_dir()
        assert json.loads(paths["local_config"].read_text())["enabled_for_repo"] is True
        assert paths["progress"].is_file(), (
            "activated public hook silently produced no progress snapshot; "
            f"stdout={result.stdout!r}, stderr={result.stderr!r}"
        )
        raw = paths["progress"].read_bytes()
        snapshot = json.loads(raw)
        assert snapshot["completed_steps"] == len(expected_completed)
        assert snapshot["completed_step_ids"] == expected_completed
        assert snapshot["pending_step_ids"] == expected_pending
        assert snapshot["all_steps_done"] is (not expected_pending)
        assert reminder_present(result.stderr) is (not expected_pending)
        return raw

    def pipe_event(sid: str, phase: str, status: str) -> str:
        return f"{sid}|{phase}|{status}|payload|2026-08-24T12:00:00Z"

    def dictionary_event(sid: str, phase: str, status: str) -> dict[str, str]:
        return {
            "sid": sid,
            "p": phase,
            "s": status,
            "d": "payload",
            "t": "2026-08-24T12:00:00Z",
        }

    # Canonical causal witness and liveness recovery through the built hook.
    recovery = fresh_project("recovery")
    write_roadmap(recovery, ["01-01"])
    write_log(recovery, [pipe_event("01-01", "COMMIT", "SKIPPED")])
    assert_snapshot(recovery, run_hook(recovery), ["01-01"], set())
    write_log(
        recovery,
        [
            pipe_event("01-01", "COMMIT", "SKIPPED"),
            dictionary_event("01-01", "COMMIT", "EXECUTED"),
            dictionary_event("01-01", "COMMIT", "EXECUTED"),
        ],
    )
    recovered = assert_snapshot(
        recovery, run_hook(recovery), ["01-01"], {"01-01"}
    )
    assert_snapshot(recovery, run_hook(recovery), ["01-01"], {"01-01"})
    assert recovery["progress"].read_bytes() == recovered

    # Closed malformed/missing/non-COMMIT/empty/off-roadmap failure partition.
    refused = fresh_project("refused")
    write_roadmap(refused, ["01-01", "01-02"])
    write_log(
        refused,
        [
            "01-01|COMMIT",
            {"sid": "01-01", "s": "EXECUTED", "d": "x", "t": "t"},
            {"p": "COMMIT", "s": "EXECUTED", "d": "x", "t": "t"},
            {"sid": "01-01", "p": "COMMIT", "d": "x", "t": "t"},
            dictionary_event("", "COMMIT", "EXECUTED"),
            dictionary_event("01-01", "NOT_COMMIT", "EXECUTED"),
            dictionary_event("off-roadmap", "COMMIT", "EXECUTED"),
            ["01-01", "COMMIT", "EXECUTED"],
            17,
            dictionary_event("01-02", "COMMIT", "EXECUTED"),
        ],
    )
    assert_snapshot(refused, run_hook(refused), ["01-01", "01-02"], {"01-02"})

    # Missing/corrupt/unreadable logs degrade to one whole pending snapshot.
    for log_mode in ("missing", "invalid", "unreadable"):
        paths = fresh_project(f"log-{log_mode}")
        write_roadmap(paths, ["01-01"])
        if log_mode == "invalid":
            paths["log"].write_text("{not-json")
        elif log_mode == "unreadable":
            write_log(paths, [dictionary_event("01-01", "COMMIT", "EXECUTED")])
            paths["log"].chmod(0)
        try:
            assert_snapshot(paths, run_hook(paths), ["01-01"], set())
        finally:
            if paths["log"].exists():
                paths["log"].chmod(0o600)

    # Hook-input/transcript rejection is non-blocking and publishes nothing.
    malformed_hook = fresh_project("malformed-hook")
    malformed_result = run_hook(malformed_hook, raw_input="{not-json")
    assert malformed_result.returncode == 0
    assert not malformed_hook["progress"].exists()
    assert not reminder_present(malformed_result.stderr)

    empty_hook = fresh_project("empty-hook")
    empty_result = run_hook(empty_hook, raw_input="")
    assert empty_result.returncode == 0
    assert not empty_hook["progress"].exists()
    assert not reminder_present(empty_result.stderr)

    missing_transcript = fresh_project("missing-transcript")
    missing_transcript["transcript"].unlink()
    missing_result = run_hook(missing_transcript)
    assert missing_result.returncode == 0
    assert not missing_transcript["progress"].exists()
    assert not reminder_present(missing_result.stderr)

    non_des = fresh_project("non-des")
    non_des["transcript"].write_text('{"message":{"role":"user","content":"x"}}\n')
    non_des_result = run_hook(non_des)
    assert non_des_result.returncode == 0
    assert not non_des["progress"].exists()
    assert not reminder_present(non_des_result.stderr)

    # Missing roadmap is quiet; malformed/unreadable roadmap preserves old bytes.
    missing_roadmap = fresh_project("roadmap-missing")
    write_log(
        missing_roadmap,
        [dictionary_event("01-01", "COMMIT", "EXECUTED")],
    )
    missing_roadmap_result = run_hook(missing_roadmap)
    assert missing_roadmap_result.returncode == 0
    assert not missing_roadmap["progress"].exists()

    for roadmap_mode in ("invalid", "unreadable"):
        paths = fresh_project(f"roadmap-{roadmap_mode}")
        old_bytes = b'{"sentinel":"old-whole-snapshot"}\n'
        paths["progress"].write_bytes(old_bytes)
        write_log(paths, [dictionary_event("01-01", "COMMIT", "EXECUTED")])
        if roadmap_mode == "invalid":
            paths["roadmap"].write_text("{not-json")
        else:
            write_roadmap(paths, ["01-01"])
            paths["roadmap"].chmod(0)
        try:
            result = run_hook(paths)
            assert result.returncode == 0
            assert result.stderr
            assert paths["progress"].read_bytes() == old_bytes
        finally:
            paths["roadmap"].chmod(0o600)

    # Temp creation/write failure leaves the old canonical and no residue.
    temp_failure = fresh_project("temp-write-failure")
    write_roadmap(temp_failure, ["01-01"])
    write_log(
        temp_failure,
        [dictionary_event("01-01", "COMMIT", "EXECUTED")],
    )
    old_snapshot = b'{"sentinel":"old-whole-snapshot"}\n'
    temp_failure["progress"].write_bytes(old_snapshot)
    names_before = {path.name for path in temp_failure["deliver"].iterdir()}
    temp_fault_path = tmp_path / "temp-write-fault"
    temp_fault_path.mkdir()
    (temp_fault_path / "sitecustomize.py").write_text(
        "import tempfile\n"
        "from pathlib import Path\n"
        "_issue99_original_mkstemp = tempfile.mkstemp\n"
        "def _issue99_mkstemp(*args, **kwargs):\n"
        "    directory = kwargs.get('dir')\n"
        "    if directory is None and len(args) >= 3:\n"
        "        directory = args[2]\n"
        "    if directory is not None and Path(directory).name == 'deliver':\n"
        "        raise OSError('issue99 injected temp-write failure')\n"
        "    return _issue99_original_mkstemp(*args, **kwargs)\n"
        "tempfile.mkstemp = _issue99_mkstemp\n"
    )
    temp_failure_result = run_hook(
        temp_failure, extra_pythonpath=temp_fault_path
    )
    assert temp_failure_result.returncode == 0
    assert "issue99 injected temp-write failure" in temp_failure_result.stderr
    assert temp_failure["progress"].read_bytes() == old_snapshot
    assert {path.name for path in temp_failure["deliver"].iterdir()} == names_before

    # Replace failure after a whole temp write leaves the old canonical.
    save_failure = fresh_project("replace-failure")
    write_roadmap(save_failure, ["01-01"])
    write_log(
        save_failure,
        [dictionary_event("01-01", "COMMIT", "EXECUTED")],
    )
    old_snapshot = b'{"sentinel":"old-whole-snapshot"}\n'
    save_failure["progress"].write_bytes(old_snapshot)
    names_before = {path.name for path in save_failure["deliver"].iterdir()}
    fault_path = tmp_path / "replace-fault"
    fault_path.mkdir()
    (fault_path / "sitecustomize.py").write_text(
        "from pathlib import Path\n"
        "_issue99_original_replace = Path.replace\n"
        "def _issue99_replace(self, target):\n"
        "    if Path(target).name == '.develop-progress.json':\n"
        "        raise OSError('issue99 injected replace failure')\n"
        "    return _issue99_original_replace(self, target)\n"
        "Path.replace = _issue99_replace\n"
    )
    save_failure_result = run_hook(
        save_failure, extra_pythonpath=fault_path
    )
    assert save_failure_result.returncode == 0
    assert "issue99 injected replace failure" in save_failure_result.stderr
    assert save_failure["progress"].read_bytes() == old_snapshot
    assert {path.name for path in save_failure["deliver"].iterdir()} == names_before

    safe_identifier = st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
        min_size=1,
        max_size=10,
    )
    safe_token = st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ .",
        min_size=0,
        max_size=12,
    )

    @st.composite
    def semantic_histories(draw):
        roadmap_ids = draw(
            st.lists(safe_identifier, min_size=1, max_size=4, unique=True)
        )
        event_count = draw(st.integers(min_value=0, max_value=8))
        semantic_events: list[tuple[str, str, str, str]] = []
        for _ in range(event_count):
            sid_source = draw(st.sampled_from(["roadmap", "off-roadmap", "empty"]))
            if sid_source == "roadmap":
                sid = draw(st.sampled_from(roadmap_ids))
            elif sid_source == "off-roadmap":
                sid = "OFFROAD:" + draw(safe_identifier)
            else:
                sid = ""
            phase = draw(st.one_of(st.sampled_from(["COMMIT", "ROLLBACK"]), safe_token))
            status = draw(
                st.one_of(
                    st.sampled_from(["EXECUTED", "SKIPPED", "FAILED"]),
                    safe_token,
                )
            )
            encoding = draw(st.sampled_from(["pipe", "dictionary"]))
            semantic_events.append((sid, phase, status, encoding))
        return roadmap_ids, semantic_events

    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(semantic_histories())
    def history_laws(
        generated: tuple[list[str], list[tuple[str, str, str, str]]],
    ) -> None:
        roadmap_ids, semantic_events = generated

        def expected_completed(
            events: list[tuple[str, str, str, str]],
        ) -> set[str]:
            return {
                sid
                for sid, phase, status, _encoding in events
                if sid in roadmap_ids
                and sid
                and phase == "COMMIT"
                and status == "EXECUTED"
            }

        def encode(
            events: list[tuple[str, str, str, str]], mode: str
        ) -> list[object]:
            encoded: list[object] = []
            for index, (sid, phase, status, generated_encoding) in enumerate(events):
                encoding = generated_encoding
                if mode == "pipe":
                    encoding = "pipe"
                elif mode == "dictionary":
                    encoding = "dictionary"
                elif mode == "alternating":
                    encoding = "pipe" if index % 2 == 0 else "dictionary"
                if encoding == "pipe":
                    encoded.append(pipe_event(sid, phase, status))
                else:
                    encoded.append(dictionary_event(sid, phase, status))
            return encoded

        expected = expected_completed(semantic_events)
        observations: list[tuple[list[str], list[str], bool]] = []
        for mode in ("pipe", "dictionary", "generated", "alternating"):
            paths = fresh_project(f"pbt-{mode}")
            write_roadmap(paths, roadmap_ids)
            write_log(paths, encode(semantic_events, mode))
            assert_snapshot(paths, run_hook(paths), roadmap_ids, expected)
            snapshot = json.loads(paths["progress"].read_text())
            observations.append(
                (
                    snapshot["completed_step_ids"],
                    snapshot["pending_step_ids"],
                    snapshot["all_steps_done"],
                )
            )
        assert observations.count(observations[0]) == len(observations)

        replay = fresh_project("pbt-replay")
        write_roadmap(replay, roadmap_ids)
        mixed = encode(semantic_events, "generated")
        write_log(replay, mixed + list(reversed(mixed)) + mixed)
        replay_bytes = assert_snapshot(replay, run_hook(replay), roadmap_ids, expected)
        assert_snapshot(replay, run_hook(replay), roadmap_ids, expected)
        assert replay["progress"].read_bytes() == replay_bytes

        target = roadmap_ids[0]
        pending_events = [
            (
                sid,
                phase,
                "SKIPPED"
                if sid == target and phase == "COMMIT" and status == "EXECUTED"
                else status,
                encoding,
            )
            for sid, phase, status, encoding in semantic_events
        ]
        recovery_paths = fresh_project("pbt-recovery")
        write_roadmap(recovery_paths, roadmap_ids)
        write_log(recovery_paths, encode(pending_events, "generated"))
        pending_expected = expected_completed(pending_events)
        assert target not in pending_expected
        assert_snapshot(
            recovery_paths,
            run_hook(recovery_paths),
            roadmap_ids,
            pending_expected,
        )
        recovered_events = pending_events + [
            (target, "COMMIT", "EXECUTED", "dictionary")
        ]
        write_log(recovery_paths, encode(recovered_events, "generated"))
        assert_snapshot(
            recovery_paths,
            run_hook(recovery_paths),
            roadmap_ids,
            pending_expected | {target},
        )

    history_laws()


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

    def test_skipped_commit_events_do_not_complete_steps(
        self, roadmap_dir: Path
    ) -> None:
        steps = [
            {"id": "01-01"},
            {"id": "01-02"},
            {"id": "01-03"},
        ]
        roadmap_path = _write_roadmap(roadmap_dir, steps)
        events = [
            {
                "sid": "01-01",
                "p": "COMMIT",
                "s": "SKIPPED",
                "d": "CHECKPOINT_PENDING: tests are red",
                "t": "2026-03-16T10:00:00Z",
            },
            (
                "01-02|COMMIT|SKIPPED|CHECKPOINT_PENDING: uncommitted changes"
                "|2026-03-16T10:01:00Z"
            ),
            "01-03|COMMIT|EXECUTED|PASS|2026-03-16T10:02:00Z",
        ]
        exec_log_path = _write_execution_log(roadmap_dir, events)

        state = track_progress(roadmap_path, exec_log_path)

        assert state.completed_steps == 1
        assert state.completed_step_ids == ("01-03",)
        assert state.pending_step_ids == ("01-01", "01-02")
        assert state.all_steps_done is False


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
