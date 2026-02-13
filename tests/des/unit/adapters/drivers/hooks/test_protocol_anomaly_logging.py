"""Tests for HOOK_PROTOCOL_ANOMALY events in claude_code_hook_adapter.

Each handler has early-return paths for empty stdin and JSON parse errors.
These paths now emit HOOK_PROTOCOL_ANOMALY audit events with anomaly_type,
handler, detail, and fallback_action fields.

Tests exercise through handler driving ports and assert at the AuditLogWriter
driven port boundary.

Test Budget: 5 distinct behaviors x 2 = 10 max. Using 5 tests.

Behaviors covered:
1. Empty stdin produces HOOK_PROTOCOL_ANOMALY with anomaly_type='empty_stdin'
2. JSON parse error produces HOOK_PROTOCOL_ANOMALY with anomaly_type='json_parse_error'
3. Each anomaly includes handler name, detail string, and fallback_action
4. fallback_action matches actual handler behavior
5. Anomaly logging failure does not change handler exit code or response
"""

import io
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


# --- Test 1: Empty stdin in any handler produces HOOK_PROTOCOL_ANOMALY ---


@pytest.mark.parametrize(
    "handler_name,expected_fallback,expected_exit_code",
    [
        ("handle_pre_tool_use", "allow", 0),
        ("handle_subagent_stop", "allow", 0),
        ("handle_post_tool_use", "allow", 0),
        ("handle_pre_write", "allow", 0),
    ],
    ids=["pre_tool_use", "subagent_stop", "post_tool_use", "pre_write"],
)
def test_empty_stdin_produces_protocol_anomaly(
    handler_name, expected_fallback, expected_exit_code, monkeypatch
):
    """Empty stdin in any handler emits HOOK_PROTOCOL_ANOMALY with anomaly_type='empty_stdin'."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        exit_code = getattr(adapter, handler_name)()

    assert exit_code == expected_exit_code

    anomaly_events = [e for e in events if e.event_type == "HOOK_PROTOCOL_ANOMALY"]
    assert len(anomaly_events) == 1, (
        f"Expected exactly one HOOK_PROTOCOL_ANOMALY event from {handler_name} on empty stdin, "
        f"got {len(anomaly_events)}. All events: {[e.event_type for e in events]}"
    )

    event = anomaly_events[0]
    assert event.data["anomaly_type"] == "empty_stdin"
    assert event.data["handler"] == handler_name.replace("handle_", "")
    assert "detail" in event.data
    assert event.data["fallback_action"] == expected_fallback


# --- Test 2: JSON parse error in any handler produces HOOK_PROTOCOL_ANOMALY ---


@pytest.mark.parametrize(
    "handler_name,expected_fallback,expected_exit_code",
    [
        ("handle_pre_tool_use", "error", 1),
        ("handle_subagent_stop", "error", 1),
        ("handle_post_tool_use", "allow", 0),
        ("handle_pre_write", "allow", 0),
    ],
    ids=["pre_tool_use", "subagent_stop", "post_tool_use", "pre_write"],
)
def test_json_parse_error_produces_protocol_anomaly(
    handler_name, expected_fallback, expected_exit_code, monkeypatch
):
    """Malformed JSON in any handler emits HOOK_PROTOCOL_ANOMALY with anomaly_type='json_parse_error'."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    monkeypatch.setattr("sys.stdin", io.StringIO("{not valid json"))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        exit_code = getattr(adapter, handler_name)()

    assert exit_code == expected_exit_code

    anomaly_events = [e for e in events if e.event_type == "HOOK_PROTOCOL_ANOMALY"]
    assert len(anomaly_events) == 1, (
        f"Expected exactly one HOOK_PROTOCOL_ANOMALY event from {handler_name} on bad JSON, "
        f"got {len(anomaly_events)}. All events: {[e.event_type for e in events]}"
    )

    event = anomaly_events[0]
    assert event.data["anomaly_type"] == "json_parse_error"
    assert event.data["handler"] == handler_name.replace("handle_", "")
    assert "detail" in event.data
    assert event.data["fallback_action"] == expected_fallback


# --- Test 3: Anomaly logging failure does not change handler behavior ---


@pytest.mark.parametrize(
    "stdin_content,handler_name,expected_exit_code",
    [
        ("", "handle_pre_tool_use", 0),
        ("{bad json", "handle_pre_tool_use", 1),
        ("", "handle_subagent_stop", 0),
        ("{bad json", "handle_subagent_stop", 1),
    ],
    ids=[
        "empty_stdin_pre_tool_use",
        "bad_json_pre_tool_use",
        "empty_stdin_subagent_stop",
        "bad_json_subagent_stop",
    ],
)
def test_anomaly_logging_failure_does_not_change_exit_code(
    stdin_content, handler_name, expected_exit_code, monkeypatch
):
    """When anomaly logging itself throws, handler exit code and response are unchanged."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    class ExplodingWriter:
        def log_event(self, event):
            raise RuntimeError("Writer explosion")

    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_content))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=ExplodingWriter()):
        exit_code = getattr(adapter, handler_name)()

    assert exit_code == expected_exit_code, (
        f"Anomaly logging failure changed exit code for {handler_name}: "
        f"expected {expected_exit_code}, got {exit_code}"
    )
