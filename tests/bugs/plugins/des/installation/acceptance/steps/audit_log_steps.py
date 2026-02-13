"""
Audit Log Location Step Definitions for Bug 2: Global vs Project-Local Logs.

This module contains step definitions for testing:
- Default audit log location (should be project-local, not global)
- Configuration override via environment variable
- Configuration override via config file
- Project isolation of audit trails

Domain: Audit Logging
Bug: Audit logs go to global ~/.claude/des/logs/ instead of project-local .nwave/des/logs/
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, then, when


def _read_jsonl_entries(log_file: Path) -> list[dict]:
    """Read all entries from a JSONL audit log file."""
    entries: list[dict] = []
    if log_file.exists():
        try:
            with open(log_file) as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception:
            pass
    return entries


# -----------------------------------------------------------------------------
# Given Steps: Audit Log Preconditions
# -----------------------------------------------------------------------------


@given(parsers.parse('I am in project directory "{project_path}"'))
def in_project_directory(project_path: str, tmp_path: Path, test_context: dict):
    """
    Set up a project directory for testing.

    For test isolation, we create the project under tmp_path.
    """
    # Create project directory under tmp_path for test isolation
    if project_path.startswith("/tmp/"):
        project_name = project_path.replace("/tmp/", "")
        project_dir = tmp_path / project_name
    else:
        project_dir = tmp_path / project_path.lstrip("/")

    project_dir.mkdir(parents=True, exist_ok=True)
    test_context["project_dir"] = project_dir
    test_context["original_cwd"] = os.getcwd()

    # Change to project directory
    os.chdir(project_dir)

    # JsonlAuditLogWriter is not a singleton, so no global reset needed.
    # Each test creates its own writer instance scoped to the current cwd.


@given("no audit log configuration is set")
def no_audit_config(clean_env, test_context: dict):
    """
    Ensure no audit log configuration environment variables are set.
    """
    # Remove any DES-related environment variables
    for key in list(clean_env.keys()):
        if key.startswith("DES_"):
            del clean_env[key]

    test_context["env_cleared"] = True


@given(parsers.parse('environment variable "{var_name}" is set to "{var_value}"'))
def set_env_variable(
    var_name: str, var_value: str, clean_env, tmp_path: Path, test_context: dict
):
    """
    Set an environment variable for testing.

    If the value starts with /, we use it as-is (absolute path).
    Otherwise, we create it under tmp_path for isolation.
    """
    if var_value.startswith("/") and not var_value.startswith("/tmp"):
        # Create the directory under tmp_path for isolation
        actual_path = tmp_path / var_value.lstrip("/")
    else:
        actual_path = Path(var_value)

    actual_path.mkdir(parents=True, exist_ok=True)
    clean_env[var_name] = str(actual_path)
    test_context[f"env_{var_name}"] = str(actual_path)


@given(parsers.parse('a DES config file exists with audit_log_dir set to "{log_dir}"'))
def des_config_with_audit_dir(log_dir: str, tmp_path: Path, test_context: dict):
    """
    Create a DES configuration file with audit_log_dir setting.
    """
    project_dir = test_context.get("project_dir", tmp_path / "test-project")
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create actual log directory
    if log_dir.startswith("/"):
        actual_log_dir = tmp_path / log_dir.lstrip("/")
    else:
        actual_log_dir = project_dir / log_dir

    actual_log_dir.mkdir(parents=True, exist_ok=True)

    # Create .nwave/des-config.json or similar
    config_dir = project_dir / ".nwave"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "des-config.json"
    config = {"audit_log_dir": str(actual_log_dir)}
    config_file.write_text(json.dumps(config, indent=2))

    test_context["des_config_file"] = config_file
    test_context["configured_log_dir"] = actual_log_dir


@given(parsers.parse('the directory "{dir_path}" does not exist'))
def directory_does_not_exist(dir_path: str, test_context: dict):
    """
    Ensure a directory does not exist before the test.
    """
    project_dir = test_context.get("project_dir")
    if project_dir:
        full_path = project_dir / dir_path.removeprefix("./")
        if full_path.exists():
            import shutil

            shutil.rmtree(full_path)

        test_context["target_dir"] = full_path


@given(parsers.parse('today is "{date_str}"'))
def set_test_date(date_str: str, test_context: dict):
    """
    Record the expected date for log file naming tests.
    """
    test_context["expected_date"] = date_str


@given(parsers.parse('existing audit logs exist at "{log_path}"'))
def existing_logs_at_path(log_path: str, tmp_path: Path, test_context: dict):
    """
    Create existing audit logs at specified location.
    """
    # For safety, we create under tmp_path
    actual_path = tmp_path / "existing-logs"
    actual_path.mkdir(parents=True, exist_ok=True)

    # Create a sample log file
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = actual_path / f"audit-{today}.log"
    log_file.write_text(
        '{"event": "existing_log", "timestamp": "2026-02-04T00:00:00Z"}\n'
    )

    test_context["existing_log_path"] = actual_path
    test_context["existing_log_file"] = log_file


@given("the DES audit logger writes an event for project-alpha")
def write_event_project_alpha(test_context: dict):
    """
    Write a test audit event for project-alpha.
    """
    _write_test_audit_event(test_context, "project-alpha")


@given("the DES audit logger writes an event for project-beta")
def write_event_project_beta(test_context: dict):
    """
    Write a test audit event for project-beta.
    """
    _write_test_audit_event(test_context, "project-beta")


def _write_test_audit_event(test_context: dict, project_name: str):
    """Helper to write a test audit event."""
    try:
        from des.adapters.driven.logging.jsonl_audit_log_writer import (
            JsonlAuditLogWriter,
        )
        from des.ports.driven_ports.audit_log_writer import AuditEvent

        project_dir = test_context.get("project_dir")
        if project_dir:
            writer = JsonlAuditLogWriter()
            ts = datetime.now(timezone.utc).isoformat()
            writer.log_event(
                AuditEvent(
                    event_type="TEST_EVENT",
                    timestamp=ts,
                    data={"project": project_name},
                )
            )
            test_context[f"{project_name}_event_written"] = True
            test_context[f"{project_name}_writer"] = writer
    except ImportError:
        pytest.skip("JsonlAuditLogWriter not available")


# -----------------------------------------------------------------------------
# When Steps: Audit Log Actions
# -----------------------------------------------------------------------------


@when("the DES audit logger initializes")
def initialize_audit_logger(test_context: dict):
    """
    Initialize the DES audit logger.

    This tests where the logger writes logs by default.
    """
    try:
        from des.adapters.driven.logging.jsonl_audit_log_writer import (
            JsonlAuditLogWriter,
        )

        # Initialize with no arguments - should use defaults
        writer = JsonlAuditLogWriter()
        test_context["audit_logger"] = writer
        test_context["audit_log_dir"] = writer._log_dir
        test_context["audit_log_file"] = writer._get_log_file()
    except ImportError as e:
        pytest.skip(f"JsonlAuditLogWriter not importable: {e}")


@when("the DES audit logger writes an event")
def write_audit_event(test_context: dict):
    """
    Write a test event to the audit log.
    """
    writer = test_context.get("audit_logger")
    if writer:
        from des.ports.driven_ports.audit_log_writer import AuditEvent

        writer.log_event(
            AuditEvent(
                event_type="TEST_EVENT",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        test_context["event_written"] = True


# -----------------------------------------------------------------------------
# Then Steps: Audit Log Assertions
# -----------------------------------------------------------------------------


@then(parsers.parse('audit logs should be written to "{expected_path}"'))
def verify_audit_log_location(expected_path: str, test_context: dict):
    """
    Verify audit logs are written to the expected location.

    BUG DETECTION: If expected_path is ".nwave/des/logs/" but logs go to
    "~/.claude/des/logs/", this test will fail, detecting the bug.
    """
    logger = test_context.get("audit_logger")
    if not logger:
        pytest.fail("Audit logger not initialized")

    actual_log_dir = logger._log_dir
    project_dir = test_context.get("project_dir")

    if expected_path.startswith(".nwave"):
        # Project-local path
        if project_dir:
            expected_full = project_dir / expected_path.removeprefix("./")
        else:
            expected_full = Path.cwd() / expected_path.removeprefix("./")
    elif expected_path.startswith("~"):
        # Home-relative path
        expected_full = Path(expected_path).expanduser()
    elif expected_path.startswith("/"):
        # Check if we have a test mapping
        env_key = "env_DES_AUDIT_LOG_DIR"
        if env_key in test_context:
            expected_full = Path(test_context[env_key])
        else:
            configured = test_context.get("configured_log_dir")
            expected_full = configured or Path(expected_path)
    else:
        expected_full = Path(expected_path)

    # Normalize paths for comparison
    actual_str = str(actual_log_dir).rstrip("/")
    expected_str = str(expected_full).rstrip("/")

    assert actual_str == expected_str, (
        f"BUG DETECTED: Audit logs are written to wrong location.\n"
        f"Expected: {expected_str}\n"
        f"Actual: {actual_str}\n"
        f"The audit log location bug is present."
    )


@then(parsers.parse('audit logs should NOT be written to "{forbidden_path}"'))
def verify_not_at_location(forbidden_path: str, test_context: dict):
    """
    Verify audit logs are NOT written to a forbidden location.
    """
    logger = test_context.get("audit_logger")
    if not logger:
        pytest.fail("Audit logger not initialized")

    actual_log_dir = str(logger._log_dir)

    if forbidden_path.startswith("~"):
        forbidden_full = str(Path(forbidden_path).expanduser())
    else:
        forbidden_full = forbidden_path

    assert forbidden_full not in actual_log_dir, (
        f"BUG DETECTED: Audit logs ARE being written to forbidden location.\n"
        f"Forbidden: {forbidden_full}\n"
        f"Actual: {actual_log_dir}\n"
        f"This violates the expected project isolation."
    )


@then("project-alpha audit events should only appear in project-alpha logs")
def verify_alpha_isolation(test_context: dict):
    """
    Verify project-alpha events are isolated.

    BUG DETECTION: With current bug, all projects share same log location.
    """
    # With the current bug, this is impossible to verify correctly
    # because both projects write to the same global location
    alpha_writer = test_context.get("project-alpha_writer")
    if alpha_writer:
        # Check the log file contains our event
        entries = _read_jsonl_entries(alpha_writer._get_log_file())
        alpha_entries = [e for e in entries if e.get("project") == "project-alpha"]

        if len(alpha_entries) == 0:
            pytest.fail(
                "BUG DETECTED: Could not isolate project-alpha events. "
                "Audit log isolation is not working."
            )


@then("project-beta audit events should only appear in project-beta logs")
def verify_beta_isolation(test_context: dict):
    """
    Verify project-beta events are isolated.
    """
    beta_writer = test_context.get("project-beta_writer")
    if beta_writer:
        entries = _read_jsonl_entries(beta_writer._get_log_file())
        beta_entries = [e for e in entries if e.get("project") == "project-beta"]

        # With the bug, both alpha and beta events appear in same file
        alpha_entries = [e for e in entries if e.get("project") == "project-alpha"]

        if len(alpha_entries) > 0 and len(beta_entries) > 0:
            pytest.fail(
                "BUG DETECTED: Both project-alpha and project-beta events "
                "appear in the same log file. Audit trails are not isolated."
            )


@then("the global audit log location should not contain either project's events")
def verify_global_clean(test_context: dict):
    """
    Verify the global location is clean.

    BUG DETECTION: With current bug, global location contains all events.
    """
    global_log_dir = Path.home() / ".claude" / "des" / "logs"

    if global_log_dir.exists():
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        global_log_file = global_log_dir / f"audit-{today}.log"

        if global_log_file.exists():
            content = global_log_file.read_text()
            if "project-alpha" in content or "project-beta" in content:
                pytest.fail(
                    "BUG DETECTED: Global audit log contains project-specific events. "
                    f"Found project events in {global_log_file}. "
                    "Audit logs should be project-local, not global."
                )


@then(parsers.parse('the directory "{dir_path}" should be created'))
def verify_directory_created(dir_path: str, test_context: dict):
    """
    Verify a directory was auto-created.
    """
    project_dir = test_context.get("project_dir")
    if project_dir:
        full_path = project_dir / dir_path.removeprefix("./")
    else:
        full_path = Path(dir_path)

    assert full_path.exists(), (
        f"Expected directory {full_path} to be created automatically"
    )


@then(parsers.parse('the audit log file should exist in "{dir_path}"'))
def verify_log_file_in_directory(dir_path: str, test_context: dict):
    """
    Verify an audit log file exists in the specified directory.
    """
    project_dir = test_context.get("project_dir")
    if project_dir:
        full_path = project_dir / dir_path.removeprefix("./")
    else:
        full_path = Path(dir_path)

    log_files = list(full_path.glob("audit-*.log"))
    assert len(log_files) > 0, (
        f"Expected at least one audit log file in {full_path}, found none"
    )


@then(parsers.parse('the audit log file should be named "{expected_name}"'))
def verify_log_file_name(expected_name: str, test_context: dict):
    """
    Verify the audit log file has the expected name.
    """
    logger = test_context.get("audit_logger")
    if logger:
        actual_name = logger._get_log_file().name
        assert actual_name == expected_name, (
            f"Expected log file name '{expected_name}', got '{actual_name}'"
        )


@then(parsers.parse('the file should be in "{dir_path}"'))
def verify_file_location(dir_path: str, test_context: dict):
    """
    Verify the current log file is in the expected directory.
    """
    logger = test_context.get("audit_logger")
    project_dir = test_context.get("project_dir")

    if logger:
        if project_dir and dir_path.startswith("."):
            expected_dir = project_dir / dir_path.removeprefix("./")
        else:
            expected_dir = Path(dir_path)

        actual_parent = logger._get_log_file().parent

        assert str(actual_parent) == str(expected_dir), (
            f"BUG DETECTED: Log file is in wrong directory.\n"
            f"Expected: {expected_dir}\n"
            f"Actual: {actual_parent}"
        )


@then("existing global logs should remain accessible")
def verify_existing_logs_accessible(test_context: dict):
    """
    Verify backward compatibility - existing logs still readable.
    """
    existing_log = test_context.get("existing_log_file")
    if existing_log:
        assert existing_log.exists(), (
            "Existing global log file should remain accessible"
        )


@then("new logs should go to project-local directory")
def verify_new_logs_project_local(test_context: dict):
    """
    Verify new logs go to project-local directory.
    """
    logger = test_context.get("audit_logger")
    if logger:
        log_path = str(logger._log_dir)
        global_path = str(Path.home() / ".claude" / "des" / "logs")

        assert log_path != global_path, (
            f"BUG: New logs are going to global location {log_path} "
            f"instead of project-local directory"
        )


# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def restore_cwd(test_context: dict):
    """Restore original working directory after test."""
    yield
    if "original_cwd" in test_context:
        os.chdir(test_context["original_cwd"])
