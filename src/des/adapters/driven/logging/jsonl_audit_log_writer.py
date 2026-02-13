"""JsonlAuditLogWriter - driven adapter for writing audit events.

Implements the AuditLogWriter port by appending events to JSONL files.
Replaces the AuditLogger singleton with a proper dependency-injected adapter.

Features retained from legacy AuditLogger:
- Append-only file operations (no modifications to existing entries)
- JSONL format output (one JSON object per line)
- Daily log rotation with date-based naming
- Configurable log directory

Features removed (no longer needed):
- Singleton pattern (replaced by dependency injection)
- SHA256 hash tracking (not required by port contract)
- File permission hardening (orthogonal concern, can be added back)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from des.domain.audit_log_path_resolver import AuditLogPathResolver
from des.ports.driven_ports.audit_log_writer import AuditEvent, AuditLogWriter


if TYPE_CHECKING:
    from pathlib import Path


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
        3. Project-local .nwave/des/logs/ (default)
        4. Global ~/.claude/des/logs/ (fallback)

        Args:
            log_dir: Directory for audit log files (default: follows priority above)
            cwd: Working directory override for deterministic resolution
        """
        resolved = AuditLogPathResolver(log_dir=log_dir, cwd=cwd).resolve()

        self._log_dir = resolved
        self._log_dir.mkdir(parents=True, exist_ok=True)

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
