"""Acceptance test: task_correlation_id flows through signal file and HOOK_COMPLETED events.

Scenario: When a DES-validated Task is allowed by PreToolUse, a task_correlation_id
(UUID4) is generated, stored in the signal file, and propagated to HOOK_COMPLETED
events in both pre_tool_use and subagent_stop handlers. For non-DES tasks, the
task_correlation_id is absent from HOOK_COMPLETED events.

Tests exercise through handler driving ports and assert at the AuditLogWriter
driven port boundary.
"""

import io
import json
import re
from unittest.mock import patch

from des.ports.driven_ports.audit_log_writer import AuditEvent


UUID4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _make_capturing_writer(events: list[AuditEvent]):
    """Create an AuditLogWriter that appends events to the given list."""
    from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter

    class CapturingWriter(NullAuditLogWriter):
        def log_event(self, event: AuditEvent) -> None:
            events.append(event)

    return CapturingWriter()


def _build_des_task_stdin() -> str:
    """Build a valid DES-validated Task input that passes all validation."""
    prompt = (
        "<!-- DES-VALIDATION : required -->\n"
        "<!-- DES-PROJECT-ID : test-project -->\n"
        "<!-- DES-STEP-ID : 01-01 -->\n"
        "\n"
        "# DES_METADATA\n"
        "Step: 01-01\n"
        "Project: test-project\n"
        "Command: /nw:execute\n"
        "\n"
        "# AGENT_IDENTITY\n"
        "Agent: @software-crafter\n"
        "\n"
        "# TASK_CONTEXT\n"
        "Implement something.\n"
        "\n"
        "# TDD_PHASES\n"
        "Execute all 5 phases.\n"
        "1. PREPARE\n"
        "2. RED_ACCEPTANCE\n"
        "3. RED_UNIT\n"
        "4. GREEN\n"
        "5. REVIEW\n"
        "6. REFACTOR_CONTINUOUS\n"
        "7. COMMIT\n"
        "\n"
        "# QUALITY_GATES\n"
        "- All tests must pass\n"
        "\n"
        "# OUTCOME_RECORDING\n"
        "Record outcomes.\n"
        "\n"
        "# RECORDING_INTEGRITY\n"
        "Valid Skip Prefixes: NOT_APPLICABLE\n"
        "\n"
        "# BOUNDARY_RULES\n"
        "Files to modify: src/test.py\n"
        "\n"
        "# TIMEOUT_INSTRUCTION\n"
        "Turn budget: 30\n"
    )
    return json.dumps(
        {
            "tool_name": "Task",
            "tool_input": {
                "prompt": prompt,
                "max_turns": 30,
                "subagent_type": "code",
            },
        }
    )


def test_task_correlation_id_flows_from_signal_to_hook_completed(monkeypatch, tmp_path):
    """End-to-end: task_correlation_id generated in pre_tool_use signal file
    is the same UUID4 that appears in HOOK_COMPLETED events for both
    pre_tool_use and subagent_stop handlers."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    # Use tmp_path for signal files to avoid polluting working directory
    monkeypatch.setattr(adapter, "DES_SESSION_DIR", tmp_path / ".nwave" / "des")
    monkeypatch.setattr(
        adapter, "DES_TASK_ACTIVE_FILE", tmp_path / ".nwave" / "des" / "des-task-active"
    )
    monkeypatch.setattr(
        adapter,
        "_signal_file_for",
        lambda project_id, step_id: (
            tmp_path / ".nwave" / "des" / f"des-task-active-{project_id}--{step_id}"
        ),
    )

    # --- Step 1: PreToolUse allows a DES task and creates signal with correlation ID ---
    pre_events: list[AuditEvent] = []
    pre_writer = _make_capturing_writer(pre_events)

    monkeypatch.setattr("sys.stdin", io.StringIO(_build_des_task_stdin()))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=pre_writer):
        pre_exit = adapter.handle_pre_tool_use()

    assert pre_exit == 0, "PreToolUse should allow the DES task"

    # Read signal file and verify task_correlation_id is present and valid UUID4
    signal_file = tmp_path / ".nwave" / "des" / "des-task-active-test-project--01-01"
    assert signal_file.exists(), "Signal file should be created for DES task"
    signal_data = json.loads(signal_file.read_text())
    assert "task_correlation_id" in signal_data, (
        "Signal file must contain task_correlation_id"
    )
    correlation_id = signal_data["task_correlation_id"]
    assert UUID4_PATTERN.match(correlation_id), (
        f"task_correlation_id '{correlation_id}' must be a valid UUID4"
    )

    # Verify HOOK_COMPLETED for pre_tool_use contains the same correlation ID
    pre_completed = [e for e in pre_events if e.event_type == "HOOK_COMPLETED"]
    assert len(pre_completed) == 1
    assert pre_completed[0].data.get("task_correlation_id") == correlation_id, (
        "HOOK_COMPLETED for pre_tool_use must include the task_correlation_id"
    )

    # --- Step 2: SubagentStop reads correlation ID from signal before removing it ---
    stop_events: list[AuditEvent] = []
    stop_writer = _make_capturing_writer(stop_events)

    subagent_stop_stdin = json.dumps(
        {
            "session_id": "s1",
            "hook_event_name": "SubagentStop",
            "agent_id": "a1",
            "agent_type": "code",
            "cwd": str(tmp_path),
            "executionLogPath": str(tmp_path / "execution-log.yaml"),
            "projectId": "test-project",
            "stepId": "01-01",
            "stop_hook_active": True,
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(subagent_stop_stdin))

    # SubagentStopService will fail validation (no real log), but HOOK_COMPLETED
    # should still fire with the correlation ID from the signal file
    with patch.object(adapter, "_create_audit_writer", return_value=stop_writer):
        adapter.handle_subagent_stop()

    stop_completed = [e for e in stop_events if e.event_type == "HOOK_COMPLETED"]
    assert len(stop_completed) == 1
    assert stop_completed[0].data.get("task_correlation_id") == correlation_id, (
        "HOOK_COMPLETED for subagent_stop must include the same task_correlation_id "
        "that was stored in the signal file"
    )


def test_task_correlation_id_absent_for_non_des_tasks(monkeypatch):
    """For non-DES tasks, task_correlation_id should be absent from HOOK_COMPLETED."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events: list[AuditEvent] = []
    writer = _make_capturing_writer(events)

    # Non-DES task: no DES-VALIDATION marker in prompt
    non_des_stdin = json.dumps(
        {
            "tool_name": "Task",
            "tool_input": {
                "prompt": "Do something without DES markers",
                "max_turns": 15,
                "subagent_type": "code",
            },
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(non_des_stdin))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        adapter.handle_pre_tool_use()

    completed = [e for e in events if e.event_type == "HOOK_COMPLETED"]
    assert len(completed) == 1
    assert "task_correlation_id" not in completed[0].data, (
        "HOOK_COMPLETED for non-DES tasks must not contain task_correlation_id"
    )
