"""
pytest configuration and fixtures for DES hook enforcement acceptance tests.

This module provides test fixtures following hexagonal architecture principles:
- Tests interact with DRIVING PORTS (DESOrchestrator, CLI adapters)
- Internal components accessed only through entry points
- FakeTimeProvider enables deterministic timestamp testing
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest


class FakeTimeProvider:
    """Test double for TimeProvider enabling deterministic timestamp testing."""

    def __init__(self, fixed_time: datetime):
        self._fixed_time = fixed_time

    def now_utc(self) -> datetime:
        """Return fixed UTC timestamp for testing."""
        return self._fixed_time


class AuditLogReader:
    """Helper for reading and verifying audit log entries."""

    def __init__(self, audit_log_path: Path):
        # audit_log_path is the directory where logs are stored
        # AuditLogger creates date-specific files like audit-2026-02-02.log
        self.audit_log_dir = (
            audit_log_path.parent
            if audit_log_path.name == "audit.log"
            else audit_log_path
        )

    def get_all_entries(self) -> list[dict[str, Any]]:
        """Read all audit log entries from all date-specific log files."""
        entries = []

        if not self.audit_log_dir.exists():
            return []

        # Read all audit-*.log files in the directory
        for log_file in self.audit_log_dir.glob("audit-*.log"):
            with open(log_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        return entries

    def get_entries_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """Filter audit log entries by event type."""
        # Note: Events are stored with 'event' field, not 'event_type'
        return [e for e in self.get_all_entries() if e.get("event") == event_type]

    def contains_event_type(self, event_type: str) -> bool:
        """Check if audit log contains at least one entry of given type."""
        return len(self.get_entries_by_type(event_type)) > 0

    def clear(self):
        """Clear audit log for test isolation."""
        if self.audit_log_dir.exists():
            for log_file in self.audit_log_dir.glob("audit-*.log"):
                log_file.unlink()


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Create temporary home directory for test isolation."""
    temp_home_dir = tmp_path / "home"
    temp_home_dir.mkdir()
    monkeypatch.setenv("HOME", str(temp_home_dir))
    return temp_home_dir


@pytest.fixture
def claude_config_dir(temp_home):
    """Create .claude directory structure."""
    claude_dir = temp_home / ".claude"
    claude_dir.mkdir()

    des_dir = claude_dir / "des"
    des_dir.mkdir()

    return claude_dir


@pytest.fixture
def settings_local_json_path(claude_config_dir):
    """Return path to .claude/settings.local.json."""
    return claude_config_dir / "settings.local.json"


@pytest.fixture
def des_config_path(claude_config_dir):
    """Return path to ~/.claude/des/config.yaml."""
    return claude_config_dir / "des" / "config.yaml"


@pytest.fixture
def audit_log_path(temp_home, tmp_path, monkeypatch):
    """Return path to audit log file.

    Uses project-local .nwave/des/logs/ path to match production behavior
    where audit logger now defaults to project-local directory.

    We set the working directory to tmp_path so the audit logger will
    use tmp_path/.nwave/des/logs/ for audit logs.
    """
    # Change to tmp_path as the current working directory for this test
    monkeypatch.chdir(tmp_path)

    # Project-local audit log directory (new default behavior)
    logs_dir = tmp_path / ".nwave" / "des" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / "audit.log"


@pytest.fixture
def audit_log_reader(audit_log_path):
    """Provide audit log reader helper."""
    return AuditLogReader(audit_log_path)


@pytest.fixture
def fixed_utc_time():
    """Provide fixed UTC timestamp for testing."""
    return datetime(2025, 10, 5, 14, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_time_provider(fixed_utc_time):
    """Provide FakeTimeProvider for deterministic timestamp testing."""
    return FakeTimeProvider(fixed_utc_time)


@pytest.fixture
def clean_des_environment(temp_home, audit_log_reader):
    """Clean DES environment before each test."""
    # Clear audit log
    audit_log_reader.clear()

    # Clean up any existing config files
    des_config = temp_home / ".claude" / "des" / "config.yaml"
    if des_config.exists():
        des_config.unlink()

    settings_local = temp_home / ".claude" / "settings.local.json"
    if settings_local.exists():
        settings_local.unlink()

    yield

    # Cleanup after test
    audit_log_reader.clear()


@pytest.fixture
def enable_audit_logging(des_config_path, audit_log_path):
    """Configure audit logging to be enabled.

    Sets up the DES config to enable audit logging. Individual tests
    that need a JsonlAuditLogWriter should create one with the
    audit_log_path fixture.
    """
    des_config_path.parent.mkdir(parents=True, exist_ok=True)
    config_content = """# DES Configuration
audit_logging_enabled: true  # Enable comprehensive audit trail
"""
    des_config_path.write_text(config_content)

    # Ensure audit log directory exists for tests that read from it
    audit_log_dir = audit_log_path.parent
    audit_log_dir.mkdir(parents=True, exist_ok=True)

    return des_config_path


@pytest.fixture
def disable_audit_logging(des_config_path, audit_log_reader):
    """Configure audit logging to be disabled.

    Also clears the audit log to ensure test isolation - the test checking
    that no entries are written should not see entries from previous tests.
    """
    # Clear audit log for test isolation
    audit_log_reader.clear()

    des_config_path.parent.mkdir(parents=True, exist_ok=True)
    config_content = """# DES Configuration
audit_logging_enabled: false  # Disable audit logging
"""
    des_config_path.write_text(config_content)
    return des_config_path


@pytest.fixture
def existing_hooks_in_settings(settings_local_json_path):
    """Create existing non-DES hooks in settings.local.json."""
    existing_config = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "SomeOtherTool", "command": "python3 /some/other/hook.py"}
            ]
        }
    }
    settings_local_json_path.write_text(json.dumps(existing_config, indent=2))


