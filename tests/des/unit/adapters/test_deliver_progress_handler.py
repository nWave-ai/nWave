"""Regression tests for DES-PROJECT-ROOT marker honored by deliver_progress_handler.

Outcome anchor: DISCUSS "orchestrator dispatching crafter on worktree sees
correct progress tracking, not stale-master false-positive."

Rex RCA — F-DES-WORKTREE-EXECUTION-LOG-RESOLUTION. The deliver-progress hook
resolves roadmap.json + execution-log.json from `hook_input['cwd']` only; on
worktree dispatches that resolves to the wrong repo.

CONTRACT_SHAPE: bounded-change
Universe: resolved roadmap_path / exec_log_path used to read progress state.
"""

from __future__ import annotations

import json
import subprocess as sp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transcript(tmp_path, prompt: str) -> str:
    transcript_path = tmp_path / "agent.jsonl"
    user_msg = {
        "type": "user",
        "message": {"role": "user", "content": prompt},
        "uuid": "test-uuid",
        "timestamp": "2026-05-19T10:00:00Z",
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


def _git_init(path):
    sp.run(["git", "init"], cwd=str(path), capture_output=True)
    sp.run(
        ["git", "config", "user.email", "t@t.com"],
        cwd=str(path),
        capture_output=True,
    )
    sp.run(["git", "config", "user.name", "T"], cwd=str(path), capture_output=True)
    sp.run(
        ["git", "commit", "--allow-empty", "--no-verify", "-m", "chore: init"],
        cwd=str(path),
        capture_output=True,
    )


def _add_worktree(master, wt, branch="feat"):
    sp.run(
        ["git", "worktree", "add", "-b", branch, str(wt), "HEAD"],
        cwd=str(master),
        capture_output=True,
    )


def _seed_feature(repo_dir, project_id: str):
    """Create roadmap.json + execution-log.json under repo_dir for project_id."""
    deliver = repo_dir / "docs" / "feature" / project_id / "deliver"
    deliver.mkdir(parents=True)
    (deliver / "roadmap.json").write_text(
        json.dumps(
            {
                "roadmap": {"project_id": project_id, "total_steps": 1},
                "phases": [
                    {
                        "id": "01",
                        "steps": [{"id": "01-01"}],
                    }
                ],
            }
        )
    )
    (deliver / "execution-log.json").write_text(
        json.dumps({"project_id": project_id, "events": []})
    )
    return deliver


class TestDeliverProgressHandlerMarkerHonored:
    """Behavior: deliver_progress_handler resolves paths via marker when present.

    Test Budget: 4 behaviors x 2 = 8 max. Using 3 focused tests (a, b, c).
    """

    def test_marker_pointing_to_worktree_overrides_cwd(self, tmp_path):
        """Scenario (a): marker valid → progress file written under worktree."""
        from des.adapters.drivers.hooks.deliver_progress_handler import (
            handle_deliver_progress,
        )

        master = tmp_path / "master"
        master.mkdir()
        _git_init(master)
        wt = tmp_path / "wt"
        _add_worktree(master, wt)

        project_id = "fix-feat-prog"
        deliver_wt = _seed_feature(wt, project_id)
        # ALSO seed master to detect leakage — if handler reads master, the
        # progress file lands there
        deliver_master = _seed_feature(master, project_id)

        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            f"<!-- DES-PROJECT-ID : {project_id} -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            f"<!-- DES-PROJECT-ROOT : {wt} -->\n"
            "Execute step"
        )
        transcript = _make_transcript(tmp_path, prompt)

        import io
        import sys

        sys.stdin = io.StringIO(_make_hook_input(transcript, str(master)))
        try:
            rc = handle_deliver_progress()
        finally:
            sys.stdin = sys.__stdin__

        assert rc == 0
        # Progress file MUST land in worktree, not master
        assert (deliver_wt / ".develop-progress.json").exists(), (
            "Expected progress file under worktree (marker honored)"
        )
        assert not (deliver_master / ".develop-progress.json").exists(), (
            "Master progress file MUST NOT be written (marker overrides cwd)"
        )

    def test_marker_absent_falls_back_to_cwd(self, tmp_path):
        """Scenario (b): no marker → existing cwd behaviour preserved."""
        from des.adapters.drivers.hooks.deliver_progress_handler import (
            handle_deliver_progress,
        )

        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init(repo)
        project_id = "fix-feat-fallback"
        deliver = _seed_feature(repo, project_id)

        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            f"<!-- DES-PROJECT-ID : {project_id} -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            "Execute step (no marker)"
        )
        transcript = _make_transcript(tmp_path, prompt)

        import io
        import sys

        sys.stdin = io.StringIO(_make_hook_input(transcript, str(repo)))
        try:
            rc = handle_deliver_progress()
        finally:
            sys.stdin = sys.__stdin__

        assert rc == 0
        assert (deliver / ".develop-progress.json").exists()

    def test_marker_invalid_falls_back_to_cwd(self, tmp_path):
        """Scenario (c): marker outside repo → reject + cwd fallback."""
        from des.adapters.drivers.hooks.deliver_progress_handler import (
            handle_deliver_progress,
        )

        repo = tmp_path / "repo"
        repo.mkdir()
        _git_init(repo)
        unrelated = tmp_path / "unrelated"
        unrelated.mkdir()
        _git_init(unrelated)

        project_id = "fix-feat-invalid"
        deliver = _seed_feature(repo, project_id)

        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            f"<!-- DES-PROJECT-ID : {project_id} -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            f"<!-- DES-PROJECT-ROOT : {unrelated} -->\n"
            "Execute step"
        )
        transcript = _make_transcript(tmp_path, prompt)

        import io
        import sys

        sys.stdin = io.StringIO(_make_hook_input(transcript, str(repo)))
        try:
            rc = handle_deliver_progress()
        finally:
            sys.stdin = sys.__stdin__

        assert rc == 0
        # Invalid marker rejected → cwd fallback used → progress under cwd's repo
        assert (deliver / ".develop-progress.json").exists()
