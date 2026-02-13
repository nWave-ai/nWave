"""Tests for SubagentStop hook protocol translation.

The SubagentStop hook receives Claude Code's protocol:
    {"agent_id", "agent_type", "agent_transcript_path", "cwd", "session_id", ...}

NOT the custom DES fields that SubagentStopService expects:
    {"executionLogPath", "projectId", "stepId"}

The adapter must:
1. Read the agent transcript to find the original Task prompt
2. Extract DES markers (project_id, step_id) via DesMarkerParser
3. Non-DES agents (no markers) -> allow passthrough
4. DES agents -> derive execution-log path and validate via SubagentStopService
"""

import json
import os

from des.adapters.drivers.hooks.claude_code_hook_adapter import (
    extract_des_context_from_transcript,
    handle_subagent_stop,
)


def _make_transcript(tmp_dir: str, prompt: str) -> str:
    """Create a minimal JSONL transcript with a user message containing the prompt."""
    transcript_path = os.path.join(tmp_dir, "agent-test.jsonl")
    user_msg = {
        "type": "user",
        "message": {"role": "user", "content": prompt},
        "uuid": "test-uuid",
        "timestamp": "2026-02-06T21:00:00Z",
    }
    with open(transcript_path, "w") as f:
        f.write(json.dumps(user_msg) + "\n")
    return transcript_path


class TestExtractDesContextFromTranscript:
    """Tests for extracting DES markers from agent transcript."""

    def test_extracts_project_id_and_step_id_from_des_markers(self, tmp_path):
        prompt = (
            "<!-- DES-VALIDATION: required -->\n"
            "<!-- DES-PROJECT-ID: audit-log-refactor -->\n"
            "<!-- DES-STEP-ID: 02-01 -->\n"
            "# DES_METADATA\ntest"
        )
        transcript = _make_transcript(str(tmp_path), prompt)

        context = extract_des_context_from_transcript(transcript)

        assert context is not None
        assert context["project_id"] == "audit-log-refactor"
        assert context["step_id"] == "02-01"

    def test_returns_none_for_non_des_transcript(self, tmp_path):
        prompt = "Find all Python files in the codebase"
        transcript = _make_transcript(str(tmp_path), prompt)

        context = extract_des_context_from_transcript(transcript)

        assert context is None

    def test_returns_none_for_missing_transcript_file(self):
        context = extract_des_context_from_transcript("/nonexistent/path.jsonl")

        assert context is None

    def test_returns_none_for_empty_transcript(self, tmp_path):
        transcript_path = str(tmp_path / "empty.jsonl")
        with open(transcript_path, "w") as f:
            f.write("")

        context = extract_des_context_from_transcript(transcript_path)

        assert context is None

    def test_returns_none_when_project_id_marker_missing(self, tmp_path):
        prompt = (
            "<!-- DES-VALIDATION: required -->\n"
            "<!-- DES-STEP-ID: 02-01 -->\n"
            "# DES_METADATA\ntest"
        )
        transcript = _make_transcript(str(tmp_path), prompt)

        context = extract_des_context_from_transcript(transcript)

        assert context is None

    def test_returns_none_when_step_id_marker_missing(self, tmp_path):
        prompt = (
            "<!-- DES-VALIDATION: required -->\n"
            "<!-- DES-PROJECT-ID: audit-log-refactor -->\n"
            "# DES_METADATA\ntest"
        )
        transcript = _make_transcript(str(tmp_path), prompt)

        context = extract_des_context_from_transcript(transcript)

        assert context is None

    def test_handles_content_as_list_of_blocks(self, tmp_path):
        """Claude Code sometimes sends content as list of text blocks."""
        transcript_path = str(tmp_path / "agent.jsonl")
        user_msg = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "<!-- DES-VALIDATION: required -->\n"
                            "<!-- DES-PROJECT-ID: my-project -->\n"
                            "<!-- DES-STEP-ID: 01-01 -->\n"
                            "Do something"
                        ),
                    }
                ],
            },
            "uuid": "test",
            "timestamp": "2026-02-06T21:00:00Z",
        }
        with open(transcript_path, "w") as f:
            f.write(json.dumps(user_msg) + "\n")

        context = extract_des_context_from_transcript(transcript_path)

        assert context is not None
        assert context["project_id"] == "my-project"
        assert context["step_id"] == "01-01"


