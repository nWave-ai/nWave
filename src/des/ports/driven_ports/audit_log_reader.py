"""AuditLogReader - driven port for reading audit events.

Separate from AuditLogWriter to respect Interface Segregation:
- Writer: append-only contract
- Reader: query contract

Defined by: PostToolUseService requirements.
Implemented by: JsonlAuditLogReader (infrastructure adapter).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AuditLogReader(ABC):
    """Driven port: reads audit events from the compliance trail.

    Provides read access to the audit log for querying recent events.
    Implementations must handle missing/empty logs gracefully (return None).
    """

    @abstractmethod
    def read_last_entry(
        self,
        event_type: str | None = None,
        feature_name: str | None = None,
        step_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Read the most recent audit entry matching the given filters.

        Args:
            event_type: Filter by event type (e.g., "HOOK_SUBAGENT_STOP_FAILED")
            feature_name: Filter by feature name
            step_id: Filter by step ID

        Returns:
            Most recent matching audit entry as dict, or None if not found
        """
        ...
