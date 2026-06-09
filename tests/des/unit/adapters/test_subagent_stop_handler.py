"""Regression tests for DES-PROJECT-ROOT marker honored by subagent_stop_handler.

Outcome anchor: DISCUSS "orchestrator dispatching a crafter against a worktree
sees correct audit-trail validation, not stale-master false-positive halts."

Rex RCA - F-DES-WORKTREE-EXECUTION-LOG-RESOLUTION (audit-2026-05-19.log:270,365).
Hook resolver previously read execution-log from hook_input["cwd"] only - when
the orchestrator's CWD is master while the crafter executes on a worktree, the
resolver picks the wrong execution-log.

CONTRACT_SHAPE: bounded-change
Universe: chosen execution_log_path emitted to SubagentStopService + HOOK_INVOKED
audit-event payload (resolved execution_log_path, project_root_marker).
"""

from __future__ import annotations

import json
import subprocess as sp


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


def _complete_exec_log(project_id: str, step_id: str = "01-01") -> str:
    return json.dumps(
        {
            "project_id": project_id,
            "events": [
                f"{step_id}|PREPARE|EXECUTED|PASS|2026-05-19T10:00:00Z",
                f"{step_id}|RED_ACCEPTANCE|EXECUTED|PASS|2026-05-19T10:05:00Z",
                f"{step_id}|RED_UNIT|EXECUTED|PASS|2026-05-19T10:10:00Z",
                f"{step_id}|GREEN|EXECUTED|PASS|2026-05-19T10:20:00Z",
                f"{step_id}|REVIEW|EXECUTED|PASS|2026-05-19T10:30:00Z",
                f"{step_id}|REFACTOR_CONTINUOUS|SKIPPED|CHECKPOINT_PENDING: Minimal|2026-05-19T10:35:00Z",
                f"{step_id}|COMMIT|EXECUTED|PASS|2026-05-19T11:00:00Z",
            ],
        },
        indent=2,
    )


def _setup_git_repo(repo_dir, step_id="01-01", feature_id=None):
    sp.run(["git", "init"], cwd=str(repo_dir), capture_output=True)
    sp.run(
        ["git", "config", "user.email", "t@t.com"],
        cwd=str(repo_dir),
        capture_output=True,
    )
    sp.run(["git", "config", "user.name", "T"], cwd=str(repo_dir), capture_output=True)
    body = f"Step-Id: {step_id}"
    if feature_id is not None:
        body += f"\nTask-Id: {feature_id}"
    sp.run(
        ["git", "commit", "--allow-empty", "-m", f"feat: step\n\n{body}"],
        cwd=str(repo_dir),
        capture_output=True,
    )


def _setup_worktree(master_repo, worktree_dir, branch="feature-branch"):
    sp.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_dir), "HEAD"],
        cwd=str(master_repo),
        capture_output=True,
    )