class TestSubagentStopWithClaudeCodeProtocol:
    """Integration tests: handle_subagent_stop() with Claude Code's actual protocol."""

    def _make_hook_input(self, agent_transcript_path: str, cwd: str) -> str:
        """Build Claude Code SubagentStop protocol JSON."""
        return json.dumps(
            {
                "session_id": "test-session",
                "hook_event_name": "SubagentStop",
                "agent_id": "test-agent-123",
                "agent_type": "software-crafter",
                "agent_transcript_path": agent_transcript_path,
                "stop_hook_active": False,
                "cwd": cwd,
                "transcript_path": "/tmp/session.jsonl",
                "permission_mode": "default",
            }
        )

    def test_non_des_subagent_allowed(self, tmp_path, monkeypatch):
        """Non-DES agent (no markers) should be allowed through."""
        prompt = "Find all Python files"
        transcript = _make_transcript(str(tmp_path), prompt)
        hook_input = self._make_hook_input(transcript, str(tmp_path))

        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(hook_input))

        captured = []
        monkeypatch.setattr("builtins.print", captured.append)

        exit_code = handle_subagent_stop()

        assert exit_code == 0
        response = json.loads(captured[0])
        assert response["decision"] == "allow"

    def test_des_subagent_with_valid_execution_log(self, tmp_path, monkeypatch):
        """DES agent with complete execution log should be allowed."""
        import subprocess as sp

        prompt = (
            "<!-- DES-VALIDATION: required -->\n"
            "<!-- DES-PROJECT-ID: test-project -->\n"
            "<!-- DES-STEP-ID: 01-01 -->\n"
            "Execute step"
        )
        transcript = _make_transcript(str(tmp_path), prompt)

        # Create execution log at the expected path
        feature_dir = tmp_path / "docs" / "feature" / "test-project"
        feature_dir.mkdir(parents=True)
        exec_log = feature_dir / "execution-log.yaml"
        exec_log.write_text(
            'project_id: "test-project"\n'
            "events:\n"
            '  - "01-01|PREPARE|EXECUTED|PASS|2026-02-06T10:00:00Z"\n'
            '  - "01-01|RED_ACCEPTANCE|EXECUTED|PASS|2026-02-06T10:05:00Z"\n'
            '  - "01-01|RED_UNIT|EXECUTED|PASS|2026-02-06T10:10:00Z"\n'
            '  - "01-01|GREEN|EXECUTED|PASS|2026-02-06T10:20:00Z"\n'
            '  - "01-01|REVIEW|EXECUTED|PASS|2026-02-06T10:30:00Z"\n'
            '  - "01-01|REFACTOR_CONTINUOUS|SKIPPED|CHECKPOINT_PENDING: Minimal|2026-02-06T10:35:00Z"\n'
            '  - "01-01|COMMIT|EXECUTED|PASS|2026-02-06T11:00:00Z"\n'
        )

        # Initialize git repo and create a commit with Step-ID trailer
        # (required because cwd is now passed for commit verification)
        sp.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
        sp.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        sp.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        sp.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        sp.run(
            ["git", "commit", "-m", "feat: implement step\n\nStep-ID: 01-01"],
            cwd=str(tmp_path),
            capture_output=True,
        )

        hook_input = self._make_hook_input(transcript, str(tmp_path))
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(hook_input))

        captured = []
        monkeypatch.setattr("builtins.print", captured.append)

        exit_code = handle_subagent_stop()

        assert exit_code == 0
        response = json.loads(captured[0])
        assert response["decision"] == "allow"

    def test_des_subagent_with_incomplete_execution_log_blocked(
        self, tmp_path, monkeypatch
    ):
        """DES agent with missing phases should be blocked."""
        prompt = (
            "<!-- DES-VALIDATION: required -->\n"
            "<!-- DES-PROJECT-ID: test-project -->\n"
            "<!-- DES-STEP-ID: 01-01 -->\n"
            "Execute step"
        )
        transcript = _make_transcript(str(tmp_path), prompt)

        # Create execution log with only 2 phases
        feature_dir = tmp_path / "docs" / "feature" / "test-project"
        feature_dir.mkdir(parents=True)
        exec_log = feature_dir / "execution-log.yaml"
        exec_log.write_text(
            'project_id: "test-project"\n'
            "events:\n"
            '  - "01-01|PREPARE|EXECUTED|PASS|2026-02-06T10:00:00Z"\n'
            '  - "01-01|RED_ACCEPTANCE|EXECUTED|PASS|2026-02-06T10:05:00Z"\n'
        )

        hook_input = self._make_hook_input(transcript, str(tmp_path))
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(hook_input))

        captured = []
        monkeypatch.setattr("builtins.print", captured.append)

        exit_code = handle_subagent_stop()

        # Exit 0 so Claude Code processes JSON (exit 2 ignores stdout)
        assert exit_code == 0
        response = json.loads(captured[0])
        assert response["decision"] == "block"
        assert "Missing phases" in response["reason"]

    def test_des_subagent_missing_execution_log_blocked(self, tmp_path, monkeypatch):
        """DES agent where execution-log.yaml doesn't exist should be blocked."""
        prompt = (
            "<!-- DES-VALIDATION: required -->\n"
            "<!-- DES-PROJECT-ID: no-such-project -->\n"
            "<!-- DES-STEP-ID: 01-01 -->\n"
            "Execute step"
        )
        transcript = _make_transcript(str(tmp_path), prompt)

        hook_input = self._make_hook_input(transcript, str(tmp_path))
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(hook_input))

        captured = []
        monkeypatch.setattr("builtins.print", captured.append)

        exit_code = handle_subagent_stop()

        # Exit 0 so Claude Code processes JSON (exit 2 ignores stdout)
        assert exit_code == 0
        response = json.loads(captured[0])
        assert response["decision"] == "block"
        assert "not found" in response["reason"].lower()
