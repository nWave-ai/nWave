"""Unit tests for hook adapter resilience (UT-14 through UT-17).

Tests resilience fixes:
- 9a: Empty stdin → exit 0 (allow passthrough) for both PreToolUse and SubagentStop
- 9c: Missing transcript → None with no HOOK_TRANSCRIPT_ERROR
- task_start_time read from des-task-active signal
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


def _invoke_hook(hook_type: str, stdin_data: str) -> tuple[int, dict]:
    """Invoke hook adapter as subprocess, matching Claude Code protocol."""
    env = os.environ.copy()
    project_root = str(Path(__file__).parent.parent.parent.parent.parent)
    src_path = str(Path(project_root) / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "des.adapters.drivers.hooks.claude_code_hook_adapter",
            hook_type,
        ],
        input=stdin_data,
        capture_output=True,
        text=True,
        env=env,
    )
    response = json.loads(proc.stdout) if proc.stdout.strip() else {}
    return proc.returncode, response


class TestEmptyStdinResilience:
    """UT-14/UT-15: Empty stdin produces exit 0 allow for both hook types."""

    def test_empty_stdin_pre_tool_use_exits_0(self) -> None:
        """UT-14: PreToolUse with empty stdin exits 0 with allow."""
        exit_code, response = _invoke_hook("pre-tool-use", "")
        assert exit_code == 0
        assert response.get("decision") == "allow"

    def test_empty_stdin_subagent_stop_exits_0(self) -> None:
        """UT-15: SubagentStop with empty stdin exits 0 with allow."""
        exit_code, response = _invoke_hook("subagent-stop", "")
        assert exit_code == 0
        assert response.get("decision") == "allow"

    def test_whitespace_only_stdin_pre_tool_use_exits_0(self) -> None:
        """PreToolUse with whitespace-only stdin exits 0."""
        exit_code, response = _invoke_hook("pre-tool-use", "   \n  ")
        assert exit_code == 0
        assert response.get("decision") == "allow"

    def test_whitespace_only_stdin_subagent_stop_exits_0(self) -> None:
        """SubagentStop with whitespace-only stdin exits 0."""
        exit_code, response = _invoke_hook("subagent-stop", "   \n  ")
        assert exit_code == 0
        assert response.get("decision") == "allow"


class TestMissingTranscriptResilience:
    """UT-16: Missing transcript file returns None without HOOK_TRANSCRIPT_ERROR."""

    def test_missing_transcript_returns_none(self, tmp_path: Path) -> None:
        """UT-16: Non-existent transcript path returns None silently."""
        from des.adapters.drivers.hooks.claude_code_hook_adapter import (
            extract_des_context_from_transcript,
        )

        result = extract_des_context_from_transcript(
            str(tmp_path / "nonexistent-transcript.jsonl")
        )
        assert result is None


class TestTaskStartTimeFromSignal:
    """UT-17: task_start_time is read from des-task-active signal file."""

    def test_task_start_time_read_from_namespaced_signal(self, tmp_path: Path) -> None:
        """UT-17: _read_des_task_signal reads from namespaced signal file."""
        from des.adapters.drivers.hooks.claude_code_hook_adapter import (
            _read_des_task_signal,
        )

        # Create a namespaced signal file
        signal_dir = tmp_path / ".nwave" / "des"
        signal_dir.mkdir(parents=True)
        signal_file = signal_dir / "des-task-active-my-project--01-03"
        signal_data = {
            "step_id": "01-03",
            "project_id": "my-project",
            "created_at": "2026-02-10T14:30:00+00:00",
        }
        signal_file.write_text(json.dumps(signal_data))

        with patch(
            "des.adapters.drivers.hooks.claude_code_hook_adapter.DES_SESSION_DIR",
            signal_dir,
        ):
            result = _read_des_task_signal(project_id="my-project", step_id="01-03")

        assert result is not None
        assert result["created_at"] == "2026-02-10T14:30:00+00:00"
        assert result["step_id"] == "01-03"
        assert result["project_id"] == "my-project"

    def test_fallback_to_legacy_singleton(self, tmp_path: Path) -> None:
        """_read_des_task_signal falls back to legacy singleton when no namespaced file."""
        from des.adapters.drivers.hooks.claude_code_hook_adapter import (
            _read_des_task_signal,
        )

        signal_dir = tmp_path / ".nwave" / "des"
        signal_dir.mkdir(parents=True)
        # Only legacy singleton exists (no namespaced file)
        legacy_file = signal_dir / "des-task-active"
        legacy_data = {
            "step_id": "01-03",
            "created_at": "2026-02-10T14:30:00+00:00",
        }
        legacy_file.write_text(json.dumps(legacy_data))

        with (
            patch(
                "des.adapters.drivers.hooks.claude_code_hook_adapter.DES_SESSION_DIR",
                signal_dir,
            ),
            patch(
                "des.adapters.drivers.hooks.claude_code_hook_adapter.DES_TASK_ACTIVE_FILE",
                legacy_file,
            ),
        ):
            result = _read_des_task_signal(project_id="my-project", step_id="01-03")

        assert result is not None
        assert result["created_at"] == "2026-02-10T14:30:00+00:00"

    def test_missing_signal_returns_none(self) -> None:
        """_read_des_task_signal returns None when no signal file exists."""
        from des.adapters.drivers.hooks.claude_code_hook_adapter import (
            _read_des_task_signal,
        )

        nonexistent_dir = Path("/tmp/nonexistent-des-dir-test")
        nonexistent = Path("/tmp/nonexistent-des-task-active-test")
        with (
            patch(
                "des.adapters.drivers.hooks.claude_code_hook_adapter.DES_SESSION_DIR",
                nonexistent_dir,
            ),
            patch(
                "des.adapters.drivers.hooks.claude_code_hook_adapter.DES_TASK_ACTIVE_FILE",
                nonexistent,
            ),
        ):
            result = _read_des_task_signal(project_id="my-project", step_id="01-03")

        assert result is None
