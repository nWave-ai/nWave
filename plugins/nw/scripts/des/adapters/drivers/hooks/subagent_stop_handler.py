"""SubagentStop handler — validates step completion after sub-agent returns.

Translates Claude Code's SubagentStop hook event (JSON stdin) into
SubagentStopService decisions (allow/block). Extracts DES context from
agent transcripts, manages signal file lifecycle, and emits audit events.

Extracted from claude_code_hook_adapter.py as part of P4 decomposition.
"""

import contextlib
import io
import json
import os
import sys
import time
import uuid
from pathlib import Path

from des.adapters.driven.logging.audit_events import (
    AgentUsageObservedEvent,
    EventType,
)
from des.adapters.driven.time.system_time import SystemTimeProvider
from des.adapters.drivers.hooks import des_task_signal, hook_protocol, service_factory
from des.adapters.drivers.hooks.execution_log_resolver import resolve_execution_log_path
from des.adapters.drivers.hooks.hook_protocol import (
    EXIT_CODE_TO_DECISION,
    STDERR_CAPTURE_MAX_CHARS,
    log_hook_completed,
    log_hook_error,
    log_hook_invoked,
    read_and_parse_stdin,
)
from des.adapters.drivers.hooks.project_root_validator import validate_project_root
from des.adapters.drivers.hooks.skill_tracking_hooks import (
    maybe_track_skill_loads as _maybe_track_skill_loads,
)
from des.adapters.drivers.hooks.token_usage_extractor import (
    extract_token_usage_events,
)
from des.domain.des_marker_parser import DesMarkerParser
from des.ports.driven_ports.audit_log_writer import AuditEvent


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
        hook_protocol.get_audit_writer().log_event(
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
        dict with "project_id", "step_id" and optional "project_root" if DES
        markers found, None otherwise. "project_root" carries the raw marker
        value (validation happens at the caller, before path resolution).
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
                        "project_root": markers.project_root,
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
) -> tuple[str, str, str, str | None, str] | tuple[None, dict, int]:
    """Resolve DES context from hook input.

    Supports two protocols:
    1. Direct DES format (CLI testing): {"executionLogPath", "projectId", "stepId"}
    2. Claude Code protocol (live hooks): {"agent_transcript_path", "cwd", ...}

    Path-resolution priority for the Claude Code protocol:
      - validated DES-PROJECT-ROOT marker  >  hook_input["cwd"]  (fallback)

    Validation (project_root_validator): absolute path + exists + git work tree
    + git-common-dir matches fallback cwd. Invalid marker degrades to cwd.

    Returns:
        On success: (execution_log_path, project_id, step_id, project_root_marker,
                     effective_cwd)
            project_root_marker is the raw marker value when present (regardless
            of validation outcome), None otherwise. Used for audit-log emission.
            effective_cwd is the resolved working directory (validated marker
            value or hook_input cwd fallback). Used for git-trailer commit
            verification.
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
        # Direct DES protocol has no cwd / no marker — use empty effective_cwd
        return execution_log_path, project_id, step_id, None, ""

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
    raw_marker = des_context.get("project_root")

    # Marker-aware effective cwd: validate marker → use; else fall back to cwd
    effective_cwd = cwd
    if raw_marker:
        validated = validate_project_root(raw_marker, cwd)
        if validated is not None:
            effective_cwd = str(validated)

    try:
        from pathlib import Path as _Path

        resolved = resolve_execution_log_path(
            project_id,
            base=_Path(effective_cwd) / "docs" / "feature",
        )
        execution_log_path = str(resolved)
    except (FileNotFoundError, ValueError) as exc:
        # No log found or ambiguous — fall back to deliver/ path so downstream
        # validation produces a meaningful "not found" error message.
        execution_log_path = os.path.join(
            effective_cwd,
            "docs",
            "feature",
            project_id,
            "deliver",
            "execution-log.json",
        )
        _ = exc  # error surfaced by SubagentStopService when log not found
    return execution_log_path, project_id, step_id, raw_marker, effective_cwd


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

IMPORTANT: Only the executing agent may write to execution-log.json.
The orchestrator must RE-DISPATCH the agent to execute missing phases.
Never write log entries for phases that were not actually executed."""

    return {
        "decision": "block",
        "reason": notification,
    }


def _read_transcript_entries(transcript_path: str) -> list[dict]:
    """Parse a transcript JSONL file into a list of dict entries.

    Fail-open: malformed lines are skipped silently. Missing file yields
    empty list. Never raises.
    """
    path = Path(transcript_path)
    if not path.exists():
        return []
    entries: list[dict] = []
    try:
        with open(path) as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(entry, dict):
                    entries.append(entry)
    except (OSError, PermissionError):
        return []
    return entries


