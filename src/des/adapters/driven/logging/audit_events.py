"""
Audit event type definitions and AuditEvent dataclass.

Defines standardized event categories:
- TASK_INVOCATION: Task invocation lifecycle events
- PHASE: TDD phase execution events
- SUBAGENT_STOP: Subagent termination events
- COMMIT: Git commit events
"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class EventType(Enum):
    """Audit event type categories."""

    # TASK_INVOCATION events
    TASK_INVOCATION_STARTED = "TASK_INVOCATION_STARTED"
    TASK_INVOCATION_VALIDATED = "TASK_INVOCATION_VALIDATED"
    TASK_INVOCATION_REJECTED = "TASK_INVOCATION_REJECTED"

    # PHASE events
    PHASE_STARTED = "PHASE_STARTED"
    PHASE_EXECUTED = "PHASE_EXECUTED"
    PHASE_SKIPPED = "PHASE_SKIPPED"
    PHASE_FAILED = "PHASE_FAILED"

    # SUBAGENT_STOP events
    SUBAGENT_STOP_VALIDATION = "SUBAGENT_STOP_VALIDATION"
    SUBAGENT_STOP_FAILURE = "SUBAGENT_STOP_FAILURE"

    # COMMIT events
    COMMIT_SUCCESS = "COMMIT_SUCCESS"
    COMMIT_FAILURE = "COMMIT_FAILURE"

    # VALIDATION events
    VALIDATION_REJECTED = "VALIDATION_REJECTED"

    # HOOK events
    HOOK_PRE_TASK_PASSED = "HOOK_PRE_TASK_PASSED"
    HOOK_PRE_TASK_BLOCKED = "HOOK_PRE_TASK_BLOCKED"
    HOOK_SUBAGENT_STOP_PASSED = "HOOK_SUBAGENT_STOP_PASSED"
    HOOK_SUBAGENT_STOP_FAILED = "HOOK_SUBAGENT_STOP_FAILED"


@dataclass
class AuditEvent:
    """Structured audit event with complete execution context."""

    timestamp: str  # ISO 8601 format: YYYY-MM-DDTHH:MM:SS.sssZ
    event: str  # Event type from EventType enum
    feature_name: str | None = None  # Feature name from step file
    step_id: str | None = None  # Step identifier (e.g., "01-02")
    phase_name: str | None = None  # Name of the TDD phase
    status: str | None = None  # Phase status: IN_PROGRESS, EXECUTED, SKIPPED
    outcome: str | None = None  # Success or failure outcome
    duration_minutes: float | None = None  # Duration of phase/event
    reason: str | None = None  # Reason for failure/rejection
    commit_hash: str | None = None  # Git commit hash (for COMMIT events)
    rejection_reason: str | None = None  # Detailed rejection reason
    extra_context: dict[str, Any] | None = None  # Additional contextual data

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Excludes None values for cleaner JSONL output.
        """
        data = asdict(self)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AuditEvent":
        """Create AuditEvent from dictionary.

        Args:
            data: Dictionary with event data

        Returns:
            AuditEvent instance
        """
        return AuditEvent(**data)


def validate_event_type(event_type: str) -> bool:
    """Validate that event type is in allowed categories.

    Args:
        event_type: Event type string to validate

    Returns:
        True if valid, False otherwise
    """
    return any(e.value == event_type for e in EventType)


def get_event_category(event_type: str) -> str:
    """Get event category from event type.

    Args:
        event_type: Event type string (e.g., 'TASK_INVOCATION_STARTED')

    Returns:
        Event category (e.g., 'TASK_INVOCATION')
    """
    if event_type.startswith("TASK_INVOCATION"):
        return "TASK_INVOCATION"
    elif event_type.startswith("PHASE"):
        return "PHASE"
    elif event_type.startswith("SUBAGENT_STOP"):
        return "SUBAGENT_STOP"
    elif event_type.startswith("COMMIT"):
        return "COMMIT"
    elif event_type.startswith("VALIDATION"):
        return "VALIDATION"
    elif event_type.startswith("HOOK"):
        return "HOOK"
    else:
        return "UNKNOWN"