class TestProjectRootMarkerHonored:
    """Behavior: hook resolver prefers marker over hook_input['cwd'].

    Test Budget: 4 behaviors x 2 = 8 max. Using 4 focused tests.
    """

    def test_marker_pointing_to_valid_worktree_overrides_cwd(
        self, tmp_path, monkeypatch
    ):
        """Scenario (a): marker carries worktree path; execution-log resolved there."""
        from des.adapters.drivers.hooks.subagent_stop_handler import (
            handle_subagent_stop,
        )

        master = tmp_path / "master"
        master.mkdir()
        _setup_git_repo(master)

        wt = tmp_path / "wt"
        _setup_worktree(master, wt)
        project_id = "fix-feat"
        _setup_git_repo(wt, feature_id=project_id)

        deliver_dir = wt / "docs" / "feature" / project_id / "deliver"
        deliver_dir.mkdir(parents=True)
        (deliver_dir / "execution-log.json").write_text(_complete_exec_log(project_id))

        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            f"<!-- DES-PROJECT-ID : {project_id} -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            f"<!-- DES-PROJECT-ROOT : {wt} -->\n"
            "Execute step"
        )
        transcript = _make_transcript(tmp_path, prompt)

        hook_input = _make_hook_input(transcript, str(master))
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(hook_input))
        captured = []
        monkeypatch.setattr("builtins.print", captured.append)

        exit_code = handle_subagent_stop()

        assert exit_code == 0, f"expected allow, got stdout: {captured}"
        assert len(captured) == 0, (
            f"Allow path should produce no output. Got: {captured}"
        )

    def test_marker_absent_falls_back_to_cwd_backward_compat(
        self, tmp_path, monkeypatch
    ):
        """Scenario (b): no marker means existing cwd-based behaviour preserved."""
        from des.adapters.drivers.hooks.subagent_stop_handler import (
            handle_subagent_stop,
        )

        project_id = "fix-feat-no-marker"
        deliver_dir = tmp_path / "docs" / "feature" / project_id / "deliver"
        deliver_dir.mkdir(parents=True)
        (deliver_dir / "execution-log.json").write_text(_complete_exec_log(project_id))
        _setup_git_repo(tmp_path, feature_id=project_id)

        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            f"<!-- DES-PROJECT-ID : {project_id} -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            "Execute step (no DES-PROJECT-ROOT)"
        )
        transcript = _make_transcript(tmp_path, prompt)
        hook_input = _make_hook_input(transcript, str(tmp_path))
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(hook_input))
        captured = []
        monkeypatch.setattr("builtins.print", captured.append)

        exit_code = handle_subagent_stop()

        assert exit_code == 0
        assert len(captured) == 0

    def test_marker_pointing_outside_repo_falls_back_to_cwd(
        self, tmp_path, monkeypatch
    ):
        """Scenario (c): marker outside repo means validation rejects, fall back to cwd."""
        from des.adapters.drivers.hooks.subagent_stop_handler import (
            handle_subagent_stop,
        )

        cwd_repo = tmp_path / "cwd_repo"
        cwd_repo.mkdir()
        unrelated = tmp_path / "unrelated_repo"
        unrelated.mkdir()
        _setup_git_repo(unrelated)

        project_id = "fix-feat-bad-marker"
        deliver_dir = cwd_repo / "docs" / "feature" / project_id / "deliver"
        deliver_dir.mkdir(parents=True)
        (deliver_dir / "execution-log.json").write_text(_complete_exec_log(project_id))
        _setup_git_repo(cwd_repo, feature_id=project_id)

        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            f"<!-- DES-PROJECT-ID : {project_id} -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            f"<!-- DES-PROJECT-ROOT : {unrelated} -->\n"
            "Execute step"
        )
        transcript = _make_transcript(tmp_path, prompt)
        hook_input = _make_hook_input(transcript, str(cwd_repo))
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(hook_input))
        captured = []
        monkeypatch.setattr("builtins.print", captured.append)

        exit_code = handle_subagent_stop()

        assert exit_code == 0
        assert len(captured) == 0, (
            f"Fallback to cwd path should allow (log complete). Got: {captured}"
        )

    def test_marker_pointing_to_sibling_worktree_allowed(self, tmp_path, monkeypatch):
        """Scenario (d): marker = sibling worktree of cwd's repo means allow."""
        from des.adapters.drivers.hooks.subagent_stop_handler import (
            handle_subagent_stop,
        )

        master = tmp_path / "master"
        master.mkdir()
        _setup_git_repo(master)

        wt_a = tmp_path / "wt_a"
        _setup_worktree(master, wt_a, branch="branch-a")
        wt_b = tmp_path / "wt_b"
        _setup_worktree(master, wt_b, branch="branch-b")

        project_id = "fix-feat-sibling"
        _setup_git_repo(wt_b, feature_id=project_id)
        deliver_dir = wt_b / "docs" / "feature" / project_id / "deliver"
        deliver_dir.mkdir(parents=True)
        (deliver_dir / "execution-log.json").write_text(_complete_exec_log(project_id))

        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            f"<!-- DES-PROJECT-ID : {project_id} -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            f"<!-- DES-PROJECT-ROOT : {wt_b} -->\n"
            "Execute step"
        )
        transcript = _make_transcript(tmp_path, prompt)
        hook_input = _make_hook_input(transcript, str(wt_a))
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(hook_input))
        captured = []
        monkeypatch.setattr("builtins.print", captured.append)

        exit_code = handle_subagent_stop()

        assert exit_code == 0, f"expected allow, got stdout: {captured}"
        assert len(captured) == 0


