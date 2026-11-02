"""Shared hook protocol infrastructure for the kept hook handlers.

Provides the common building blocks used by all hook handlers:
- Audit writer factory
- Stdin parsing with protocol anomaly logging
- Diagnostic event loggers (invoked, completed, error, anomaly)
- Protocol constants (exit codes, thresholds)

All audit-aware functions accept an ``audit_writer_factory`` callable so the
caller can control which writer is used. Moved verbatim from the removed DES
runtime (S5-OQ6); the host payload mapping keeps the same argv and stdin contract.
"""

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass

from nwave_ai.hooks.audit import (
    AuditEvent,
    AuditLogWriter,
    JsonlAuditLogWriter,
    JsonlNWaveLogWriter,
    LogLevel,
    NullAuditLogWriter,
    NullNWaveLogWriter,
)
from nwave_ai.hooks.run_context import SystemTimeProvider
from nwave_ai.platform.config import NWaveConfig


# ---------------------------------------------------------------------------
# Audit writer factory (default implementation)
# ---------------------------------------------------------------------------


def create_audit_writer() -> AuditLogWriter:
    """Create appropriate AuditLogWriter based on nWave configuration.

    Returns JsonlAuditLogWriter by default,
    NullAuditLogWriter when explicitly disabled in .nwave/config.json.
    """
    config = NWaveConfig()
    if not config.audit_logging_enabled:
        return NullAuditLogWriter()
    return JsonlAuditLogWriter()


# Type alias for the factory callable accepted by all audit-aware functions
AuditWriterFactory = Callable[[], AuditLogWriter]

# Module-level factory variable -- the single patch point for tests.
# Tests patch ``hosts._audit_writer_factory`` to inject spy writers.
_audit_writer_factory: AuditWriterFactory = create_audit_writer


def get_audit_writer() -> AuditLogWriter:
    """Get an audit writer using the currently registered factory."""
    return _audit_writer_factory()


def _get_nwave_log_writer(config: object) -> object:
    """Create appropriate NWaveLogWriter based on nWave configuration.

    Returns JsonlNWaveLogWriter when logging is enabled,
    NullNWaveLogWriter otherwise.
    """
    if not config.log_enabled:
        return NullNWaveLogWriter()

    level_str = config.log_level.upper()
    level = LogLevel[level_str] if level_str in LogLevel.__members__ else LogLevel.WARN
    return JsonlNWaveLogWriter(level=level)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Threshold in milliseconds above which a hook is considered slow
SLOW_HOOK_THRESHOLD_MS = 5000.0

# Maximum characters to capture from stderr in HOOK_ERROR events
STDERR_CAPTURE_MAX_CHARS = 1000

EXIT_CODE_TO_DECISION = {
    0: "allow",
    1: "error",
    2: "block",
}


# ---------------------------------------------------------------------------
# Stdin parsing
# ---------------------------------------------------------------------------


class StdinParseResult:
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


def read_and_parse_stdin(
    handler: str,
    json_error_fallback: str = "error",
    *,
    audit_writer_factory: AuditWriterFactory | None = None,
) -> StdinParseResult:
    """Read JSON from stdin with protocol anomaly logging.

    Handles the two protocol-level anomalies (empty stdin, malformed JSON)
    that every hook handler must deal with identically.

    Args:
        handler: Name of the calling handler for anomaly log context.
        json_error_fallback: Fallback action to log for JSON parse errors.
            Fail-closed handlers pass "error", fail-open handlers pass "allow".
        audit_writer_factory: Callable returning an AuditLogWriter.
            Falls back to ``create_audit_writer`` if None.

    Returns:
        StdinParseResult with either parsed hook_input, is_empty flag,
        or parse_error string.
    """
    factory = audit_writer_factory or _audit_writer_factory
    input_data = sys.stdin.read()

    if not input_data or not input_data.strip():
        log_protocol_anomaly(
            handler=handler,
            anomaly_type="empty_stdin",
            detail="No input data received on stdin",
            fallback_action="allow",
            audit_writer_factory=factory,
        )
        return StdinParseResult(is_empty=True)

    try:
        hook_input = json.loads(input_data)
    except json.JSONDecodeError as e:
        log_protocol_anomaly(
            handler=handler,
            anomaly_type="json_parse_error",
            detail=f"Invalid JSON: {e!s}",
            fallback_action=json_error_fallback,
            audit_writer_factory=factory,
        )
        return StdinParseResult(parse_error=f"Invalid JSON: {e!s}")

    return StdinParseResult(hook_input=hook_input)


