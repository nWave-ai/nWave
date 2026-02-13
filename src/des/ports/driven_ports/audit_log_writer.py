"""AuditLogWriter - driven port for writing audit events.

Abstract interface defining how the application layer writes audit events
to the compliance trail.

Defined by: Application layer audit requirements.
Implemented by: JsonlAuditLogWriter (infrastructure adapter).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


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
        HOOK_SUBAGENT_STOP_PASSED  - Step completion validated successfully
        HOOK_SUBAGENT_STOP_FAILED  - Step completion validation failed
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
