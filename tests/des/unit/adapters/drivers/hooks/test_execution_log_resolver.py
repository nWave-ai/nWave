"""Regression tests for wave-agnostic execution-log path resolution.

Root cause (Rex RCA): DES-PROJECT-ID encodes only feature id, not wave subdir.
Both hooks hardcoded deliver/ — a relic of the DELIVER-only DES era. Bugfix,
design, and distill features fail the stop hook because their logs live in
bugfix/, design/, or distill/ subdirectories.

Fix (Option 2): glob-scan fallback with explicit priority for deliver/.
"""

import json
import subprocess as sp

import pytest

from des.adapters.drivers.hooks.execution_log_resolver import resolve_execution_log_path
from des.adapters.drivers.hooks.subagent_stop_handler import handle_subagent_stop


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_transcript(tmp_path, prompt: str) -> str:
    """Create a minimal JSONL transcript with a user message."""
    transcript_path = tmp_path / "agent.jsonl"
    user_msg = {
        "type": "user",
        "message": {"role": "user", "content": prompt},
        "uuid": "test-uuid",
        "timestamp": "2026-01-01T10:00:00Z",
    }
    transcript_path.write_text(json.dumps(user_msg) + "\n")
    return str(transcript_path)


def _make_hook_input(transcript_path: str, cwd: str) -> str:
    return json.dumps(
        {
            "session_id": "test-session",
            "hook_event_name": "SubagentStop",
            "agent_id": "test-agent",
            "agent_type": "software-crafter",
            "agent_transcript_path": transcript_path,
            "stop_hook_active": False,
            "cwd": cwd,
            "transcript_path": "/tmp/session.jsonl",
            "permission_mode": "default",
        }
    )


