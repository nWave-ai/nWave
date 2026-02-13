#!/usr/bin/env python3
"""Claude Code hook adapter with DES integration.

This adapter bridges Claude Code's hook protocol (JSON stdin/stdout, exit codes)
to DES application services (PreToolUseService, SubagentStopService, PostToolUseService).

Protocol-only: no business logic here. All decisions delegated to application layer.

Commands:
  python3 -m src.des.adapters.drivers.hooks.claude_code_hook_adapter pre-tool-use
  python3 -m src.des.adapters.drivers.hooks.claude_code_hook_adapter subagent-stop
  python3 -m src.des.adapters.drivers.hooks.claude_code_hook_adapter post-tool-use

Exit Codes:
  0 = allow/continue
  1 = fail-closed error (BLOCKS execution)
  2 = block/reject (validation failed)

Protocol:
  - Input: JSON on stdin
  - Output: JSON on stdout
  - Fail-closed: Any error causes exit 1 (BLOCK)
"""

import contextlib
import io
import json
import os
import sys
import time
import uuid
from pathlib import Path


# Add project root to sys.path for standalone script execution
if __name__ == "__main__":
    project_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from des.adapters.driven.git.git_commit_verifier import GitCommitVerifier
from des.adapters.driven.hooks.yaml_execution_log_reader import (
    YamlExecutionLogReader,
)
from des.adapters.driven.logging.jsonl_audit_log_writer import JsonlAuditLogWriter
from des.adapters.driven.time.system_time import SystemTimeProvider
from des.adapters.driven.validation.git_scope_checker import GitScopeChecker
from des.application.pre_tool_use_service import PreToolUseService
from des.application.subagent_stop_service import SubagentStopService
from des.application.validator import TemplateValidator
from des.domain.des_enforcement_policy import DesEnforcementPolicy
from des.domain.des_marker_parser import DesMarkerParser
from des.domain.marker_completeness_policy import MarkerCompletenessPolicy
from des.domain.max_turns_policy import MaxTurnsPolicy
from des.domain.session_guard_policy import SessionGuardPolicy
from des.domain.step_completion_validator import StepCompletionValidator
from des.domain.tdd_schema import get_tdd_schema
from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter
from des.ports.driver_ports.pre_tool_use_port import PreToolUseInput


def _create_audit_writer() -> AuditLogWriter:
    """Create appropriate AuditLogWriter based on DES configuration.

    Returns JsonlAuditLogWriter by default,
    NullAuditLogWriter when explicitly disabled in .nwave/des-config.json.
    """
    from des.adapters.driven.config.des_config import DESConfig
    from des.adapters.driven.logging.null_audit_log_writer import NullAuditLogWriter

    config = DESConfig()
    if not config.audit_logging_enabled:
        return NullAuditLogWriter()
    return JsonlAuditLogWriter()


def create_pre_tool_use_service() -> PreToolUseService:
    """Create PreToolUseService with production dependencies.

    Returns:
        PreToolUseService configured for production use
    """
    time_provider = SystemTimeProvider()
    audit_writer = _create_audit_writer()

    return PreToolUseService(
        max_turns_policy=MaxTurnsPolicy(),
        marker_parser=DesMarkerParser(),
        prompt_validator=TemplateValidator(),
        audit_writer=audit_writer,
        time_provider=time_provider,
        enforcement_policy=DesEnforcementPolicy(),
        completeness_policy=MarkerCompletenessPolicy(),
    )


def create_subagent_stop_service() -> SubagentStopService:
    """Create SubagentStopService with production dependencies.

    Returns:
        SubagentStopService configured for production use
    """
    from des.domain.log_integrity_validator import LogIntegrityValidator

    time_provider = SystemTimeProvider()
    audit_writer = _create_audit_writer()
    schema = get_tdd_schema()

    return SubagentStopService(
        log_reader=YamlExecutionLogReader(),
        completion_validator=StepCompletionValidator(schema=schema),
        scope_checker=GitScopeChecker(),
        audit_writer=audit_writer,
        time_provider=time_provider,
        commit_verifier=GitCommitVerifier(),
        integrity_validator=LogIntegrityValidator(
            schema=schema, time_provider=time_provider
        ),
    )


