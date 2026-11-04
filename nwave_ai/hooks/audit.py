"""Hook audit trail: the audit writer port and its adapters, the nWave observability log writers,
the audit event vocabulary and the audit log path resolution.

Moved verbatim from the removed DES runtime (S5-OQ6 closure of the hook handlers). It records
decisions; it makes none. The log directory follows AuditLogPathResolver's documented priority.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any

from nwave_ai.hooks.run_context import resolve_run_context
from nwave_ai.platform.gitignore import ensure_nwave_gitignore
from nwave_ai.platform.locations import resolve_nwave_root
from nwave_ai.platform.project_root import (
    anchor_to_project_root,
    is_refused_project_root,
)


@dataclass(frozen=True)
class AuditEvent:
    """A single audit event for the compliance trail.

    Attributes:
        event_type: Event classification (e.g., HOOK_PRE_TOOL_USE_ALLOWED)
        timestamp: ISO 8601 timestamp string
        feature_name: Feature identifier for traceability (optional)
        step_id: Step identifier for traceability (optional)
        hook_id: Correlation ID linking this event to its hook invocation (optional).
            When None, the field is omitted from serialized output (backward compatible).
        data: Additional event-specific data
    """

    event_type: str
    timestamp: str
    feature_name: str | None = None
    step_id: str | None = None
    hook_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


class AuditLogWriter(ABC):
    """Driven port: writes audit events to the compliance trail.

    Events must be append-only (no modification of existing entries).
    Each event must include an ISO 8601 timestamp.

    Event types logged:
        HOOK_PRE_TOOL_USE_ALLOWED  - Task invocation permitted
        HOOK_PRE_TOOL_USE_BLOCKED  - Task invocation rejected (with reason)
        SCOPE_VIOLATION            - Out-of-scope file modification detected
    """

    @abstractmethod
    def log_event(self, event: AuditEvent) -> None:
        """Append a single audit event to the log.

        Must be append-only: no modification of existing entries.

        Args:
            event: The audit event to log
        """
        ...


class EventType(Enum):
    """Audit event type categories."""

    # PHASE events
    PHASE_STARTED = "PHASE_STARTED"

    # SUBAGENT_STOP events
    SUBAGENT_STOP_VALIDATION = "SUBAGENT_STOP_VALIDATION"

    # HOOK events
    HOOK_PRE_TASK_PASSED = "HOOK_PRE_TASK_PASSED"
    HOOK_PRE_TASK_BLOCKED = "HOOK_PRE_TASK_BLOCKED"
    HOOK_SUBAGENT_STOP_PASSED = "HOOK_SUBAGENT_STOP_PASSED"
    HOOK_SUBAGENT_STOP_FAILED = "HOOK_SUBAGENT_STOP_FAILED"

    # AGENT_USAGE events (L1 token instrumentation)
    AGENT_USAGE_OBSERVED = "AGENT_USAGE_OBSERVED"

    # HEALTH_GATE events (DV-5 — install-freshness dual-emit, KPI-1 sink)
    HEALTH_GATE_INSTALL_FRESHNESS_STALE = "HEALTH_GATE_INSTALL_FRESHNESS_STALE"
    # SYS-4 / AD-27 — shipped config-asset drift (lib/nWave/) dual-emit
    HEALTH_GATE_INSTALL_FRESHNESS_CONFIG_DRIFT = (
        "HEALTH_GATE_INSTALL_FRESHNESS_CONFIG_DRIFT"
    )


@dataclass
class StepAuditEvent:
    """Structured step audit event with complete execution context.

    Retained under a distinct name because the bypass detector's optional event carries step
    fields, while AuditEvent above is the hook port event. Both keep their serialised shape.
    """

    timestamp: str  # ISO 8601 format: YYYY-MM-DDTHH:MM:SS.sssZ
    event: str  # Event type from EventType enum
    feature_name: str | None = None  # Feature name from step file
    step_id: str | None = None  # Step identifier (e.g., "01-02")
    phase_name: str | None = None  # Name of the TDD phase
    status: str | None = None  # Phase status: IN_PROGRESS, EXECUTED, SKIPPED
    reason: str | None = None  # Reason for failure/rejection
    commit_hash: str | None = None  # Git commit hash (for COMMIT events)
    rejection_reason: str | None = None  # Detailed rejection reason
    extra_context: dict[str, Any] | None = None  # Additional contextual data

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization; excludes None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> StepAuditEvent:
        """Create StepAuditEvent from dictionary."""
        return StepAuditEvent(**data)


class AuditLogPathResolver:
    """Resolves audit log directory path deterministically."""

    def __init__(
        self,
        log_dir: str | Path | None = None,
        cwd: str | Path | None = None,
    ) -> None:
        """Initialize resolver.

        Args:
            log_dir: Explicit log directory (highest priority)
            cwd: Working directory override (for hook context where
                 Path.cwd() may be non-deterministic)
        """
        self._explicit_dir = Path(log_dir) if log_dir else None
        self._cwd = Path(cwd) if cwd else None

    def resolve(self) -> Path:
        """Resolve audit log directory path.

        Returns:
            Path to audit log directory
        """
        # Priority 1: Explicit parameter
        if self._explicit_dir:
            return self._explicit_dir

        # Priority 2: Environment variable
        env_dir = os.environ.get("DES_AUDIT_LOG_DIR")
        if env_dir:
            return Path(env_dir)

        # Priority 3: Config file
        effective_cwd = self._cwd or resolve_nwave_root()
        config_dir = self._resolve_config_dir(effective_cwd)
        if config_dir:
            return config_dir

        # Priority 4: Project-local, anchored at the project root so a session
        # that moves into a subfolder keeps writing one log
        project_root = anchor_to_project_root(effective_cwd)
        if not is_refused_project_root(project_root):
            return project_root / ".nwave" / "des" / "logs"

        # Priority 5: Global fallback
        home = Path.home()
        return home / ".claude" / "des" / "logs"

    @staticmethod
    def _resolve_config_dir(cwd: Path) -> Path | None:
        """Read audit_log_dir from the canonical .nwave/config.json."""
        config_file = cwd / ".nwave" / "config.json"
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text(encoding="utf-8"))
                audit_dir = config.get("audit_log_dir")
                if audit_dir:
                    return Path(audit_dir)
            except (json.JSONDecodeError, OSError):
                # WHAT: config.json exists but is malformed JSON, or
                # became unreadable between the exists() check and read.
                # WHY: this is priority-4-of-5 in the resolver's fallback
                # chain (see method docstring) -- a bad config file must
                # degrade to the next priority, not raise.
                # HOW: safe to continue -- caller falls through to
                # priority 4/5 fallback below.
                pass
        return None


class JsonlAuditLogWriter(AuditLogWriter):
    """Writes audit events to JSONL files.

    Each event is serialized as one JSON line, appended to a daily log file.
    File format: audit-YYYY-MM-DD.log in the configured log directory.
    """

    def __init__(
        self, log_dir: str | Path | None = None, cwd: str | Path | None = None
    ) -> None:
        """Initialize with a log directory.

        Log directory priority (highest to lowest):
        1. Explicit log_dir parameter
        2. DES_AUDIT_LOG_DIR environment variable
        3. Project-local .nwave/des/logs/ under the project root (default)
        4. Global ~/.claude/des/logs/ (fallback)

        Args:
            log_dir: Directory for audit log files (default: follows priority above)
            cwd: Working directory override for deterministic resolution
        """
        resolved = AuditLogPathResolver(log_dir=log_dir, cwd=cwd).resolve()

        self._log_dir = resolved
        self._log_dir.mkdir(parents=True, exist_ok=True)
        ensure_nwave_gitignore(resolved)

    def log_event(self, event: AuditEvent) -> None:
        """Append a single audit event to the log.

        Serializes the AuditEvent to a JSON line and appends to today's log file.
        Must be append-only: no modification of existing entries.

        Args:
            event: The audit event to log
        """
        # Ensure log directory exists (handles temp dir cleanup)
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Build the JSON entry from the port-defined AuditEvent
        entry = {
            "event": event.event_type,
            "timestamp": event.timestamp,
        }

        # Add optional traceability fields (exclude None values)
        if event.feature_name is not None:
            entry["feature_name"] = event.feature_name
        if event.step_id is not None:
            entry["step_id"] = event.step_id
        if event.hook_id is not None:
            entry["hook_id"] = event.hook_id

        # Merge additional event-specific data
        entry.update(event.data)

        # Stamp the DECLARED run context last, so an event payload cannot
        # relabel where the event was born. Always present -- an undeclared
        # context serializes as the explicit `unknown` state rather than an
        # absent field, otherwise a reader cannot tell "no context declared"
        # from "written before this field existed", and every count that
        # separates real firings from test-manufactured ones stays wrong.
        entry["run_context"] = resolve_run_context(os.environ)

        # Serialize to compact JSONL
        json_line = json.dumps(entry, separators=(",", ":"), sort_keys=True)

        # Append to today's log file
        log_file = self._get_log_file()
        with open(log_file, "a") as f:
            f.write(json_line + "\n")

    def _get_log_file(self) -> Path:
        """Get today's log file path with date-based naming.

        Format: audit-YYYY-MM-DD.log
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._log_dir / f"audit-{today}.log"


