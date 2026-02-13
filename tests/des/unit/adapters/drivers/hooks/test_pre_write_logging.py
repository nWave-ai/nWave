"""Tests for decision logging in handle_pre_write.

handle_pre_write emits HOOK_PRE_WRITE_ALLOWED or HOOK_PRE_WRITE_BLOCKED audit
events after the SessionGuardPolicy check, and enriches HOOK_INVOKED with
input_summary including file_path, session_active, and des_task_active.

Tests exercise through the handle_pre_write driving port and assert at the
AuditLogWriter driven port boundary.

Test Budget: 5 distinct behaviors x 2 = 10 max. Using 5 tests.

Behaviors:
1. HOOK_INVOKED enriched with session_active and des_task_active in input_summary
2. HOOK_PRE_WRITE_ALLOWED emitted when session not active (reason='no_session')
3. HOOK_PRE_WRITE_ALLOWED emitted for allowed paths
4. HOOK_PRE_WRITE_BLOCKED emitted when guard blocks the write
5. Exception in decision logging does not break handler (fail-open preserved)
"""

import io
import json
from unittest.mock import patch

import pytest

from des.ports.driven_ports.audit_log_writer import AuditEvent


def _make_capturing_writer(events: list[AuditEvent]):
    """Create a mock AuditLogWriter that appends events to the given list."""
    from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter

    class CapturingWriter(NullAuditLogWriter):
        def log_event(self, event: AuditEvent) -> None:
            events.append(event)

    return CapturingWriter()


def _build_pre_write_stdin(file_path: str = "/tmp/test.py") -> str:
    """Build Write tool input JSON."""
    return json.dumps({"tool_name": "Write", "tool_input": {"file_path": file_path}})


# --- Test 1: HOOK_INVOKED enriched with session_active and des_task_active ---


def test_hook_invoked_includes_session_state_in_input_summary(monkeypatch, tmp_path):
    """HOOK_INVOKED input_summary includes file_path, session_active, and des_task_active."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    # Set up deliver session as active, DES task as inactive
    session_file = tmp_path / "deliver-session.json"
    session_file.write_text("{}")
    monkeypatch.setattr(adapter, "DES_DELIVER_SESSION_FILE", session_file)
    monkeypatch.setattr(adapter, "DES_TASK_ACTIVE_FILE", tmp_path / "nonexistent")

    monkeypatch.setattr(
        "sys.stdin", io.StringIO(_build_pre_write_stdin("/tmp/safe.txt"))
    )
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        adapter.handle_pre_write()

    invoked_events = [e for e in events if e.event_type == "HOOK_INVOKED"]
    assert len(invoked_events) >= 1, "Expected at least one HOOK_INVOKED event"

    summary = invoked_events[0].data.get("input_summary", {})
    assert "file_path" in summary, "input_summary must include file_path"
    assert "session_active" in summary, "input_summary must include session_active"
    assert "des_task_active" in summary, "input_summary must include des_task_active"
    assert summary["session_active"] is True
    assert summary["des_task_active"] is False


# --- Test 2: HOOK_PRE_WRITE_ALLOWED emitted when no session active ---


def test_allowed_event_emitted_when_no_session(monkeypatch, tmp_path):
    """HOOK_PRE_WRITE_ALLOWED emitted with reason='no_session' when no deliver session."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    # No session file, no DES task
    monkeypatch.setattr(adapter, "DES_DELIVER_SESSION_FILE", tmp_path / "nonexistent")
    monkeypatch.setattr(adapter, "DES_TASK_ACTIVE_FILE", tmp_path / "nonexistent")

    monkeypatch.setattr("sys.stdin", io.StringIO(_build_pre_write_stdin("src/main.py")))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        exit_code = adapter.handle_pre_write()

    assert exit_code == 0

    allowed_events = [e for e in events if e.event_type == "HOOK_PRE_WRITE_ALLOWED"]
    assert len(allowed_events) == 1, (
        f"Expected one HOOK_PRE_WRITE_ALLOWED event, got {len(allowed_events)}. "
        f"All events: {[e.event_type for e in events]}"
    )

    event = allowed_events[0]
    assert event.data["file_path"] == "src/main.py"
    assert event.data["reason"] == "no_session"