def _log_hook_invoked(
    handler: str, summary: dict | None = None, hook_id: str | None = None
) -> None:
    """Log a HOOK_INVOKED diagnostic event at handler entry.

    This confirms the hook was actually called by Claude Code.
    Without this, silent passthrough is indistinguishable from hook-not-firing.

    Args:
        handler: Name of the handler being invoked.
        summary: Optional dict of input summary fields.
        hook_id: Optional UUID4 correlation ID. When provided, included in event data.
            When None, the field is omitted (backward compatible).
    """
    try:
        audit_writer = _create_audit_writer()
        data: dict = {"handler": handler}
        if hook_id is not None:
            data["hook_id"] = hook_id
        if summary:
            data["input_summary"] = summary
        audit_writer.log_event(
            AuditEvent(
                event_type="HOOK_INVOKED",
                timestamp=SystemTimeProvider().now_utc().isoformat(),
                data=data,
            )
        )
    except Exception:
        pass  # Diagnostic logging must never break the hook


# Threshold in milliseconds above which a hook is considered slow
_SLOW_HOOK_THRESHOLD_MS = 5000.0

# Maximum characters to capture from stderr in HOOK_ERROR events
_STDERR_CAPTURE_MAX_CHARS = 1000

_EXIT_CODE_TO_DECISION = {
    0: "allow",
    1: "error",
    2: "block",
}


def _log_hook_completed(
    hook_id: str,
    handler: str,
    exit_code: int,
    decision: str,
    duration_ms: float,
    task_correlation_id: str | None = None,
    turns_used: int | None = None,
    tokens_used: int | None = None,
) -> None:
    """Log a HOOK_COMPLETED diagnostic event at handler exit.

    Emitted in a finally block so it fires on allow, block, AND error paths.
    Wrapped in try/except so logging never breaks the hook.

    Args:
        hook_id: UUID4 correlation ID matching the HOOK_INVOKED event.
        handler: Name of the handler that completed.
        exit_code: Process exit code (0=allow, 1=error, 2=block).
        decision: Human-readable decision string.
        duration_ms: Wall-clock duration of the handler in milliseconds.
        task_correlation_id: Optional UUID4 linking events across the DES task lifecycle.
            When provided, included in event data. When None, the field is omitted.
        turns_used: Optional number of turns used by the subagent.
        tokens_used: Optional number of tokens used by the subagent.
    """
    try:
        audit_writer = _create_audit_writer()
        data: dict = {
            "hook_id": hook_id,
            "handler": handler,
            "exit_code": exit_code,
            "decision": decision,
            "duration_ms": duration_ms,
        }
        if duration_ms > _SLOW_HOOK_THRESHOLD_MS:
            data["slow_hook"] = True
        if task_correlation_id is not None:
            data["task_correlation_id"] = task_correlation_id
        if turns_used is not None:
            data["turns_used"] = turns_used
        if tokens_used is not None:
            data["tokens_used"] = tokens_used
        audit_writer.log_event(
            AuditEvent(
                event_type="HOOK_COMPLETED",
                timestamp=SystemTimeProvider().now_utc().isoformat(),
                data=data,
            )
        )
    except Exception:
        pass  # Diagnostic logging must never break the hook


def _log_protocol_anomaly(
    handler: str,
    anomaly_type: str,
    detail: str,
    fallback_action: str,
) -> None:
    """Log a HOOK_PROTOCOL_ANOMALY diagnostic event for early-return paths.

    Emitted when a handler receives empty stdin or malformed JSON, which are
    protocol-level anomalies that bypass normal business logic processing.
    Wrapped in try/except so anomaly logging never breaks the handler.

    Args:
        handler: Name of the handler (e.g., 'pre_tool_use', 'subagent_stop').
        anomaly_type: Classification of the anomaly ('empty_stdin' or 'json_parse_error').
        detail: Human-readable description of what happened.
        fallback_action: What the handler did ('allow' or 'error').
    """
    try:
        audit_writer = _create_audit_writer()
        audit_writer.log_event(
            AuditEvent(
                event_type="HOOK_PROTOCOL_ANOMALY",
                timestamp=SystemTimeProvider().now_utc().isoformat(),
                data={
                    "handler": handler,
                    "anomaly_type": anomaly_type,
                    "detail": detail,
                    "fallback_action": fallback_action,
                },
            )
        )
    except Exception:
        pass  # Anomaly logging must never break the handler


# ---------------------------------------------------------------------------
# L2 Extract: shared stdin parsing and error logging across all 4 handlers
# ---------------------------------------------------------------------------


class _StdinParseResult:
    """Result of reading and parsing JSON from stdin.

    Encapsulates three outcomes: empty stdin, JSON parse error, or success.
    """

    __slots__ = ("hook_input", "is_empty", "parse_error")

    def __init__(
        self,
        hook_input: dict | None = None,
        is_empty: bool = False,
        parse_error: str | None = None,
    ) -> None:
        self.hook_input = hook_input
        self.is_empty = is_empty
        self.parse_error = parse_error

    @property
    def ok(self) -> bool:
        """True when stdin was parsed successfully into a dict."""
        return self.hook_input is not None