def _complete_exec_log(project_id: str, step_id: str = "01-01") -> str:
    return json.dumps(
        {
            "project_id": project_id,
            "events": [
                f"{step_id}|PREPARE|EXECUTED|PASS|2026-01-01T10:00:00Z",
                f"{step_id}|RED_ACCEPTANCE|EXECUTED|PASS|2026-01-01T10:05:00Z",
                f"{step_id}|RED_UNIT|EXECUTED|PASS|2026-01-01T10:10:00Z",
                f"{step_id}|GREEN|EXECUTED|PASS|2026-01-01T10:20:00Z",
                f"{step_id}|REVIEW|EXECUTED|PASS|2026-01-01T10:30:00Z",
                f"{step_id}|REFACTOR_CONTINUOUS|SKIPPED|CHECKPOINT_PENDING: Minimal|2026-01-01T10:35:00Z",
                f"{step_id}|COMMIT|EXECUTED|PASS|2026-01-01T11:00:00Z",
            ],
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Unit tests: resolve_execution_log_path()
# ---------------------------------------------------------------------------


class TestResolveExecutionLogPath:
    """Tests for the wave-agnostic resolver helper.

    Test Budget: 6 behaviors x 2 = 12 max. Using 5 focused tests.
    """

    def test_returns_deliver_log_when_it_exists(self, tmp_path):
        """Behavior 1: deliver/ log exists → use it (preserve backward compat)."""
        project_id = "my-feature"
        deliver_dir = tmp_path / "docs" / "feature" / project_id / "deliver"
        deliver_dir.mkdir(parents=True)
        log = deliver_dir / "execution-log.json"
        log.write_text("{}")

        result = resolve_execution_log_path(
            project_id, base=tmp_path / "docs" / "feature"
        )

        assert result == log

    def test_returns_bugfix_log_when_no_deliver_log(self, tmp_path):
        """Behavior 2a: no deliver/ log, single bugfix/ match → use it."""
        project_id = "fix-something-p0"
        bugfix_dir = tmp_path / "docs" / "feature" / project_id / "bugfix"
        bugfix_dir.mkdir(parents=True)
        log = bugfix_dir / "execution-log.json"
        log.write_text("{}")

        result = resolve_execution_log_path(
            project_id, base=tmp_path / "docs" / "feature"
        )

        assert result == log

    @pytest.mark.parametrize("wave", ["design", "distill"])
    def test_returns_wave_log_for_other_wave_modes(self, tmp_path, wave):
        """Behavior 2b: non-deliver single match → use it (design, distill)."""
        project_id = "some-feature"
        wave_dir = tmp_path / "docs" / "feature" / project_id / wave
        wave_dir.mkdir(parents=True)
        log = wave_dir / "execution-log.json"
        log.write_text("{}")

        result = resolve_execution_log_path(
            project_id, base=tmp_path / "docs" / "feature"
        )

        assert result == log

    def test_raises_file_not_found_when_no_log_anywhere(self, tmp_path):
        """Behavior 3: 0 matches → FileNotFoundError."""
        project_dir = tmp_path / "docs" / "feature" / "empty-project"
        project_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="No execution-log.json"):
            resolve_execution_log_path(
                "empty-project", base=tmp_path / "docs" / "feature"
            )

    def test_raises_value_error_when_ambiguous_multiple_matches(self, tmp_path):
        """Behavior 4: 2+ matches without deliver/ → ValueError (ambiguous)."""
        project_id = "multi-wave"
        for wave in ("bugfix", "design"):
            wave_dir = tmp_path / "docs" / "feature" / project_id / wave
            wave_dir.mkdir(parents=True)
            (wave_dir / "execution-log.json").write_text("{}")

        with pytest.raises(ValueError, match="Ambiguous"):
            resolve_execution_log_path(project_id, base=tmp_path / "docs" / "feature")

    def test_deliver_takes_priority_even_when_other_waves_also_have_logs(
        self, tmp_path
    ):
        """deliver/ is the fast path; other waves present don't matter."""
        project_id = "mixed-feature"
        for wave in ("deliver", "bugfix"):
            wave_dir = tmp_path / "docs" / "feature" / project_id / wave
            wave_dir.mkdir(parents=True)
            (wave_dir / "execution-log.json").write_text("{}")

        result = resolve_execution_log_path(
            project_id, base=tmp_path / "docs" / "feature"
        )

        expected = (
            tmp_path
            / "docs"
            / "feature"
            / project_id
            / "deliver"
            / "execution-log.json"
        )
        assert result == expected


# ---------------------------------------------------------------------------
# Hook-level integration tests: subagent_stop with wave-specific log paths
# ---------------------------------------------------------------------------


def _setup_git_repo(
    tmp_path, step_id: str = "01-01", feature_id: str | None = None
) -> None:
    """Initialize a throwaway git repo with a commit carrying Step-Id (+ optional Task-Id) trailers.

    SF parity port (step 01-01): when the SubagentStopService receives a
    non-empty ``project_id`` in context, it passes ``feature_id_filter`` to
    the verifier and AND-semantics requires a ``Task-Id:`` trailer too. Tests
    invoking the hook with a real project_id MUST pass ``feature_id`` here.
    """
    sp.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    sp.run(
        ["git", "config", "user.email", "t@t.com"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    sp.run(["git", "config", "user.name", "T"], cwd=str(tmp_path), capture_output=True)
    sp.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    body = f"Step-Id: {step_id}"
    if feature_id is not None:
        body += f"\nTask-Id: {feature_id}"
    sp.run(
        ["git", "commit", "--allow-empty", "-m", f"feat: step\n\n{body}"],
        cwd=str(tmp_path),
        capture_output=True,
    )


class TestSubagentStopWithWaveAgnosticLogs:
    """Hook-level integration: DES agent with non-deliver wave log is allowed.

    Test Budget: 2 behaviors (bugfix wave, design wave) x 2 = 4 max. Using 2.
    """

    def test_subagent_stop_succeeds_for_bugfix_mode_feature(
        self, tmp_path, monkeypatch
    ):
        """Behavior 5: bugfix/ log found via glob → stop hook allows."""
        project_id = "fix-opencode-test-isolation-p0"
        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            f"<!-- DES-PROJECT-ID : {project_id} -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            "Execute step"
        )
        transcript = _make_transcript(tmp_path, prompt)

        # Log lives in bugfix/, not deliver/
        bugfix_dir = tmp_path / "docs" / "feature" / project_id / "bugfix"
        bugfix_dir.mkdir(parents=True)
        (bugfix_dir / "execution-log.json").write_text(_complete_exec_log(project_id))

        _setup_git_repo(tmp_path, feature_id=project_id)

        hook_input = _make_hook_input(transcript, str(tmp_path))
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(hook_input))
        captured = []
        monkeypatch.setattr("builtins.print", captured.append)

        exit_code = handle_subagent_stop()

        assert exit_code == 0
        assert len(captured) == 0, (
            f"Allow path should produce no stdout. Got: {captured}"
        )

    def test_subagent_stop_succeeds_for_design_mode_feature(
        self, tmp_path, monkeypatch
    ):
        """Behavior 6: design/ log found via glob → stop hook allows."""
        project_id = "nwave-doctor"
        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            f"<!-- DES-PROJECT-ID : {project_id} -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            "Execute step"
        )
        transcript = _make_transcript(tmp_path, prompt)

        # Log lives in design/, not deliver/
        design_dir = tmp_path / "docs" / "feature" / project_id / "design"
        design_dir.mkdir(parents=True)
        (design_dir / "execution-log.json").write_text(_complete_exec_log(project_id))

        _setup_git_repo(tmp_path, feature_id=project_id)

        hook_input = _make_hook_input(transcript, str(tmp_path))
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(hook_input))
        captured = []
        monkeypatch.setattr("builtins.print", captured.append)

        exit_code = handle_subagent_stop()

        assert exit_code == 0
        assert len(captured) == 0, (
            f"Allow path should produce no stdout. Got: {captured}"
        )
