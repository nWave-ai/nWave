"""PreWrite/PreEdit handler — guards source file writes during deliver sessions.

The shell fast-path tests for deliver-session.json BEFORE invoking Python.
This handler only runs during active deliver sessions.

Extracted from claude_code_hook_adapter.py as part of P4 decomposition.
"""

import contextlib
import io
import json
import time
import uuid
from pathlib import Path

from des.adapters.driven.time.system_time import SystemTimeProvider
from des.adapters.drivers.hooks import des_task_signal, hook_protocol
from des.adapters.drivers.hooks.hook_protocol import (
    EXIT_CODE_TO_DECISION,
    STDERR_CAPTURE_MAX_CHARS,
    log_hook_completed,
    log_hook_error,
    log_hook_invoked,
    read_and_parse_stdin,
)
from des.domain.session_guard_policy import SessionGuardPolicy
from des.ports.driven_ports.audit_log_writer import AuditEvent


def _log_pre_write_decision(
    hook_id: str,
    event_type: str,
    file_path: str,
    reason: str,
) -> None:
    """Log a HOOK_PRE_WRITE_ALLOWED or HOOK_PRE_WRITE_BLOCKED diagnostic event."""
    try:
        audit_writer = hook_protocol.get_audit_writer()
        audit_writer.log_event(
            AuditEvent(
                event_type=event_type,
                timestamp=SystemTimeProvider().now_utc().isoformat(),
                data={
                    "hook_id": hook_id,
                    "file_path": file_path,
                    "reason": reason,
                },
            )
        )
    except Exception:
        pass  # Diagnostic logging must never break the hook


def handle_pre_write() -> int:
    """Handle PreToolUse for Write/Edit: guard source writes during deliver.

    Shell fast-path: the hook command tests for deliver-session.json BEFORE
    invoking Python. This handler only runs during active deliver sessions.

    Returns:
        0 if write is allowed
        2 if write is blocked (source file during deliver without DES task)
    """
    hook_id = str(uuid.uuid4())
    start_ns = time.perf_counter_ns()
    exit_code = 0
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr_buffer):
            stdin_result = read_and_parse_stdin(
                "pre_write",
                json_error_fallback="allow",
            )

            if stdin_result.is_empty:
                return 0

            if stdin_result.parse_error:
                # Write/Edit fails open on parse errors
                return 0

            hook_input = stdin_result.hook_input

            # Extract file path from tool_input
            tool_input = hook_input.get("tool_input", {})
            file_path = tool_input.get("file_path", "")

            # --- Execution log guard: always block direct writes ---
            if file_path and file_path.endswith("execution-log.json"):
                project_dir = (
                    str(Path(file_path).parent) if file_path else "{project-dir}"
                )
                tool_name = hook_input.get("tool_name", "")
                if tool_name == "Write":
                    block_reason = (
                        "Direct creation of execution-log.json is blocked.\n\n"
                        "Use the CLI to initialize the execution log:\n\n"
                        f"  des-init-log \\\n"
                        f"    --project-dir {project_dir} \\\n"
                        "    --feature-id {feature-id}\n\n"
                        "IMPORTANT: The execution log must be created through the CLI "
                        "to ensure correct schema."
                    )
                else:
                    block_reason = (
                        "Direct modification of execution-log.json is blocked.\n\n"
                        "Use the CLI to record phase outcomes after executing the step:\n\n"
                        f"  des-log-phase \\\n"
                        f"    --project-dir {project_dir} \\\n"
                        "    --step-id {step-id} \\\n"
                        "    --phase {phase} \\\n"
                        "    --status EXECUTED \\\n"
                        "    --data PASS\n\n"
                        "IMPORTANT: The step must be executed and completed successfully "
                        "BEFORE\n"
                        "logging. The execution log records outcomes — it does not drive "
                        "execution."
                    )
                _log_pre_write_decision(
                    hook_id=hook_id,
                    event_type="HOOK_PRE_WRITE_BLOCKED",
                    file_path=file_path,
                    reason="execution_log_direct_write",
                )
                print(json.dumps({"decision": "block", "reason": block_reason}))
                return 2

            # Check session and signal state
            session_active = des_task_signal.DES_DELIVER_SESSION_FILE.exists()
            des_task_active = des_task_signal.DES_TASK_ACTIVE_FILE.exists()

            # Diagnostic: confirm hook was invoked with full context
            log_hook_invoked(
                "pre_write",
                {
                    "file_path": file_path,
                    "session_active": session_active,
                    "des_task_active": des_task_active,
                },
                hook_id=hook_id,
            )

            policy = SessionGuardPolicy()
            guard_result = policy.check(
                file_path=file_path,
                session_active=session_active,
                des_task_active=des_task_active,
            )

            if guard_result.blocked:
                _log_pre_write_decision(
                    hook_id=hook_id,
                    event_type="HOOK_PRE_WRITE_BLOCKED",
                    file_path=file_path,
                    reason=guard_result.reason or "Source write blocked during deliver",
                )
                response = {
                    "decision": "block",
                    "reason": guard_result.reason
                    or "Source write blocked during deliver",
                }
                print(json.dumps(response))
                exit_code = 2
                return exit_code
            else:
                # Determine allow reason for diagnostics
                allow_reason = "no_session" if not session_active else "policy_allowed"
                _log_pre_write_decision(
                    hook_id=hook_id,
                    event_type="HOOK_PRE_WRITE_ALLOWED",
                    file_path=file_path,
                    reason=allow_reason,
                )
                exit_code = 0
                return exit_code

    except Exception as e:
        # Fail-open for Write/Edit (unlike Task which is fail-closed)
        stderr_capture = stderr_buffer.getvalue()[:STDERR_CAPTURE_MAX_CHARS]
        log_hook_error(
            "pre_write",
            e,
            stderr_capture,
        )
        exit_code = 0
        return exit_code
    finally:
        duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        decision_str = EXIT_CODE_TO_DECISION.get(exit_code, "error")
        log_hook_completed(
            hook_id=hook_id,
            handler="pre_write",
            exit_code=exit_code,
            decision=decision_str,
            duration_ms=duration_ms,
        )