def _read_and_parse_stdin(
    handler: str,
    json_error_fallback: str = "error",
) -> _StdinParseResult:
    """Read JSON from stdin with protocol anomaly logging.

    Handles the two protocol-level anomalies (empty stdin, malformed JSON)
    that every hook handler must deal with identically.

    Args:
        handler: Name of the calling handler for anomaly log context.
        json_error_fallback: Fallback action to log for JSON parse errors.
            Fail-closed handlers pass "error", fail-open handlers pass "allow".

    Returns:
        _StdinParseResult with either parsed hook_input, is_empty flag,
        or parse_error string.
    """
    input_data = sys.stdin.read()

    if not input_data or not input_data.strip():
        _log_protocol_anomaly(
            handler=handler,
            anomaly_type="empty_stdin",
            detail="No input data received on stdin",
            fallback_action="allow",
        )
        return _StdinParseResult(is_empty=True)

    try:
        hook_input = json.loads(input_data)
    except json.JSONDecodeError as e:
        _log_protocol_anomaly(
            handler=handler,
            anomaly_type="json_parse_error",
            detail=f"Invalid JSON: {e!s}",
            fallback_action=json_error_fallback,
        )
        return _StdinParseResult(parse_error=f"Invalid JSON: {e!s}")

    return _StdinParseResult(hook_input=hook_input)


def _log_hook_error(handler: str, error: Exception, stderr_capture: str) -> None:
    """Log a HOOK_ERROR audit event for unhandled exceptions in handlers.

    Extracted from the identical try/except blocks in all 4 handler exception paths.
    Wrapped in try/except so audit logging failure never masks the original error.

    Args:
        handler: Name of the handler that raised the exception.
        error: The unhandled exception.
        stderr_capture: Captured stderr content (already truncated by caller).
    """
    try:
        audit_writer = _create_audit_writer()
        audit_writer.log_event(
            AuditEvent(
                event_type="HOOK_ERROR",
                timestamp=SystemTimeProvider().now_utc().isoformat(),
                data={
                    "error": str(error),
                    "handler": handler,
                    "error_type": type(error).__name__,
                    "stderr_capture": stderr_capture,
                },
            )
        )
    except Exception:
        pass  # Don't let audit logging failure mask the original error


# ---------------------------------------------------------------------------
# DES task signal file management
# ---------------------------------------------------------------------------

DES_SESSION_DIR = Path(".nwave") / "des"
DES_DELIVER_SESSION_FILE = DES_SESSION_DIR / "deliver-session.json"
DES_TASK_ACTIVE_FILE = DES_SESSION_DIR / "des-task-active"


def _signal_file_for(project_id: str, step_id: str) -> Path:
    """Return the namespaced signal file path for a project/step pair."""
    safe_name = f"{project_id}--{step_id}".replace("/", "_")
    return DES_SESSION_DIR / f"des-task-active-{safe_name}"


def _create_des_task_signal(step_id: str = "", project_id: str = "") -> str:
    """Create DES task active signal file, namespaced by project/step.

    Called when PreToolUse allows a DES-validated Task.
    Indicates a DES subagent is currently running.

    Returns:
        task_correlation_id (UUID4 string) for correlating events across hooks.
        Returns empty string if signal creation fails.
    """
    task_correlation_id = str(uuid.uuid4())
    try:
        DES_SESSION_DIR.mkdir(parents=True, exist_ok=True)
        from datetime import datetime, timezone

        signal = json.dumps(
            {
                "step_id": step_id,
                "project_id": project_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "task_correlation_id": task_correlation_id,
            }
        )
        signal_file = _signal_file_for(project_id, step_id)
        signal_file.write_text(signal)
        # Also write legacy singleton for backward compatibility
        DES_TASK_ACTIVE_FILE.write_text(signal)
    except Exception:
        pass  # Signal creation must never break the hook
    return task_correlation_id


def _read_des_task_signal(project_id: str = "", step_id: str = "") -> dict | None:
    """Read DES task active signal file before removal.

    Tries namespaced file first, falls back to legacy singleton.

    Returns:
        Signal data dict with step_id, project_id, and created_at, or None.
    """
    try:
        # Try namespaced signal first (race-condition resistant)
        if project_id and step_id:
            namespaced = _signal_file_for(project_id, step_id)
            if namespaced.exists():
                return json.loads(namespaced.read_text())
        # Fallback to legacy singleton
        if DES_TASK_ACTIVE_FILE.exists():
            return json.loads(DES_TASK_ACTIVE_FILE.read_text())
    except Exception:
        pass
    return None


