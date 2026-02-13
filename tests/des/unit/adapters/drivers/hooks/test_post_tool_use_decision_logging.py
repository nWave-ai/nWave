"""Tests for decision logging in handle_post_tool_use.

handle_post_tool_use emits HOOK_POST_TOOL_USE_INJECTED when additional_context
is returned by PostToolUseService, or HOOK_POST_TOOL_USE_PASSTHROUGH when it is
None. Logging is in the adapter layer (not the service) to keep the hexagonal
boundary clean.

Tests exercise through the handle_post_tool_use driving port and assert at the
AuditLogWriter driven port boundary.

Test Budget: 5 distinct behaviors x 2 = 10 max. Using 5 tests.

Behaviors:
1. HOOK_POST_TOOL_USE_INJECTED emitted with context_type='continuation' and is_des_task=True
2. HOOK_POST_TOOL_USE_INJECTED emitted with context_type='failure_notification' for failure context
3. HOOK_POST_TOOL_USE_PASSTHROUGH emitted when additional_context is None (non-DES task)
4. HOOK_POST_TOOL_USE_PASSTHROUGH emitted with reason for DES task that has no context
5. Logging failure does not affect response to Claude Code (fail-open preserved)
"""

import io
import json
from unittest.mock import patch

from des.ports.driven_ports.audit_log_writer import AuditEvent


def _make_capturing_writer(events: list[AuditEvent]):
    """Create a mock AuditLogWriter that appends events to the given list."""
    from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter

    class CapturingWriter(NullAuditLogWriter):
        def log_event(self, event: AuditEvent) -> None:
            events.append(event)

    return CapturingWriter()


def _build_post_tool_use_stdin(*, des_task: bool = False) -> str:
    """Build PostToolUse input JSON."""
    prompt = "Do something"
    if des_task:
        prompt = (
            "<!-- DES-VALIDATION : required -->\n"
            "<!-- DES-PROJECT-ID : des-observability -->\n"
            "<!-- DES-STEP-ID : 04-01 -->\n"
            "Do something"
        )
    return json.dumps({"tool_name": "Task", "tool_input": {"prompt": prompt}})


def _stub_service_returning(context_value: str | None):
    """Create a PostToolUseService stub returning the given context."""

    class StubPostToolUseService:
        def __init__(self, **kwargs):
            pass

        def check_completion_status(self, **kwargs):
            return context_value

    return StubPostToolUseService


# --- Test 1: INJECTED emitted with context_type='continuation' for DES task ---


def test_injected_event_emitted_for_continuation_context(monkeypatch):
    """HOOK_POST_TOOL_USE_INJECTED emitted with context_type='continuation' and is_des_task=True."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    continuation_text = (
        "DES STEP COMPLETED [des-observability/04-01]\n"
        "Status: PASSED\n"
        "\n"
        "Continue the DELIVER workflow."
    )

    monkeypatch.setattr(
        "sys.stdin", io.StringIO(_build_post_tool_use_stdin(des_task=True))
    )
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    stub_service = _stub_service_returning(continuation_text)

    with (
        patch.object(adapter, "_create_audit_writer", return_value=writer),
        patch(
            "des.application.post_tool_use_service.PostToolUseService",
            stub_service,
        ),
    ):
        exit_code = adapter.handle_post_tool_use()

    assert exit_code == 0

    injected = [e for e in events if e.event_type == "HOOK_POST_TOOL_USE_INJECTED"]
    assert len(injected) == 1, (
        f"Expected one HOOK_POST_TOOL_USE_INJECTED event, "
        f"got {len(injected)}. All events: {[e.event_type for e in events]}"
    )

    event = injected[0]
    assert event.data["is_des_task"] is True
    assert event.data["context_type"] == "continuation"


# --- Test 2: INJECTED emitted with context_type='failure_notification' ---


def test_injected_event_emitted_for_failure_notification(monkeypatch):
    """HOOK_POST_TOOL_USE_INJECTED emitted with context_type='failure_notification'."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    failure_text = (
        "DES STEP INCOMPLETE [des-observability/04-01]\n"
        "Status: FAILED\n"
        "Errors: Missing COMMIT phase\n"
        "\n"
        "The sub-agent failed to complete all required TDD phases."
    )

    monkeypatch.setattr(
        "sys.stdin", io.StringIO(_build_post_tool_use_stdin(des_task=True))
    )
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    stub_service = _stub_service_returning(failure_text)

    with (
        patch.object(adapter, "_create_audit_writer", return_value=writer),
        patch(
            "des.application.post_tool_use_service.PostToolUseService",
            stub_service,
        ),
    ):
        exit_code = adapter.handle_post_tool_use()

    assert exit_code == 0

    injected = [e for e in events if e.event_type == "HOOK_POST_TOOL_USE_INJECTED"]
    assert len(injected) == 1, (
        f"Expected one HOOK_POST_TOOL_USE_INJECTED event, "
        f"got {len(injected)}. All events: {[e.event_type for e in events]}"
    )

    event = injected[0]
    assert event.data["is_des_task"] is True
    assert event.data["context_type"] == "failure_notification"