# --- Test 3: HOOK_PRE_WRITE_ALLOWED emitted for allowed/unprotected paths ---


@pytest.mark.parametrize(
    "file_path,scenario",
    [
        ("docs/feature/des-obs/plan.md", "orchestration path always allowed"),
        ("/tmp/safe.txt", "unprotected path not blocked"),
    ],
    ids=["orchestration_path", "unprotected_path"],
)
def test_allowed_event_emitted_for_non_blocked_paths(
    file_path, scenario, monkeypatch, tmp_path
):
    """HOOK_PRE_WRITE_ALLOWED emitted for paths the policy allows during active session."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    # Session active but no DES task
    session_file = tmp_path / "deliver-session.json"
    session_file.write_text("{}")
    monkeypatch.setattr(adapter, "DES_DELIVER_SESSION_FILE", session_file)
    monkeypatch.setattr(adapter, "DES_TASK_ACTIVE_FILE", tmp_path / "nonexistent")

    monkeypatch.setattr("sys.stdin", io.StringIO(_build_pre_write_stdin(file_path)))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        exit_code = adapter.handle_pre_write()

    assert exit_code == 0

    allowed_events = [e for e in events if e.event_type == "HOOK_PRE_WRITE_ALLOWED"]
    assert len(allowed_events) == 1, (
        f"Expected HOOK_PRE_WRITE_ALLOWED for '{scenario}', "
        f"got events: {[e.event_type for e in events]}"
    )
    assert allowed_events[0].data["file_path"] == file_path


# --- Test 4: HOOK_PRE_WRITE_BLOCKED emitted when guard blocks ---


def test_blocked_event_emitted_when_guard_blocks(monkeypatch, tmp_path):
    """HOOK_PRE_WRITE_BLOCKED emitted with file_path and reason when source write blocked."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    # Session active, no DES task, writing to protected path
    session_file = tmp_path / "deliver-session.json"
    session_file.write_text("{}")
    monkeypatch.setattr(adapter, "DES_DELIVER_SESSION_FILE", session_file)
    monkeypatch.setattr(adapter, "DES_TASK_ACTIVE_FILE", tmp_path / "nonexistent")

    monkeypatch.setattr(
        "sys.stdin", io.StringIO(_build_pre_write_stdin("src/des/main.py"))
    )
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        exit_code = adapter.handle_pre_write()

    assert exit_code == 2

    blocked_events = [e for e in events if e.event_type == "HOOK_PRE_WRITE_BLOCKED"]
    assert len(blocked_events) == 1, (
        f"Expected one HOOK_PRE_WRITE_BLOCKED event, got {len(blocked_events)}. "
        f"All events: {[e.event_type for e in events]}"
    )

    event = blocked_events[0]
    assert event.data["file_path"] == "src/des/main.py"
    assert "reason" in event.data
    assert len(event.data["reason"]) > 0, "Blocked reason must not be empty"
    assert "hook_id" in event.data, "HOOK_PRE_WRITE_BLOCKED must include hook_id"


# --- Test 5: Exception in decision logging does not break fail-open behavior ---


def test_logging_exception_preserves_fail_open_behavior(monkeypatch, tmp_path):
    """When audit logging raises, handle_pre_write still returns allow (fail-open)."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    call_count = 0

    class ExplodingWriter:
        def log_event(self, event):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Audit writer exploded")

    # No session = allow path, but logging will throw
    monkeypatch.setattr(adapter, "DES_DELIVER_SESSION_FILE", tmp_path / "nonexistent")
    monkeypatch.setattr(adapter, "DES_TASK_ACTIVE_FILE", tmp_path / "nonexistent")

    monkeypatch.setattr("sys.stdin", io.StringIO(_build_pre_write_stdin("src/app.py")))
    printed = []
    monkeypatch.setattr("builtins.print", lambda *a, **kw: printed.append(a))

    with patch.object(adapter, "_create_audit_writer", return_value=ExplodingWriter()):
        exit_code = adapter.handle_pre_write()

    # Must still allow (fail-open)
    assert exit_code == 0
    # Verify it attempted to log (writer was called)
    assert call_count > 0, "Expected audit writer to be called even though it raised"
    # Verify it printed allow response
    assert any('"allow"' in str(p) for p in printed), (
        "Expected allow decision in output"
    )