def _remove_des_task_signal(project_id: str = "", step_id: str = "") -> None:
    """Remove DES task active signal file(s).

    Called when SubagentStop fires (DES task completed).
    Removes both namespaced and legacy singleton files.
    """
    try:
        if project_id and step_id:
            namespaced = _signal_file_for(project_id, step_id)
            if namespaced.exists():
                namespaced.unlink()
        if DES_TASK_ACTIVE_FILE.exists():
            DES_TASK_ACTIVE_FILE.unlink()
    except Exception:
        pass  # Signal cleanup must never break the hook


# ---------------------------------------------------------------------------
# Handler: PreToolUse (Task validation)
# ---------------------------------------------------------------------------


def handle_pre_tool_use() -> int:
    """Handle PreToolUse command: validate Task tool invocation.

    Protocol translation only -- all decisions delegated to PreToolUseService.

    Returns:
        0 if validation passes (allow)
        1 if error occurs (fail-closed)
        2 if validation fails (block)
    """
    hook_id = str(uuid.uuid4())
    start_ns = time.perf_counter_ns()
    exit_code = 0
    task_correlation_id: str | None = None
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr_buffer):
            stdin_result = _read_and_parse_stdin("pre_tool_use")

            if stdin_result.is_empty:
                print(json.dumps({"decision": "allow"}))
                return 0

            if stdin_result.parse_error:
                response = {"status": "error", "reason": stdin_result.parse_error}
                print(json.dumps(response))
                exit_code = 1
                return exit_code

            hook_input = stdin_result.hook_input

            # Diagnostic: confirm hook was invoked
            tool_input = hook_input.get("tool_input", {})
            _log_hook_invoked(
                "pre_tool_use",
                {
                    "subagent_type": tool_input.get("subagent_type"),
                    "has_max_turns": tool_input.get("max_turns") is not None,
                },
                hook_id=hook_id,
            )

            # Extract protocol fields
            # Claude Code sends: {"tool_name": "Task", "tool_input": {...}, ...}
            prompt = tool_input.get("prompt", "")
            max_turns = tool_input.get("max_turns")

            # Delegate to application service
            service = create_pre_tool_use_service()
            decision = service.validate(
                PreToolUseInput(
                    prompt=prompt,
                    max_turns=max_turns,
                    subagent_type=tool_input.get("subagent_type"),
                ),
                hook_id=hook_id,
            )

            # Translate HookDecision to protocol response
            if decision.action == "allow":
                # Create DES task signal if this is a DES-validated task
                if "DES-VALIDATION" in prompt:
                    # Extract step-id and project-id from DES markers
                    step_id_marker = ""
                    project_id_marker = ""
                    parser = DesMarkerParser()
                    markers = parser.parse(prompt)
                    if markers.step_id:
                        step_id_marker = markers.step_id
                    if markers.project_id:
                        project_id_marker = markers.project_id
                    task_correlation_id = _create_des_task_signal(
                        step_id=step_id_marker, project_id=project_id_marker
                    )
                response = {"decision": "allow"}
                print(json.dumps(response))
                exit_code = 0
                return exit_code
            else:
                recovery = decision.recovery_suggestions or []
                reason_with_recovery = decision.reason or "Validation failed"
                if recovery:
                    reason_with_recovery += "\n\nRecovery:\n" + "\n".join(
                        f"  {i + 1}. {s}" for i, s in enumerate(recovery)
                    )
                response = {
                    "decision": "block",
                    "reason": reason_with_recovery,
                }
                print(json.dumps(response))
                exit_code = decision.exit_code
                return exit_code

    except Exception as e:
        # Fail-closed: any error blocks execution
        stderr_capture = stderr_buffer.getvalue()[:_STDERR_CAPTURE_MAX_CHARS]
        _log_hook_error("pre_tool_use", e, stderr_capture)
        response = {"status": "error", "reason": f"Unexpected error: {e!s}"}
        print(json.dumps(response))
        exit_code = 1
        return exit_code
    finally:
        duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        decision_str = _EXIT_CODE_TO_DECISION.get(exit_code, "error")
        _log_hook_completed(
            hook_id=hook_id,
            handler="pre_tool_use",
            exit_code=exit_code,
            decision=decision_str,
            duration_ms=duration_ms,
            task_correlation_id=task_correlation_id,
        )


# ---------------------------------------------------------------------------
# Transcript DES context extraction
# ---------------------------------------------------------------------------


