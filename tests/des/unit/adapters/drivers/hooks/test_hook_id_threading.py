"""Tests for hook_id threading from adapter through services to audit events.

Verifies that hook_id generated at adapter entry is propagated through
service.validate() calls so all service-emitted audit events (ALLOWED,
BLOCKED, PASSED, FAILED, COMMIT_*) carry the hook_id for correlation
with the adapter-emitted HOOK_INVOKED event.

Test Budget: 4 distinct behaviors x 2 = 8 max unit tests.
Using 4 tests (parametrized where appropriate):

1. PreToolUse ALLOWED event carries same hook_id as HOOK_INVOKED
2. PreToolUse BLOCKED event carries same hook_id as HOOK_INVOKED
3. SubagentStop PASSED event carries same hook_id as HOOK_INVOKED
4. SubagentStop FAILED event carries same hook_id as HOOK_INVOKED
"""

import io
import json
from pathlib import Path
from unittest.mock import patch

import yaml

from des.ports.driven_ports.audit_log_writer import AuditEvent


def _make_capturing_writer(events: list[AuditEvent]):
    """Create an AuditLogWriter that appends events to the given list."""
    from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter

    class CapturingWriter(NullAuditLogWriter):
        def log_event(self, event: AuditEvent) -> None:
            events.append(event)

    return CapturingWriter()


def _build_des_task_stdin() -> str:
    """Valid DES-validated Task input that passes all validation."""
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


def _build_no_max_turns_stdin() -> str:
    """Task input missing max_turns (triggers BLOCKED)."""
    return json.dumps(
        {
            "tool_name": "Task",
            "tool_input": {
                "prompt": "Do something",
                "subagent_type": "code",
            },
        }
    )


# --- Test 1: PreToolUse ALLOWED event carries same hook_id as HOOK_INVOKED ---


def test_pre_tool_use_allowed_event_carries_hook_id(monkeypatch, tmp_path):
    """When PreToolUse allows a DES task, the HOOK_PRE_TOOL_USE_ALLOWED
    event carries the same hook_id as the HOOK_INVOKED event."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

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

    events: list[AuditEvent] = []
    writer = _make_capturing_writer(events)

    monkeypatch.setattr("sys.stdin", io.StringIO(_build_des_task_stdin()))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        exit_code = adapter.handle_pre_tool_use()

    assert exit_code == 0

    # Extract hook_id from HOOK_INVOKED
    invoked = [e for e in events if e.event_type == "HOOK_INVOKED"]
    assert len(invoked) >= 1
    hook_id = invoked[0].data["hook_id"]

    # The service-emitted ALLOWED event must carry the same hook_id
    allowed = [e for e in events if e.event_type == "HOOK_PRE_TOOL_USE_ALLOWED"]
    assert len(allowed) == 1
    assert allowed[0].hook_id == hook_id


# --- Test 2: PreToolUse BLOCKED event carries same hook_id as HOOK_INVOKED ---


def test_pre_tool_use_blocked_event_carries_hook_id(monkeypatch):
    """When PreToolUse blocks (missing max_turns), the HOOK_PRE_TOOL_USE_BLOCKED
    event carries the same hook_id as the HOOK_INVOKED event."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    events: list[AuditEvent] = []
    writer = _make_capturing_writer(events)

    monkeypatch.setattr("sys.stdin", io.StringIO(_build_no_max_turns_stdin()))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        exit_code = adapter.handle_pre_tool_use()

    assert exit_code == 2

    # Extract hook_id from HOOK_INVOKED
    invoked = [e for e in events if e.event_type == "HOOK_INVOKED"]
    assert len(invoked) >= 1
    hook_id = invoked[0].data["hook_id"]

    # The service-emitted BLOCKED event must carry the same hook_id
    blocked = [e for e in events if e.event_type == "HOOK_PRE_TOOL_USE_BLOCKED"]
    assert len(blocked) == 1
    assert blocked[0].hook_id == hook_id


# --- Test 3: SubagentStop PASSED event carries same hook_id as HOOK_INVOKED ---