# --- Test 3: PASSTHROUGH emitted for non-DES task ---


def test_passthrough_event_emitted_for_non_des_task(monkeypatch):
    """HOOK_POST_TOOL_USE_PASSTHROUGH emitted with is_des_task=False when no DES markers."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    monkeypatch.setattr(
        "sys.stdin", io.StringIO(_build_post_tool_use_stdin(des_task=False))
    )
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    stub_service = _stub_service_returning(None)

    with (
        patch.object(adapter, "_create_audit_writer", return_value=writer),
        patch(
            "des.application.post_tool_use_service.PostToolUseService",
            stub_service,
        ),
    ):
        exit_code = adapter.handle_post_tool_use()

    assert exit_code == 0

    passthrough = [
        e for e in events if e.event_type == "HOOK_POST_TOOL_USE_PASSTHROUGH"
    ]
    assert len(passthrough) == 1, (
        f"Expected one HOOK_POST_TOOL_USE_PASSTHROUGH event, "
        f"got {len(passthrough)}. All events: {[e.event_type for e in events]}"
    )

    event = passthrough[0]
    assert event.data["is_des_task"] is False
    assert "reason" in event.data
    assert len(event.data["reason"]) > 0


# --- Test 4: PASSTHROUGH emitted for DES task with no context ---


def test_passthrough_event_emitted_for_des_task_with_no_context(monkeypatch):
    """HOOK_POST_TOOL_USE_PASSTHROUGH emitted with is_des_task=True and reason when service returns None."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events = []
    writer = _make_capturing_writer(events)

    monkeypatch.setattr(
        "sys.stdin", io.StringIO(_build_post_tool_use_stdin(des_task=True))
    )
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    stub_service = _stub_service_returning(None)

    with (
        patch.object(adapter, "_create_audit_writer", return_value=writer),
        patch(
            "des.application.post_tool_use_service.PostToolUseService",
            stub_service,
        ),
    ):
        exit_code = adapter.handle_post_tool_use()

    assert exit_code == 0

    passthrough = [
        e for e in events if e.event_type == "HOOK_POST_TOOL_USE_PASSTHROUGH"
    ]
    assert len(passthrough) == 1, (
        f"Expected one HOOK_POST_TOOL_USE_PASSTHROUGH event, "
        f"got {len(passthrough)}. All events: {[e.event_type for e in events]}"
    )

    event = passthrough[0]
    assert event.data["is_des_task"] is True
    assert "reason" in event.data


# --- Test 5: Logging failure does not affect response ---


def test_logging_failure_does_not_affect_response(monkeypatch):
    """When decision logging raises, handle_post_tool_use still returns valid response."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    log_call_count = 0

    class ExplodingWriter:
        def log_event(self, event):
            nonlocal log_call_count
            log_call_count += 1
            raise RuntimeError("Audit writer exploded")

    monkeypatch.setattr(
        "sys.stdin", io.StringIO(_build_post_tool_use_stdin(des_task=False))
    )
    printed = []
    monkeypatch.setattr("builtins.print", lambda *a, **kw: printed.append(a))

    stub_service = _stub_service_returning(None)

    with (
        patch.object(adapter, "_create_audit_writer", return_value=ExplodingWriter()),
        patch(
            "des.application.post_tool_use_service.PostToolUseService",
            stub_service,
        ),
    ):
        exit_code = adapter.handle_post_tool_use()

    # Must still succeed (fail-open)
    assert exit_code == 0
    # Verify response is valid JSON
    assert len(printed) > 0, "Expected at least one print call"
    last_output = str(printed[-1])
    assert "{}" in last_output or '"additionalContext"' in last_output
    # Verify writer was called (logging was attempted)
    assert log_call_count > 0, (
        "Expected audit writer to be called even though it raised"
    )