def extract_transcript_path(hook_input: dict) -> str | None:
    """Validated optional ``transcript_path`` from a raw hook_input dict.

    The raw dict from ``StdinParseResult.hook_input`` is preserved as-is for
    every existing caller; this is a side reader, not a wrapper. Returns the
    path only when present and a non-empty string, else None.
    """
    value = hook_input.get("transcript_path")
    return value if isinstance(value, str) and value else None


# ---------------------------------------------------------------------------
# Diagnostic event loggers
# ---------------------------------------------------------------------------


def log_hook_invoked(
    handler: str,
    summary: dict | None = None,
    hook_id: str | None = None,
    *,
    audit_writer_factory: AuditWriterFactory | None = None,
) -> None:
    """Log a HOOK_INVOKED diagnostic event at handler entry.

    This confirms the hook was actually called by the host. Without this,
    silent passthrough is indistinguishable from hook-not-firing.

    Args:
        handler: Name of the handler being invoked.
        summary: Optional dict of input summary fields.
        hook_id: Optional UUID4 correlation ID. When provided, included in event data.
            When None, the field is omitted (backward compatible).
        audit_writer_factory: Callable returning an AuditLogWriter.
    """
    try:
        factory = audit_writer_factory or _audit_writer_factory
        audit_writer = factory()
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


@dataclass(frozen=True)
class HookCompletion:
    """The completion event itself: what happened and how long it took."""

    hook_id: str
    handler: str
    exit_code: int
    decision: str
    duration_ms: float


@dataclass(frozen=True)
class TaskAccounting:
    """Optional task-lifecycle accounting linked to a HOOK_COMPLETED event."""

    task_correlation_id: str | None = None
    turns_used: int | None = None
    tokens_used: int | None = None


def log_hook_completed(
    completion: HookCompletion,
    accounting: TaskAccounting | None = None,
    *,
    audit_writer_factory: AuditWriterFactory | None = None,
) -> None:
    """Log a HOOK_COMPLETED diagnostic event at handler exit.

    Emitted in a finally block so it fires on allow, block, AND error paths.
    Wrapped in try/except so logging never breaks the hook.

    Args:
        completion: The completion event (hook_id, handler, exit_code,
            decision, duration_ms).
        accounting: Optional task-lifecycle accounting (task_correlation_id,
            turns_used, tokens_used), linking events across the task lifecycle.
        audit_writer_factory: Callable returning an AuditLogWriter.
    """
    try:
        factory = audit_writer_factory or _audit_writer_factory
        audit_writer = factory()
        data: dict = {
            "hook_id": completion.hook_id,
            "handler": completion.handler,
            "exit_code": completion.exit_code,
            "decision": completion.decision,
            "duration_ms": completion.duration_ms,
        }
        if completion.duration_ms > SLOW_HOOK_THRESHOLD_MS:
            data["slow_hook"] = True
        if accounting is not None:
            if accounting.task_correlation_id is not None:
                data["task_correlation_id"] = accounting.task_correlation_id
            if accounting.turns_used is not None:
                data["turns_used"] = accounting.turns_used
            if accounting.tokens_used is not None:
                data["tokens_used"] = accounting.tokens_used
        audit_writer.log_event(
            AuditEvent(
                event_type="HOOK_COMPLETED",
                timestamp=SystemTimeProvider().now_utc().isoformat(),
                data=data,
            )
        )
    except Exception:
        pass  # Diagnostic logging must never break the hook


def log_protocol_anomaly(
    handler: str,
    anomaly_type: str,
    detail: str,
    fallback_action: str,
    *,
    audit_writer_factory: AuditWriterFactory | None = None,
) -> None:
    """Log a HOOK_PROTOCOL_ANOMALY diagnostic event for early-return paths.

    Args:
        handler: Name of the handler (e.g., 'pre_tool_use', 'subagent_stop').
        anomaly_type: Classification of the anomaly ('empty_stdin' or 'json_parse_error').
        detail: Human-readable description of what happened.
        fallback_action: What the handler did ('allow' or 'error').
        audit_writer_factory: Callable returning an AuditLogWriter.
    """
    try:
        factory = audit_writer_factory or _audit_writer_factory
        audit_writer = factory()
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


def log_hook_error(
    handler: str,
    error: Exception,
    stderr_capture: str,
    *,
    audit_writer_factory: AuditWriterFactory | None = None,
) -> None:
    """Log a HOOK_ERROR audit event for unhandled exceptions in handlers.

    Args:
        handler: Name of the handler that raised the exception.
        error: The unhandled exception.
        stderr_capture: Captured stderr content (already truncated by caller).
        audit_writer_factory: Callable returning an AuditLogWriter.
    """
    try:
        factory = audit_writer_factory or _audit_writer_factory
        audit_writer = factory()
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