class NullAuditLogWriter(AuditLogWriter):
    """No-op implementation of AuditLogWriter for disabled audit logging."""

    def log_event(self, event: AuditEvent) -> None:
        """Accept event without writing. No-op."""


class LogLevel(IntEnum):
    """Log severity levels for nWave observability.

    Levels follow the standard 10-increment convention for extensibility.
    Supports comparison operators for level-based filtering.
    """

    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40


@dataclass(frozen=True)
class NWaveLogEntry:
    """A single structured log entry for nWave observability.

    Frozen (immutable) to ensure log entries cannot be modified after creation.

    Attributes:
        timestamp: ISO 8601 timestamp string.
        level: Severity level of the log entry.
        stage: System stage producing the entry
            ("install"|"hook"|"build"|"plugin"|"runtime").
        operation: Specific operation being performed.
        event: Event type ("entry"|"outcome"|"error"|"debug").
        message: Human-readable log message.
        operation_id: UUID correlating related log entries.
        error_code: Machine-readable error code (None if no error).
        duration_ms: Operation duration in milliseconds (None if not timed).
        context: Additional structured data for the entry.
    """

    timestamp: str
    level: LogLevel
    stage: str
    operation: str
    event: str
    message: str
    operation_id: str
    error_code: str | None = None
    duration_ms: float | None = None
    context: dict[str, Any] = field(default_factory=dict)


