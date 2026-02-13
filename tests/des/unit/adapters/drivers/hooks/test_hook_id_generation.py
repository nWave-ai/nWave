"""Tests for hook_id generation in claude_code_hook_adapter.

Each handler generates a UUID4 hook_id at entry and includes it in the
HOOK_INVOKED audit event. Tests exercise through the handler driving ports
and assert at the AuditLogWriter driven port boundary.

Acceptance criteria:
- hook_id is a valid UUID4 string
- hook_id is unique per handler invocation
- hook_id appears in HOOK_INVOKED event data under key 'hook_id'
- All four handlers generate hook_id
- _log_hook_invoked accepts optional hook_id (backward compatible: None omits field)
"""

import io
import json
import re
from unittest.mock import patch

import pytest

from des.ports.driven_ports.audit_log_writer import AuditEvent


UUID4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _make_capturing_writer(events: list[AuditEvent]):
    """Create a mock AuditLogWriter that appends events to the given list."""
    from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter

    class CapturingWriter(NullAuditLogWriter):
        def log_event(self, event: AuditEvent) -> None:
            events.append(event)

    return CapturingWriter()


# --- Test 1: All four handlers produce HOOK_INVOKED with valid UUID4 hook_id ---


def _build_pre_tool_use_stdin() -> str:
    return json.dumps(
        {
            "tool_name": "Task",
            "tool_input": {
                "prompt": "Do something",
                "max_turns": 15,
                "subagent_type": "code",
            },
        }
    )


def _build_subagent_stop_stdin() -> str:
    return json.dumps(
        {
            "session_id": "s1",
            "hook_event_name": "SubagentStop",
            "agent_id": "a1",
            "agent_type": "code",
            "cwd": "/tmp",
        }
    )


def _build_post_tool_use_stdin() -> str:
    return json.dumps({"tool_name": "Task", "tool_input": {"prompt": "done"}})


def _build_pre_write_stdin() -> str:
    return json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": "/tmp/test.py"}}
    )


@pytest.mark.parametrize(
    "handler_name,stdin_factory",
    [
        ("handle_pre_tool_use", _build_pre_tool_use_stdin),
        ("handle_subagent_stop", _build_subagent_stop_stdin),
        ("handle_post_tool_use", _build_post_tool_use_stdin),
        ("handle_pre_write", _build_pre_write_stdin),
    ],
    ids=["pre_tool_use", "subagent_stop", "post_tool_use", "pre_write"],
)
def test_handler_generates_valid_uuid4_hook_id_in_hook_invoked_event(
    handler_name, stdin_factory, monkeypatch
):
    """Each handler generates a UUID4 hook_id and includes it in the HOOK_INVOKED event."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_factory()))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        handler_fn = getattr(adapter, handler_name)
        handler_fn()

    hook_invoked_events = [e for e in events if e.event_type == "HOOK_INVOKED"]
    assert len(hook_invoked_events) >= 1, (
        f"Expected at least one HOOK_INVOKED event from {handler_name}"
    )

    first_event = hook_invoked_events[0]
    assert "hook_id" in first_event.data, (
        f"HOOK_INVOKED event from {handler_name} missing 'hook_id' in data"
    )
    assert UUID4_PATTERN.match(first_event.data["hook_id"]), (
        f"hook_id '{first_event.data['hook_id']}' is not a valid UUID4"
    )


# --- Test 2: hook_id is unique per invocation ---


def test_hook_id_unique_across_invocations(monkeypatch):
    """Calling the same handler twice produces different hook_ids."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    all_hook_ids = []

    for _ in range(2):
        events = []
        writer = _make_capturing_writer(events)

        monkeypatch.setattr("sys.stdin", io.StringIO(_build_pre_tool_use_stdin()))
        monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

        with patch.object(adapter, "_create_audit_writer", return_value=writer):
            adapter.handle_pre_tool_use()

        hook_invoked = [e for e in events if e.event_type == "HOOK_INVOKED"]
        assert len(hook_invoked) >= 1
        all_hook_ids.append(hook_invoked[0].data["hook_id"])

    assert all_hook_ids[0] != all_hook_ids[1], "hook_id must be unique per invocation"


# --- Test 3: _log_hook_invoked with hook_id=None omits the field ---


def test_log_hook_invoked_without_hook_id_omits_field():
    """Backward compatibility: calling _log_hook_invoked without hook_id omits the field."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        adapter._log_hook_invoked("test_handler", summary={"key": "val"})

    hook_invoked = [e for e in events if e.event_type == "HOOK_INVOKED"]
    assert len(hook_invoked) == 1
    assert "hook_id" not in hook_invoked[0].data, (
        "hook_id should be absent when not provided"
    )