@pytest.fixture
def step_file_complete(tmp_path, tdd_phases):
    """Create step file (JSON) with all phases complete for RealSubagentStopHook API."""
    step_file = tmp_path / "step-01-01.json"

    # Build phase_execution_log with all phases from schema
    phase_log = []
    for phase in tdd_phases:
        phase_log.append({"phase_name": phase, "status": "EXECUTED", "outcome": "PASS"})

    step_data = {
        "step_id": "01-01",
        "description": "Test step",
        "tdd_cycle": {"phase_execution_log": phase_log},
        "state": {"status": "COMPLETE"},
    }
    step_file.write_text(json.dumps(step_data, indent=2))
    return step_file


@pytest.fixture
def step_file_incomplete(tmp_path):
    """Create step file with incomplete phases (abandoned IN_PROGRESS)."""
    step_file = tmp_path / "step-01-01.json"
    step_data = {
        "step_id": "01-01",
        "description": "Test step",
        "tdd_cycle": {
            "phase_execution_log": [
                {"phase_name": "PREPARE", "status": "COMPLETED", "outcome": "PASS"},
                {"phase_name": "RED_ACCEPTANCE", "status": "IN_PROGRESS"},  # Abandoned!
            ],
            "duration_minutes": 30,
        },
        "state": {"status": "IN_PROGRESS"},
    }
    step_file.write_text(json.dumps(step_data, indent=2))
    return step_file


@pytest.fixture
def execution_log_complete(tmp_path, tdd_phases):
    """Create execution-log.yaml with all phases complete (Schema v2.0 append-only format)."""
    from datetime import datetime, timezone

    import yaml

    log_file = tmp_path / "execution-log.yaml"
    timestamp = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc).isoformat()

    # Build events for all phases from schema
    events = []
    for phase in tdd_phases:
        # Format: "step_id|phase|status|data|timestamp"
        events.append(f"01-01|{phase}|EXECUTED|PASS|{timestamp}")

    log_data = {
        "project_id": "test-project",
        "created_at": timestamp,
        "total_steps": 1,
        "events": events,
    }

    log_file.write_text(yaml.dump(log_data, default_flow_style=False))
    return log_file


@pytest.fixture
def execution_log_incomplete(tmp_path, tdd_phases):
    """Create execution-log.yaml with incomplete phases (Schema v2.0 append-only format)."""
    from datetime import datetime, timezone

    import yaml

    log_file = tmp_path / "execution-log.yaml"
    timestamp = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc).isoformat()

    # Build events with only first 2 phases (missing remaining phases)
    events = [
        f"01-01|{tdd_phases[0]}|EXECUTED|PASS|{timestamp}",  # PREPARE
        f"01-01|{tdd_phases[1]}|EXECUTED|PASS|{timestamp}",  # RED_ACCEPTANCE
        # Missing: RED_UNIT, GREEN, REVIEW, REFACTOR_CONTINUOUS, COMMIT
    ]

    log_data = {
        "project_id": "test-project",
        "created_at": timestamp,
        "total_steps": 1,
        "events": events,
    }

    log_file.write_text(yaml.dump(log_data, default_flow_style=False))
    return log_file