class NWaveLogWriter(ABC):
    """Driven port: writes structured log entries to the observability system.

    Adapters implement this port to direct log output to different
    destinations (null/no-op, stderr, file, etc.).
    """

    @abstractmethod
    def log(self, entry: NWaveLogEntry) -> None:
        """Write a single log entry.

        Args:
            entry: The structured log entry to write.
        """
        ...

    @abstractmethod
    def set_level(self, level: LogLevel) -> None:
        """Set the minimum log level for filtering.

        Entries below this level should be discarded by the adapter.

        Args:
            level: The minimum severity level to log.
        """
        ...


class JsonlNWaveLogWriter(NWaveLogWriter):
    """Writes structured log entries to daily JSONL files.

    Each entry is serialized as one compact JSON line, appended to a
    daily log file. File format: nwave-YYYY-MM-DD.jsonl in the
    configured log directory.

    Never raises exceptions -- all I/O errors are silently swallowed
    to ensure logging cannot break operations.
    """

    def __init__(
        self,
        log_dir: str | Path | None = None,
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        """Initialize with a log directory and minimum level.

        Args:
            log_dir: Directory for log files. Defaults to ~/.nwave/logs/.
            level: Minimum severity level to log. Defaults to INFO.
        """
        if log_dir is None:
            self._log_dir = Path.home() / ".nwave" / "logs"
        else:
            self._log_dir = Path(log_dir)
        self._level = level

    def log(self, entry: NWaveLogEntry) -> None:
        """Write a single log entry to the daily JSONL file.

        Entries below the configured minimum level are silently discarded.
        Any I/O errors are swallowed to ensure logging never breaks operations.

        Args:
            entry: The structured log entry to write.
        """
        try:
            if entry.level < self._level:
                return

            self._log_dir.mkdir(parents=True, exist_ok=True)

            record: dict = {
                "timestamp": entry.timestamp,
                "level": entry.level.name,
                "stage": entry.stage,
                "operation": entry.operation,
                "event": entry.event,
                "message": entry.message,
                "operation_id": entry.operation_id,
            }

            if entry.error_code is not None:
                record["error_code"] = entry.error_code
            if entry.duration_ms is not None:
                record["duration_ms"] = entry.duration_ms
            if entry.context:
                record["context"] = entry.context

            json_line = json.dumps(record, separators=(",", ":"))

            date_part = entry.timestamp[:10]
            log_file = self._log_dir / f"nwave-{date_part}.jsonl"

            with open(log_file, "a") as f:
                f.write(json_line + "\n")

        except Exception:
            # WHAT: log-directory creation or file append failed (e.g.
            # permission error, disk full, unreadable path).
            # WHY: this IS the logging adapter itself -- "Exception
            # swallowing (logging must never break operations)" is a
            # documented class invariant (see class docstring); there is
            # no lower-level sink left to report the failure to.
            # HOW: safe to continue -- caller's operation proceeds
            # unaffected, only observability is lost for this entry.
            pass

    def set_level(self, level: LogLevel) -> None:
        """Set the minimum log level for filtering.

        Args:
            level: The minimum severity level to log.
        """
        self._level = level


class NullNWaveLogWriter(NWaveLogWriter):
    """No-op implementation of NWaveLogWriter for disabled logging."""

    def log(self, entry: NWaveLogEntry) -> None:
        """Accept entry without writing. No-op."""

    def set_level(self, level: LogLevel) -> None:
        """Accept level without storing. No-op."""


__all__ = [
    "AuditEvent",
    "AuditLogPathResolver",
    "AuditLogWriter",
    "EventType",
    "JsonlAuditLogWriter",
    "JsonlNWaveLogWriter",
    "LogLevel",
    "NWaveLogEntry",
    "NWaveLogWriter",
    "NullAuditLogWriter",
    "NullNWaveLogWriter",
    "StepAuditEvent",
]