def _emit_token_usage_events(
    transcript_path: str | None,
    *,
    agent_name: str | None,
    feature_id: str | None = None,
    wave: str | None = None,
) -> None:
    """Read transcript, extract token-usage events, write each via the audit port.

    Per D4 (fail-open): any failure inside this routine is swallowed so
    the SubagentStop hook itself is never blocked by token instrumentation.
    """
    if not transcript_path:
        return
    try:
        entries = _read_transcript_entries(transcript_path)
        events = extract_token_usage_events(
            entries,
            agent_name=agent_name or "unknown",
            feature_id=feature_id,
            wave=wave,
        )
        if not events:
            return
        writer = hook_protocol.get_audit_writer()
        for event in events:
            writer.log_event(_to_audit_event(event))
    except Exception:
        # Fail-open: token instrumentation must never block the hook.
        pass


def _to_audit_event(event: AgentUsageObservedEvent) -> AuditEvent:
    """Convert a domain event to the port-level AuditEvent for logging."""
    return AuditEvent(
        event_type=EventType.AGENT_USAGE_OBSERVED.value,
        timestamp=event.timestamp or SystemTimeProvider().now_utc().isoformat(),
        feature_name=event.feature_id,
        data=event.to_audit_data(),
    )


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


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------


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
            stdin_result = read_and_parse_stdin("subagent_stop")

            if stdin_result.is_empty:
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
            log_hook_invoked(
                "subagent_stop",
                {
                    "agent_type": hook_input.get("agent_type"),
                    "agent_id": hook_input.get("agent_id"),
                    "has_transcript": hook_input.get("agent_transcript_path")
                    is not None,
                },
                hook_id=hook_id,
            )

            # L1 token instrumentation — additive walk of the same transcript.
            # Fail-open per D4: never blocks the hook on instrumentation errors.
            _emit_token_usage_events(
                hook_input.get("agent_transcript_path"),
                agent_name=hook_input.get("agent_type"),
            )

            # Resolve DES context from either protocol
            des_context_result = _resolve_des_context(hook_input)
            if des_context_result[0] is None:
                # Error or non-DES passthrough -- log it for diagnostics
                _, response, exit_code = des_context_result
                log_hook_invoked(
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
                return exit_code
            (
                execution_log_path,
                project_id,
                step_id,
                raw_marker,
                effective_cwd,
            ) = des_context_result

            # Audit enrichment (Rex pre-req #5): record the resolved
            # execution-log path and the DES-PROJECT-ROOT marker value so
            # post-hoc analysis can trace why a particular log was chosen.
            log_hook_invoked(
                "subagent_stop_resolved",
                {
                    "agent_type": hook_input.get("agent_type"),
                    "agent_id": hook_input.get("agent_id"),
                    "execution_log_path": execution_log_path,
                    "des_project_root_marker": raw_marker,
                    "project_id": project_id,
                    "step_id": step_id,
                },
                hook_id=hook_id,
            )

            # Read task_start_time and task_correlation_id from signal BEFORE removing it
            task_start_time = ""
            signal_data = des_task_signal.read_signal(
                project_id=project_id, step_id=step_id
            )
            if signal_data:
                task_start_time = signal_data.get("created_at", "")
                task_correlation_id = signal_data.get("task_correlation_id")

            # Clean up DES task signal (subagent finished)
            des_task_signal.remove_signal(project_id=project_id, step_id=step_id)

            # Delegate to application service
            from des.ports.driver_ports.subagent_stop_port import SubagentStopContext

            stop_hook_active = bool(hook_input.get("stop_hook_active", False))
            # Pass effective_cwd for commit verification: validated DES-PROJECT-
            # ROOT marker (worktree) when present, else hook_input cwd. This
            # ensures the commit-verifier inspects the repo where the crafter
            # actually committed, not the orchestrator's startup CWD.
            cwd = effective_cwd or hook_input.get("cwd", "")
            service = service_factory.create_subagent_stop_service()
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

            # Track skill loads from sub-agent transcript (fail-open)
            transcript_path = hook_input.get("agent_transcript_path")
            if transcript_path:
                _maybe_track_skill_loads(transcript_path)

            # Translate HookDecision to protocol response
            if decision.action == "allow":
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
        stderr_capture = stderr_buffer.getvalue()[:STDERR_CAPTURE_MAX_CHARS]
        log_hook_error(
            "subagent_stop",
            e,
            stderr_capture,
        )
        print(f"SubagentStop hook error: {e!s}", file=sys.stderr)
        exit_code = 1
        return exit_code
    finally:
        duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        decision_str = EXIT_CODE_TO_DECISION.get(exit_code, "error")
        log_hook_completed(
            hook_id=hook_id,
            handler="subagent_stop",
            exit_code=exit_code,
            decision=decision_str,
            duration_ms=duration_ms,
            task_correlation_id=task_correlation_id,
            turns_used=turns_used,
            tokens_used=tokens_used,
        )