class TestProjectRootValidator:
    """Unit tests for the project-root validation helper.

    Test Budget: 5 behaviors x 2 = 10 max. Using 5 tests.
    """

    def test_returns_path_for_valid_worktree_of_same_repo(self, tmp_path):
        from des.adapters.drivers.hooks.project_root_validator import (
            validate_project_root,
        )

        master = tmp_path / "master"
        master.mkdir()
        _setup_git_repo(master)
        wt = tmp_path / "wt"
        _setup_worktree(master, wt)

        result = validate_project_root(str(wt), str(master))

        assert result is not None
        assert result.resolve() == wt.resolve()

    def test_returns_none_for_relative_path(self, tmp_path):
        from des.adapters.drivers.hooks.project_root_validator import (
            validate_project_root,
        )

        result = validate_project_root("./relative/path", str(tmp_path))

        assert result is None

    def test_returns_none_for_nonexistent_path(self, tmp_path):
        from des.adapters.drivers.hooks.project_root_validator import (
            validate_project_root,
        )

        result = validate_project_root(str(tmp_path / "ghost"), str(tmp_path))

        assert result is None

    def test_returns_none_for_unrelated_repo(self, tmp_path):
        from des.adapters.drivers.hooks.project_root_validator import (
            validate_project_root,
        )

        cwd_repo = tmp_path / "cwd_repo"
        cwd_repo.mkdir()
        _setup_git_repo(cwd_repo)
        unrelated = tmp_path / "unrelated"
        unrelated.mkdir()
        _setup_git_repo(unrelated)

        result = validate_project_root(str(unrelated), str(cwd_repo))

        assert result is None

    def test_returns_none_for_non_git_directory(self, tmp_path):
        from des.adapters.drivers.hooks.project_root_validator import (
            validate_project_root,
        )

        cwd_repo = tmp_path / "cwd_repo"
        cwd_repo.mkdir()
        _setup_git_repo(cwd_repo)
        plain = tmp_path / "plain"
        plain.mkdir()

        result = validate_project_root(str(plain), str(cwd_repo))

        assert result is None


class TestHookInvokedAuditEnrichment:
    """HOOK_INVOKED summary must include resolved execution_log_path and
    (when present) DES-PROJECT-ROOT marker value.
    """

    def test_subagent_stop_audit_includes_execution_log_path_and_marker(
        self, tmp_path, monkeypatch
    ):
        from des.adapters.drivers.hooks import subagent_stop_handler as ssh

        master = tmp_path / "master"
        master.mkdir()
        _setup_git_repo(master)
        wt = tmp_path / "wt"
        _setup_worktree(master, wt)
        project_id = "fix-feat-audit"
        _setup_git_repo(wt, feature_id=project_id)
        deliver_dir = wt / "docs" / "feature" / project_id / "deliver"
        deliver_dir.mkdir(parents=True)
        exec_log = deliver_dir / "execution-log.json"
        exec_log.write_text(_complete_exec_log(project_id))

        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            f"<!-- DES-PROJECT-ID : {project_id} -->\n"
            "<!-- DES-STEP-ID : 01-01 -->\n"
            f"<!-- DES-PROJECT-ROOT : {wt} -->\n"
            "Execute step"
        )
        transcript = _make_transcript(tmp_path, prompt)
        hook_input = _make_hook_input(transcript, str(master))
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(hook_input))
        captured = []
        monkeypatch.setattr("builtins.print", captured.append)

        events: list[dict] = []
        orig_log = ssh.log_hook_invoked

        def _spy_log(name, data, hook_id=None):
            events.append({"name": name, "data": dict(data or {})})
            return orig_log(name, data, hook_id=hook_id)

        monkeypatch.setattr(ssh, "log_hook_invoked", _spy_log)

        exit_code = ssh.handle_subagent_stop()
        assert exit_code == 0

        matching = [
            ev for ev in events if ev["data"].get("execution_log_path") == str(exec_log)
        ]
        assert matching, (
            "Expected HOOK_INVOKED event with execution_log_path slot; "
            f"got events: {events}"
        )
        markers = [ev["data"].get("des_project_root_marker") for ev in matching]
        assert str(wt) in markers, (
            "Expected des_project_root_marker slot to carry marker value; "
            f"got markers: {markers}"
        )