def _normalize_message_content(content: object) -> str:
    """Normalize message content from string or list-of-text-blocks to plain string."""
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return content if isinstance(content, str) else ""


def _log_transcript_audit(
    event_type: str, transcript_path: str, **extra: object
) -> None:
    """Log a transcript-related audit event, silently swallowing failures."""
    try:
        _create_audit_writer().log_event(
            AuditEvent(
                event_type=event_type,
                timestamp=SystemTimeProvider().now_utc().isoformat(),
                data={"transcript_path": transcript_path, **extra},
            )
        )
    except Exception:
        pass


def extract_des_context_from_transcript(transcript_path: str) -> dict | None:
    """Extract DES markers from an agent's transcript file.

    Reads the JSONL transcript, finds the first user message (which contains
    the Task prompt), and extracts DES-PROJECT-ID and DES-STEP-ID markers.

    Args:
        transcript_path: Absolute path to the agent's transcript JSONL file

    Returns:
        dict with "project_id" and "step_id" if DES markers found, None otherwise
    """
    if not Path(transcript_path).exists():
        return None

    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                message = entry.get("message", {})
                if not isinstance(message, dict):
                    continue

                content = _normalize_message_content(message.get("content", ""))
                if "DES-VALIDATION" not in content:
                    continue

                markers = DesMarkerParser().parse(content)
                if markers.is_des_task and markers.project_id and markers.step_id:
                    return {
                        "project_id": markers.project_id,
                        "step_id": markers.step_id,
                    }
                return None

    except (OSError, PermissionError) as e:
        _log_transcript_audit("HOOK_TRANSCRIPT_ERROR", transcript_path, error=str(e))
        return None

    _log_transcript_audit("HOOK_TRANSCRIPT_NO_MARKERS", transcript_path)
    return None


# ---------------------------------------------------------------------------
# DES context resolution (direct protocol vs transcript-based)
# ---------------------------------------------------------------------------


def _resolve_des_context(
    hook_input: dict,
) -> tuple[str, str, str] | tuple[None, dict, int]:
    """Resolve DES context (execution_log_path, project_id, step_id) from hook input.

    Supports two protocols:
    1. Direct DES format (CLI testing): {"executionLogPath", "projectId", "stepId"}
    2. Claude Code protocol (live hooks): {"agent_transcript_path", "cwd", ...}

    Returns:
        On success: (execution_log_path, project_id, step_id)
        On error/passthrough: (None, response_dict, exit_code)
    """
    execution_log_path = hook_input.get("executionLogPath")
    project_id = hook_input.get("projectId")
    step_id = hook_input.get("stepId")

    uses_direct_des_protocol = execution_log_path or project_id or step_id

    if uses_direct_des_protocol:
        if not (execution_log_path and project_id and step_id):
            return (
                None,
                {
                    "status": "error",
                    "reason": "Missing required fields: executionLogPath, projectId, and stepId are all required",
                },
                1,
            )
        if not Path(execution_log_path).is_absolute():
            return (
                None,
                {
                    "status": "error",
                    "reason": f"executionLogPath must be absolute (got: {execution_log_path})",
                },
                1,
            )
        return execution_log_path, project_id, step_id

    # Claude Code protocol - extract DES context from transcript
    agent_transcript_path = hook_input.get("agent_transcript_path")
    cwd = hook_input.get("cwd", "")

    des_context = None
    if agent_transcript_path:
        des_context = extract_des_context_from_transcript(agent_transcript_path)

    if des_context is None:
        return None, {"decision": "allow"}, 0

    project_id = des_context["project_id"]
    step_id = des_context["step_id"]
    execution_log_path = os.path.join(
        cwd, "docs", "feature", project_id, "execution-log.yaml"
    )
    return execution_log_path, project_id, step_id


def _build_block_notification(
    project_id: str, step_id: str, execution_log_path: str, decision
) -> dict:
    """Build protocol response for a blocked subagent stop decision."""
    reason = decision.reason or "Validation failed"

    recovery_suggestions = decision.recovery_suggestions or []
    recovery_steps = "\n".join(
        [f"  {i + 1}. {s}" for i, s in enumerate(recovery_suggestions)]
    )

    notification = f"""STOP HOOK VALIDATION FAILED

Step: {project_id}/{step_id}
Execution Log: {execution_log_path}
Status: FAILED
Error: {reason}

RECOVERY REQUIRED:
{recovery_steps}

The step validation failed. You MUST fix these issues before proceeding.

IMPORTANT: Only the executing agent may write to execution-log.yaml.
The orchestrator must RE-DISPATCH the agent to execute missing phases.
Never write log entries for phases that were not actually executed."""

    return {
        "decision": "block",
        "reason": notification,
        "hookSpecificOutput": {
            "hookEventName": "SubagentStop",
            "additionalContext": notification,
        },
        "systemMessage": f"DES STEP INCOMPLETE [{project_id}/{step_id}]: {reason}",
    }