@pytest.fixture
def valid_task_json():
    """Provide valid Task tool JSON for hook adapter testing.

    Schema v3.0: Loads TDD phases dynamically from canonical template
    (Single Source of Truth: nWave/templates/step-tdd-cycle-schema.json).
    """
    # Import template loader to get canonical phase definitions
    from des.application.tdd_template_loader import (
        get_expected_phase_count,
        get_schema_version,
        get_valid_tdd_phases,
    )

    phases = get_valid_tdd_phases()
    phase_count = get_expected_phase_count()
    schema_version = get_schema_version()

    # Build TDD phase section dynamically from canonical template
    tdd_section = f"# TDD_{phase_count}_PHASES\nExecute all {phase_count} phases (schema v{schema_version}):\n"
    for i, phase in enumerate(phases, 1):
        tdd_section += f"{i}. {phase}\n"

    # DES-formatted prompt with all mandatory sections
    valid_prompt = f"""<!-- DES-VALIDATION: required -->

# DES_METADATA
Project: test-project
Step: 01-01
Command: /nw:execute

# AGENT_IDENTITY
Agent: @software-crafter
Role: Implement features through Outside-In TDD

# TASK_CONTEXT
**Title**: Create user authentication module
**Type**: feature

Acceptance Criteria:
- User can register with email/password
- User can login with valid credentials
- Invalid credentials return error message

{tdd_section}
# QUALITY_GATES
- All tests must pass
- Test coverage >80%
- Code quality validated

# OUTCOME_RECORDING
Update execution-log.yaml after each phase.
Track phase completion in step file.

# RECORDING_INTEGRITY
## Valid Skip Prefixes
NOT_APPLICABLE, BLOCKED_BY_DEPENDENCY, APPROVED_SKIP, CHECKPOINT_PENDING
## Anti-Fraud Rules
NEVER write EXECUTED for phases not actually performed.
NEVER invent timestamps. DES audits all entries.

# BOUNDARY_RULES
- Follow hexagonal architecture
- Use production service integration
- No external API calls without approval

Files to modify:
- src/auth/user_auth.py
- tests/auth/test_user_auth.py

# TIMEOUT_INSTRUCTION
Turn budget: 50 turns
Exit on: completion or blocking issue
"""
    return {
        "tool": "Task",
        "tool_input": {
            "prompt": valid_prompt,
            "max_turns": 30,  # Required per CLAUDE.md
        },
    }


@pytest.fixture
def invalid_task_json():
    """Provide invalid Task tool JSON that should be blocked.

    This prompt has the DES-VALIDATION marker but is missing all mandatory sections,
    so it should be blocked by prompt validation.
    """
    invalid_prompt = """<!-- DES-VALIDATION: required -->

# TASK_CONTEXT
This prompt is missing most mandatory sections and should be blocked.
"""
    return {
        "tool": "Task",
        "tool_input": {
            "prompt": invalid_prompt,
            "max_turns": 30,  # Has max_turns but prompt is invalid
        },
    }


@pytest.fixture
def hook_adapter_cli():
    """Return path to hook adapter CLI script."""
    # Return absolute path to work correctly even when working directory changes
    project_root = Path(__file__).parent.parent.parent.parent
    return (
        project_root
        / "src"
        / "des"
        / "adapters"
        / "drivers"
        / "hooks"
        / "claude_code_hook_adapter.py"
    )


@pytest.fixture
def installer_cli():
    """Return path to installer CLI script."""
    # Return absolute path to work correctly even when working directory changes
    project_root = Path(__file__).parent.parent.parent.parent
    return project_root / "scripts" / "install" / "install_des_hooks.py"


def run_cli_command(
    cli_path: Path, args: list[str], stdin_data: str | None = None
) -> subprocess.CompletedProcess:
    """
    Helper to run CLI commands with stdin and capture output.

    Args:
        cli_path: Path to CLI script
        args: Command arguments
        stdin_data: Optional stdin data as string

    Returns:
        CompletedProcess with returncode, stdout, stderr
    """
    import os

    cmd = [sys.executable, str(cli_path), *args]

    # Add src/ to PYTHONPATH for subprocess import resolution (des. package)
    env = os.environ.copy()
    project_root = str(Path(__file__).parent.parent.parent.parent)
    src_path = str(Path(project_root) / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        cmd,
        input=stdin_data.encode() if stdin_data else None,
        capture_output=True,
        text=False,
        env=env,
    )

    return result


@pytest.fixture
def cli_runner():
    """Provide CLI command runner helper."""
    return run_cli_command


@pytest.fixture
def context():
    """Provide test context dictionary for sharing state between steps."""
    return {}


@pytest.fixture
def stub_adapter_exists():
    """Verify production stub hook adapter exists at expected path."""
    # Use absolute path to work correctly even when working directory changes
    project_root = Path(__file__).parent.parent.parent.parent
    adapter_file = (
        project_root
        / "src"
        / "des"
        / "adapters"
        / "drivers"
        / "hooks"
        / "claude_code_hook_adapter.py"
    )
    assert adapter_file.exists(), f"Production stub adapter not found at {adapter_file}"
    return adapter_file
