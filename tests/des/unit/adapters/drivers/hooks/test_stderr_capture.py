"""Tests for stderr capture in HOOK_ERROR events in claude_code_hook_adapter.

When an exception occurs in a handler, the HOOK_ERROR event should include:
- error_type: the exception class name (e.g., 'RuntimeError')
- stderr_capture: any stderr output captured during handler execution,
  truncated to 1000 characters maximum. Empty string when no stderr.

Tests exercise through handler driving ports and assert at the AuditLogWriter
driven port boundary.

Test Budget: 5 distinct behaviors x 2 = 10 max. Using 6 tests (1 acceptance + 5 unit).

Behaviors covered:
1. HOOK_ERROR includes error_type field with exception class name
2. HOOK_ERROR includes stderr_capture with stderr content when present
3. stderr_capture truncated to 1000 characters maximum
4. stderr_capture is empty string when no stderr output
5. stderr redirect does not interfere with normal handler operation
"""

import io
import json
import sys
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


def _build_valid_pre_tool_use_stdin() -> str:
    """Valid Task input that passes max_turns validation (allow path)."""
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


def _run_handler_with_exception(monkeypatch, exception_factory, events=None):
    """Run handle_pre_tool_use with a service that raises an exception.

    Returns the list of captured audit events.
    """
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    if events is None:
        events = []
    writer = _make_capturing_writer(events)

    monkeypatch.setattr("sys.stdin", io.StringIO(_build_valid_pre_tool_use_stdin()))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with (
        patch.object(adapter, "_create_audit_writer", return_value=writer),
        patch.object(
            adapter, "create_pre_tool_use_service", side_effect=exception_factory
        ),
    ):
        exit_code = adapter.handle_pre_tool_use()

    return events, exit_code


# --- Acceptance Test: HOOK_ERROR includes error_type and stderr_capture ---


def test_acceptance_hook_error_includes_error_type_and_stderr_capture(monkeypatch):
    """HOOK_ERROR event includes error_type (class name) and stderr_capture
    when an exception occurs in a handler that also writes to stderr."""

    def exploding_service():
        # Write to stderr directly (not via print which is monkeypatched)
        sys.stderr.write("something went wrong in service\n")
        raise ValueError("bad input data")

    events, exit_code = _run_handler_with_exception(monkeypatch, exploding_service)

    assert exit_code == 1, "Handler should return 1 on exception"

    error_events = [e for e in events if e.event_type == "HOOK_ERROR"]
    assert len(error_events) >= 1, (
        f"Expected at least one HOOK_ERROR event, got {len(error_events)}. "
        f"All events: {[e.event_type for e in events]}"
    )

    event = error_events[0]
    # AC1: error_type is the exception class name
    assert event.data.get("error_type") == "ValueError", (
        f"Expected error_type='ValueError', got '{event.data.get('error_type')}'"
    )
    # AC2: stderr_capture contains the stderr output
    assert "something went wrong in service" in event.data.get("stderr_capture", ""), (
        f"Expected stderr content in stderr_capture, "
        f"got '{event.data.get('stderr_capture')}'"
    )


# --- Test 1: error_type included in HOOK_ERROR with correct class name ---


@pytest.mark.parametrize(
    "exception_class,expected_name",
    [
        (ValueError, "ValueError"),
        (TypeError, "TypeError"),
        (RuntimeError, "RuntimeError"),
        (KeyError, "KeyError"),
    ],
    ids=["ValueError", "TypeError", "RuntimeError", "KeyError"],
)
def test_hook_error_includes_error_type(exception_class, expected_name, monkeypatch):
    """HOOK_ERROR event includes error_type field matching the exception class name."""

    def raiser():
        raise exception_class("simulated")

    events, _ = _run_handler_with_exception(monkeypatch, raiser)

    error_events = [e for e in events if e.event_type == "HOOK_ERROR"]
    assert len(error_events) >= 1, (
        f"Expected HOOK_ERROR, got events: {[e.event_type for e in events]}"
    )
    assert error_events[0].data.get("error_type") == expected_name, (
        f"Expected error_type='{expected_name}', "
        f"got '{error_events[0].data.get('error_type')}'"
    )


# --- Test 2: stderr_capture contains stderr output ---


def test_hook_error_captures_stderr_output(monkeypatch):
    """HOOK_ERROR event includes stderr_capture with captured stderr content."""

    def exploding_with_stderr():
        # Write to stderr directly (not via print which is monkeypatched)
        sys.stderr.write("stderr output line 1\n")
        sys.stderr.write("stderr output line 2\n")
        raise RuntimeError("boom")

    events, _ = _run_handler_with_exception(monkeypatch, exploding_with_stderr)

    error_events = [e for e in events if e.event_type == "HOOK_ERROR"]
    assert len(error_events) >= 1

    stderr_capture = error_events[0].data.get("stderr_capture", "")
    assert "stderr output line 1" in stderr_capture
    assert "stderr output line 2" in stderr_capture


# --- Test 3: stderr_capture truncated to 1000 characters ---


def test_hook_error_stderr_truncated_to_1000_chars(monkeypatch):
    """stderr_capture is truncated to 1000 characters maximum."""

    def exploding_with_long_stderr():
        # Write to stderr directly (not via print which is monkeypatched)
        sys.stderr.write("X" * 2000)
        raise RuntimeError("boom")

    events, _ = _run_handler_with_exception(monkeypatch, exploding_with_long_stderr)

    error_events = [e for e in events if e.event_type == "HOOK_ERROR"]
    assert len(error_events) >= 1

    stderr_capture = error_events[0].data.get("stderr_capture", "")
    assert len(stderr_capture) <= 1000, (
        f"stderr_capture should be at most 1000 chars, got {len(stderr_capture)}"
    )


# --- Test 4: stderr_capture is empty string when no stderr output ---


def test_hook_error_stderr_empty_when_no_output(monkeypatch):
    """stderr_capture is empty string (not absent) when no stderr was written."""

    def exploding_no_stderr():
        raise RuntimeError("boom without stderr")

    events, _ = _run_handler_with_exception(monkeypatch, exploding_no_stderr)

    error_events = [e for e in events if e.event_type == "HOOK_ERROR"]
    assert len(error_events) >= 1

    assert "stderr_capture" in error_events[0].data, (
        "stderr_capture field should be present even when empty"
    )
    assert error_events[0].data["stderr_capture"] == "", (
        f"Expected empty string, got '{error_events[0].data['stderr_capture']}'"
    )


# --- Test 5: stderr redirect does not interfere with normal handler operation ---


def test_stderr_redirect_does_not_interfere_with_normal_operation(monkeypatch):
    """Handlers still operate correctly when stderr redirect is in place
    (no exceptions, normal allow path works)."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    monkeypatch.setattr("sys.stdin", io.StringIO(_build_valid_pre_tool_use_stdin()))
    captured_output = []
    monkeypatch.setattr("builtins.print", lambda *a, **kw: captured_output.append(a))

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        exit_code = adapter.handle_pre_tool_use()

    assert exit_code == 0, "Normal allow path should return 0"
    # Verify no HOOK_ERROR events (no exception occurred)
    error_events = [e for e in events if e.event_type == "HOOK_ERROR"]
    assert len(error_events) == 0, (
        f"No HOOK_ERROR expected on normal path, got {len(error_events)}"
    )