# ---------------------------------------------------------------------------
# Handler: SubagentStop (step completion validation)
# ---------------------------------------------------------------------------


def _extract_execution_stats(hook_input: dict) -> tuple[int | None, int | None]:
    """Extract turns_used and tokens_used from hook input.

    Claude Code may include num_turns and total_tokens in SubagentStop hook_input.

    Args:
        hook_input: Parsed JSON from stdin.

    Returns:
        Tuple of (turns_used, tokens_used), each None if not present.
    """
    turns_used: int | None = None
    tokens_used: int | None = None
    raw_turns = hook_input.get("num_turns")
    raw_tokens = hook_input.get("total_tokens")
    if raw_turns is not None:
        turns_used = int(raw_turns)
    if raw_tokens is not None:
        tokens_used = int(raw_tokens)
    return turns_used, tokens_used


def handle_subagent_stop() -> int:
    """Handle subagent-stop command: validate step completion.

    Protocol translation only -- all decisions delegated to SubagentStopService.

    Claude Code sends: {"agent_id", "agent_type", "agent_transcript_path", "cwd", ...}
    DES context (project_id, step_id) is extracted from the agent's transcript.
    Non-DES agents (no markers in transcript) are allowed through.

    Returns:
        0 if gate passes or non-DES agent
        1 if error occurs (fail-closed)
        2 if gate fails (BLOCKS orchestrator)
    """
    hook_id = str(uuid.uuid4())
    start_ns = time.perf_counter_ns()
    exit_code = 0
    task_correlation_id: str | None = None
    turns_used: int | None = None
    tokens_used: int | None = None
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr_buffer):
            stdin_result = _read_and_parse_stdin("subagent_stop")

            if stdin_result.is_empty:
                print(json.dumps({"decision": "allow"}))
                return 0

            if stdin_result.parse_error:
                response = {"status": "error", "reason": stdin_result.parse_error}
                print(json.dumps(response))
                exit_code = 1
                return exit_code

            hook_input = stdin_result.hook_input

            # Extract execution stats from hook_input
            turns_used, tokens_used = _extract_execution_stats(hook_input)

            # Diagnostic: confirm hook was invoked with agent details
            _log_hook_invoked(
                "subagent_stop",
                {
                    "agent_type": hook_input.get("agent_type"),
                    "agent_id": hook_input.get("agent_id"),
                    "has_transcript": hook_input.get("agent_transcript_path")
                    is not None,
                },
                hook_id=hook_id,
            )

            # Resolve DES context from either protocol
            des_context_result = _resolve_des_context(hook_input)
            if des_context_result[0] is None:
                # Error or non-DES passthrough -- log it for diagnostics
                _, response, exit_code = des_context_result
                _log_hook_invoked(
                    "subagent_stop_passthrough",
                    {
                        "reason": "non_des_or_error",
                        "agent_type": hook_input.get("agent_type"),
                        "agent_id": hook_input.get("agent_id"),
                        "has_transcript": hook_input.get("agent_transcript_path")
                        is not None,
                        "transcript_path": hook_input.get("agent_transcript_path"),
                        "exit_code": exit_code,
                    },
                    hook_id=hook_id,
                )
                print(json.dumps(response))
                return exit_code
            execution_log_path, project_id, step_id = des_context_result

            # Read task_start_time and task_correlation_id from signal BEFORE removing it
            task_start_time = ""
            signal_data = _read_des_task_signal(project_id=project_id, step_id=step_id)
            if signal_data:
                task_start_time = signal_data.get("created_at", "")
                task_correlation_id = signal_data.get("task_correlation_id")

            # Clean up DES task signal (subagent finished)
            _remove_des_task_signal(project_id=project_id, step_id=step_id)

            # Delegate to application service
            from des.ports.driver_ports.subagent_stop_port import SubagentStopContext

            stop_hook_active = bool(hook_input.get("stop_hook_active", False))
            # Pass cwd for commit verification from both protocols.
            # Claude Code sends cwd in hook input JSON.
            cwd = hook_input.get("cwd", "")
            service = create_subagent_stop_service()
            decision = service.validate(
                SubagentStopContext(
                    execution_log_path=execution_log_path,
                    project_id=project_id,
                    step_id=step_id,
                    stop_hook_active=stop_hook_active,
                    cwd=cwd,
                    task_start_time=task_start_time,
                    turns_used=turns_used,
                    tokens_used=tokens_used,
                ),
                hook_id=hook_id,
            )

            # Translate HookDecision to protocol response
            if decision.action == "allow":
                print(json.dumps({"decision": "allow"}))
                exit_code = 0
                return exit_code

            response = _build_block_notification(
                project_id, step_id, execution_log_path, decision
            )
            print(json.dumps(response))
            # Exit 0 so Claude Code processes the JSON (exit 2 ignores stdout)
            exit_code = 0
            return exit_code

    except Exception as e:
        # Fail-closed: any error blocks execution via stderr + exit 1
        stderr_capture = stderr_buffer.getvalue()[:_STDERR_CAPTURE_MAX_CHARS]
        _log_hook_error("subagent_stop", e, stderr_capture)
        print(f"SubagentStop hook error: {e!s}", file=sys.stderr)
        exit_code = 1
        return exit_code
    finally:
        duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        decision_str = _EXIT_CODE_TO_DECISION.get(exit_code, "error")
        _log_hook_completed(
            hook_id=hook_id,
            handler="subagent_stop",
            exit_code=exit_code,
            decision=decision_str,
            duration_ms=duration_ms,
            task_correlation_id=task_correlation_id,
            turns_used=turns_used,
            tokens_used=tokens_used,
        )