def _write_complete_execution_log(
    log_path: Path, project_id: str, step_id: str
) -> None:
    """Write a complete execution-log.yaml that passes validation."""
    events = []
    phases = [
        ("PREPARE", "EXECUTED", "PASS"),
        ("RED_ACCEPTANCE", "EXECUTED", "FAIL"),
        ("RED_UNIT", "EXECUTED", "FAIL"),
        ("GREEN", "EXECUTED", "PASS"),
        ("REVIEW", "EXECUTED", "PASS"),
        ("REFACTOR_CONTINUOUS", "SKIPPED", "APPROVED_SKIP:Clean"),
        ("COMMIT", "EXECUTED", "PASS"),
    ]
    for i, (name, status, outcome) in enumerate(phases):
        ts = f"2026-02-10T21:{i:02d}:00Z"
        events.append(f"{step_id}|{name}|{status}|{outcome}|{ts}")

    log_data = {
        "schema_version": "2.0",
        "project_id": project_id,
        "events": events,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(yaml.dump(log_data, default_flow_style=False, sort_keys=False))


def test_subagent_stop_passed_event_carries_hook_id(monkeypatch, tmp_path):
    """When SubagentStop passes validation, the HOOK_SUBAGENT_STOP_PASSED
    event carries the same hook_id as the HOOK_INVOKED event."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    des_dir = tmp_path / ".nwave" / "des"
    des_dir.mkdir(parents=True)
    monkeypatch.setattr(adapter, "DES_SESSION_DIR", des_dir)
    monkeypatch.setattr(adapter, "DES_TASK_ACTIVE_FILE", des_dir / "des-task-active")
    monkeypatch.setattr(
        adapter,
        "_signal_file_for",
        lambda project_id, step_id: (
            des_dir / f"des-task-active-{project_id}--{step_id}"
        ),
    )

    # Write complete execution log
    log_path = tmp_path / "execution-log.yaml"
    _write_complete_execution_log(log_path, "test-project", "01-01")

    events: list[AuditEvent] = []
    writer = _make_capturing_writer(events)

    stop_stdin = json.dumps(
        {
            "executionLogPath": str(log_path),
            "projectId": "test-project",
            "stepId": "01-01",
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(stop_stdin))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        exit_code = adapter.handle_subagent_stop()

    assert exit_code == 0

    # Extract hook_id from HOOK_INVOKED
    invoked = [e for e in events if e.event_type == "HOOK_INVOKED"]
    assert len(invoked) >= 1
    hook_id = invoked[0].data["hook_id"]

    # The service-emitted PASSED event must carry the same hook_id
    passed = [e for e in events if e.event_type == "HOOK_SUBAGENT_STOP_PASSED"]
    assert len(passed) == 1
    assert passed[0].hook_id == hook_id


# --- Test 4: SubagentStop FAILED event carries same hook_id as HOOK_INVOKED ---


def test_subagent_stop_failed_event_carries_hook_id(monkeypatch, tmp_path):
    """When SubagentStop fails validation (incomplete phases), the
    HOOK_SUBAGENT_STOP_FAILED event carries the same hook_id as HOOK_INVOKED."""
    from des.adapters.drivers.hooks import claude_code_hook_adapter as adapter

    des_dir = tmp_path / ".nwave" / "des"
    des_dir.mkdir(parents=True)
    monkeypatch.setattr(adapter, "DES_SESSION_DIR", des_dir)
    monkeypatch.setattr(adapter, "DES_TASK_ACTIVE_FILE", des_dir / "des-task-active")
    monkeypatch.setattr(
        adapter,
        "_signal_file_for",
        lambda project_id, step_id: (
            des_dir / f"des-task-active-{project_id}--{step_id}"
        ),
    )

    # Write incomplete execution log (only 2 of 7 phases)
    log_path = tmp_path / "execution-log.yaml"
    event_strings = [
        "01-01|PREPARE|EXECUTED|PASS|2026-02-10T21:00:00Z",
        "01-01|RED_ACCEPTANCE|EXECUTED|FAIL|2026-02-10T21:01:00Z",
    ]
    log_data = {
        "schema_version": "2.0",
        "project_id": "test-project",
        "events": event_strings,
    }
    log_path.write_text(yaml.dump(log_data, default_flow_style=False, sort_keys=False))

    events: list[AuditEvent] = []
    writer = _make_capturing_writer(events)

    stop_stdin = json.dumps(
        {
            "executionLogPath": str(log_path),
            "projectId": "test-project",
            "stepId": "01-01",
        }
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(stop_stdin))
    monkeypatch.setattr("builtins.print", lambda *a, **kw: None)

    with patch.object(adapter, "_create_audit_writer", return_value=writer):
        adapter.handle_subagent_stop()

    # Extract hook_id from HOOK_INVOKED
    invoked = [e for e in events if e.event_type == "HOOK_INVOKED"]
    assert len(invoked) >= 1
    hook_id = invoked[0].data["hook_id"]

    # The service-emitted FAILED event must carry the same hook_id
    failed = [e for e in events if e.event_type == "HOOK_SUBAGENT_STOP_FAILED"]
    assert len(failed) == 1
    assert failed[0].hook_id == hook_id