# ---------------------------------------------------------------------------
# Handler: PostToolUse (failure notification injection)
# ---------------------------------------------------------------------------


def handle_post_tool_use() -> int:
    """Handle post-tool-use command: notify parent of sub-agent failures.

    Reads the audit log for the most recent HOOK_SUBAGENT_STOP_FAILED entry.
    If found, injects additionalContext into the parent's conversation so
    the orchestrator knows a sub-agent failed.

    Protocol translation only -- business logic in PostToolUseService.

    Returns:
        0 always (PostToolUse should never block)
    """
    hook_id = str(uuid.uuid4())
    start_ns = time.perf_counter_ns()
    exit_code = 0
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr_buffer):
            stdin_result = _read_and_parse_stdin(
                "post_tool_use", json_error_fallback="allow"
            )

            if stdin_result.is_empty:
                print(json.dumps({}))
                return 0

            if stdin_result.parse_error:
                # PostToolUse fails open on parse errors
                print(json.dumps({}))
                return 0

            hook_input = stdin_result.hook_input

            # Diagnostic: confirm hook was invoked
            _log_hook_invoked(
                "post_tool_use",
                {
                    "tool_name": hook_input.get("tool_name"),
                },
                hook_id=hook_id,
            )

            # Check if the just-completed Task was a DES task (had DES markers)
            tool_input = hook_input.get("tool_input", {})
            prompt = tool_input.get("prompt", "")
            is_des_task = "DES-VALIDATION" in prompt

            # Delegate to PostToolUseService
            from des.adapters.driven.logging.jsonl_audit_log_reader import (
                JsonlAuditLogReader,
            )
            from des.application.post_tool_use_service import PostToolUseService

            reader = JsonlAuditLogReader()
            service = PostToolUseService(audit_reader=reader)
            additional_context = service.check_completion_status(
                is_des_task=is_des_task,
            )

            if additional_context:
                # Determine context_type from content
                if "INCOMPLETE" in additional_context or "FAILED" in additional_context:
                    context_type = "failure_notification"
                else:
                    context_type = "continuation"
                _log_post_tool_use_decision(
                    hook_id=hook_id,
                    event_type="HOOK_POST_TOOL_USE_INJECTED",
                    is_des_task=is_des_task,
                    context_type=context_type,
                )
                response = {"additionalContext": additional_context}
            else:
                reason = "no_completion_status" if is_des_task else "non_des_task"
                _log_post_tool_use_decision(
                    hook_id=hook_id,
                    event_type="HOOK_POST_TOOL_USE_PASSTHROUGH",
                    is_des_task=is_des_task,
                    reason=reason,
                )
                response = {}

            print(json.dumps(response))
            return 0

    except Exception as e:
        # PostToolUse should never block - fail open
        stderr_capture = stderr_buffer.getvalue()[:_STDERR_CAPTURE_MAX_CHARS]
        _log_hook_error("post_tool_use", e, stderr_capture)
        print(json.dumps({}))
        return 0
    finally:
        duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        decision_str = _EXIT_CODE_TO_DECISION.get(exit_code, "error")
        _log_hook_completed(
            hook_id=hook_id,
            handler="post_tool_use",
            exit_code=exit_code,
            decision=decision_str,
            duration_ms=duration_ms,
        )


# ---------------------------------------------------------------------------
# Handler-specific diagnostic loggers
# ---------------------------------------------------------------------------


def _log_pre_write_decision(
    hook_id: str,
    event_type: str,
    file_path: str,
    reason: str,
) -> None:
    """Log a HOOK_PRE_WRITE_ALLOWED or HOOK_PRE_WRITE_BLOCKED diagnostic event.

    Emitted after SessionGuardPolicy check to record the decision with context.
    Wrapped in try/except so logging never breaks the hook.

    Args:
        hook_id: UUID4 correlation ID matching the HOOK_INVOKED event.
        event_type: Either HOOK_PRE_WRITE_ALLOWED or HOOK_PRE_WRITE_BLOCKED.
        file_path: Path of the file being written.
        reason: Why the write was allowed or blocked.
    """
    try:
        audit_writer = _create_audit_writer()
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


def _log_post_tool_use_decision(
    hook_id: str,
    event_type: str,
    is_des_task: bool,
    **extra: str,
) -> None:
    """Log a HOOK_POST_TOOL_USE_INJECTED or HOOK_POST_TOOL_USE_PASSTHROUGH event.

    Emitted after PostToolUseService.check_completion_status() to record
    whether context was injected or not. Wrapped in try/except so logging
    never breaks the hook.

    Args:
        hook_id: UUID4 correlation ID matching the HOOK_INVOKED event.
        event_type: Either HOOK_POST_TOOL_USE_INJECTED or HOOK_POST_TOOL_USE_PASSTHROUGH.
        is_des_task: Whether the just-completed Task had DES markers.
        **extra: Additional key-value pairs (context_type, reason, etc.).
    """
    try:
        audit_writer = _create_audit_writer()
        data: dict = {
            "hook_id": hook_id,
            "is_des_task": is_des_task,
        }
        data.update(extra)
        audit_writer.log_event(
            AuditEvent(
                event_type=event_type,
                timestamp=SystemTimeProvider().now_utc().isoformat(),
                data=data,
            )
        )
    except Exception:
        pass  # Decision logging must never break the hook


# ---------------------------------------------------------------------------
# Handler: PreWrite/PreEdit (session guard)
# ---------------------------------------------------------------------------


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
            stdin_result = _read_and_parse_stdin(
                "pre_write", json_error_fallback="allow"
            )

            if stdin_result.is_empty:
                print(json.dumps({"decision": "allow"}))
                return 0

            if stdin_result.parse_error:
                # Write/Edit fails open on parse errors
                print(json.dumps({"decision": "allow"}))
                return 0

            hook_input = stdin_result.hook_input

            # Extract file path from tool_input
            tool_input = hook_input.get("tool_input", {})
            file_path = tool_input.get("file_path", "")

            # Check session and signal state
            session_active = DES_DELIVER_SESSION_FILE.exists()
            des_task_active = DES_TASK_ACTIVE_FILE.exists()

            # Diagnostic: confirm hook was invoked with full context
            _log_hook_invoked(
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
                print(json.dumps({"decision": "allow"}))
                exit_code = 0
                return exit_code

    except Exception as e:
        # Fail-open for Write/Edit (unlike Task which is fail-closed)
        stderr_capture = stderr_buffer.getvalue()[:_STDERR_CAPTURE_MAX_CHARS]
        _log_hook_error("pre_write", e, stderr_capture)
        print(json.dumps({"decision": "allow"}))
        exit_code = 0
        return exit_code
    finally:
        duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        decision_str = _EXIT_CODE_TO_DECISION.get(exit_code, "error")
        _log_hook_completed(
            hook_id=hook_id,
            handler="pre_write",
            exit_code=exit_code,
            decision=decision_str,
            duration_ms=duration_ms,
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Hook adapter entry point - routes command to appropriate handler."""
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "status": "error",
                    "reason": "Missing command argument (pre-tool-use or subagent-stop)",
                }
            )
        )
        sys.exit(1)

    command = sys.argv[1]

    if command in ("pre-tool-use", "pre-task"):
        # "pre-task" accepted for backward compatibility
        exit_code = handle_pre_tool_use()
    elif command == "subagent-stop":
        exit_code = handle_subagent_stop()
    elif command == "post-tool-use":
        exit_code = handle_post_tool_use()
    elif command in ("pre-write", "pre-edit"):
        exit_code = handle_pre_write()
    else:
        print(json.dumps({"status": "error", "reason": f"Unknown command: {command}"}))
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
