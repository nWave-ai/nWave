# Audit Trail and Compliance Verification Reference

## Overview

The DES audit trail module provides append-only, immutable logging for compliance verification. It captures all execution state transitions with cryptographic integrity guarantees, enabling auditors to prove feature execution occurred correctly.

## Breaking Changes

**Schema v2.0 Migration (2026-02)**

The `step_path` field has been replaced with two direct fields:

| Old Schema | New Schema |
|---|---|
| `step_path: "steps/01-01.json"` | `feature_name: "audit-log-refactor"` + `step_id: "01-01"` |

**Rationale**: `feature_name` is sourced from the `DES-PROJECT-ID` marker in the step file header and from `SubagentStopContext.project_id`. This aligns audit events with the project-centric hexagonal architecture, where feature identity is a first-class concept rather than a file system path.

**Migration**: All consumers of the audit log must update queries from `.step_path` to `.feature_name` and `.step_id`. The `step_path` field is no longer emitted.

## Core Components

### AuditLogger

The `AuditLogger` class manages append-only audit logs with the following characteristics:

- **Append-Only**: Entries cannot be modified or deleted, only appended
- **Immutable**: SHA256 hashing ensures log tampering is detectable
- **Timestamped**: ISO 8601 timestamps with millisecond precision
- **Rotated**: Daily rotation with date-based naming prevents unbounded file growth
- **Human-Readable**: JSONL format (one JSON entry per line)

#### Location
`src/des/adapters/driven/logging/audit_logger.py`

#### Key Methods

```python
# Initialize logger (creates .nwave/des/logs directory)
logger = AuditLogger(log_dir=".nwave/des/logs")

# Append entry (creates file on first append)
logger.append({
    "timestamp": "2026-01-27T14:30:45.123Z",
    "event": "PHASE_STARTED",
    "feature_name": "audit-log-refactor",
    "step_id": "01-01",
    "phase": "RED_ACCEPTANCE"
})

# Compute hash of range (for integrity verification)
hash_result = logger.compute_hash_of_entries(start_idx=0, end_idx=10)

# Retrieve entries for specific step
entries = logger.read_entries_for_step(step_id="01-01")

# Get all entries
all_entries = logger.get_entries()

# Rotate log file if date changed
logger.rotate_if_needed()
```

### AuditEvent (Port Layer)

The `PortAuditEvent` dataclass in the port layer provides structured event definitions with comprehensive context. The `feature_name` and `step_id` are direct fields on the event, not nested inside extra context.

#### Location
`src/des/ports/driven_ports/audit_log_writer.py`

#### Event Types

Organized into 4 categories:

**Task Invocation Events**
- `TASK_INVOCATION_STARTED` - Task invocation initiated
- `TASK_INVOCATION_VALIDATED` - Task invocation validated
- `TASK_INVOCATION_REJECTED` - Task invocation rejected

**Phase Lifecycle Events**
- `PHASE_STARTED` - TDD phase execution started
- `PHASE_EXECUTED` - Phase completed successfully
- `PHASE_SKIPPED` - Phase skipped (pre-requisite not met)
- `PHASE_FAILED` - Phase execution failed

**Subagent Control Events**
- `SUBAGENT_STOP_VALIDATION` - Subagent stopped by validation
- `SUBAGENT_STOP_FAILURE` - Subagent stopped due to failure

**Commit Events**
- `COMMIT_SUCCESS` - Commit successful
- `COMMIT_FAILURE` - Commit failed

**Validation Events**
- `VALIDATION_REJECTED` - Validation rejection recorded

#### Event Structure

```python
@dataclass
class PortAuditEvent:
    timestamp: str  # ISO 8601: YYYY-MM-DDTHH:MM:SS.sssZ
    event: str  # Event type
    feature_name: Optional[str]  # Project/feature identifier (from DES-PROJECT-ID)
    step_id: Optional[str]  # Step identifier (e.g., "01-01")
    phase_name: Optional[str]  # Name of TDD phase
    status: Optional[str]  # Current status
    outcome: Optional[str]  # Success or failure
    duration_minutes: Optional[float]  # Duration
    reason: Optional[str]  # Reason for failure
    commit_hash: Optional[str]  # Git commit hash
    rejection_reason: Optional[str]  # Detailed rejection
    extra_context: Optional[Dict[str, Any]]  # Additional data
```

## Usage

### Logging Events

```python
from src.des.adapters.driven.logging.audit_logger import log_audit_event

# Log a task invocation
log_audit_event(
    "TASK_INVOCATION_STARTED",
    command="nw:execute",
    feature_name="audit-log-refactor",
    step_id="01-01"
)

# Log phase transition
log_audit_event(
    "PHASE_STARTED",
    feature_name="audit-log-refactor",
    step_id="01-01",
    phase_name="RED_ACCEPTANCE",
    status="IN_PROGRESS"
)

# Log successful completion
log_audit_event(
    "PHASE_EXECUTED",
    feature_name="audit-log-refactor",
    step_id="01-01",
    phase_name="RED_ACCEPTANCE",
    outcome="success",
    duration_minutes=15.5
)
```

### Verifying Integrity

```python
# Get entries for a step
entries = logger.read_entries_for_step(step_id="01-01")

# Verify no tampering occurred
original_hash = logger.compute_hash_of_entries(0, 5)
# ... later ...
verify_hash = logger.compute_hash_of_entries(0, 5)
assert original_hash == verify_hash  # Hash unchanged = no tampering
```

### Log File Format

Entries are stored in JSONL format (JSON Lines):

```jsonl
{"timestamp":"2026-01-27T14:30:45.123Z","event":"PHASE_STARTED","feature_name":"audit-log-refactor","step_id":"01-01","phase":"RED_ACCEPTANCE"}
{"timestamp":"2026-01-27T14:31:12.456Z","event":"PHASE_EXECUTED","feature_name":"audit-log-refactor","step_id":"01-01","phase":"RED_ACCEPTANCE","outcome":"success"}
{"timestamp":"2026-01-27T14:31:45.789Z","event":"PHASE_STARTED","feature_name":"audit-log-refactor","step_id":"01-01","phase":"RED_UNIT"}
```

## Log File Rotation

Log files are automatically rotated daily with naming scheme: `audit-YYYY-MM-DD.log`

Example:
- `audit-2026-01-27.log` - All entries from January 27
- `audit-2026-01-28.log` - All entries from January 28

## Integration Points

### DES Orchestrator

The audit logger is integrated into the DES orchestrator (`src/des/application/orchestrator.py`):

```python
# Logs task invocation lifecycle
def render_prompt(self, command, step_file=None, agent=None, project_id=None):
    # Log start of task invocation (feature_name sourced from project_id parameter)
    log_audit_event(
        "TASK_INVOCATION_STARTED",
        command=command,
        feature_name=project_id,
        step_id=step_id
    )

    # ... validation logic ...

    # Log successful validation
    log_audit_event(
        "TASK_INVOCATION_VALIDATED",
        command=command,
        feature_name=project_id,
        step_id=step_id,
        status="VALIDATED"
    )
```

### SubagentStopService

The subagent stop service (`src/des/application/subagent_stop_service.py`) sources `feature_name` from `SubagentStopContext.project_id`:

```python
# SubagentStopContext provides project_id which maps to feature_name
context = SubagentStopContext(project_id="audit-log-refactor", step_id="01-01", ...)

# Audit event uses feature_name and step_id as direct fields
log_audit_event(
    "SUBAGENT_STOP_VALIDATION",
    feature_name=context.project_id,
    step_id=context.step_id,
    outcome="PASS"
)
```

## Querying Audit Logs

### By Feature Name

```bash
# Find all events for a specific feature
jq -c 'select(.feature_name == "audit-log-refactor")' .nwave/des/logs/audit-2026-01-27.log

# Find all events for a specific step within a feature
jq -c 'select(.feature_name == "audit-log-refactor" and .step_id == "01-01")' .nwave/des/logs/audit-2026-01-27.log
```

### By Event Type

```bash
# Find all phase failures
jq -c 'select(.event == "PHASE_FAILED")' .nwave/des/logs/audit-2026-01-27.log

# Find all events for a step with phase details
jq -c 'select(.step_id == "01-01") | {event, phase: .phase_name, outcome}' .nwave/des/logs/audit-2026-01-27.log
```

## Compliance Features

- **Immutability**: SHA256 hashing prevents undetected tampering
- **Non-Repudiation**: Timestamps prove when events occurred
- **Audit Trail**: Complete execution history for review
- **Data Integrity**: Hash verification confirms no modifications
- **Regulatory Compliance**: Append-only logs meet audit requirements
- **Human Readable**: JSONL format allows manual inspection

## Test Coverage

- **12/12 Acceptance Tests** - All audit trail scenarios validated
- **11/11 Unit Tests** - AuditLogger functionality comprehensive
- **73% Code Coverage** - Core audit functionality validated

## Performance Considerations

- **Append-Only**: O(1) write performance (no log rewriting)
- **Log Rotation**: Daily rotation prevents single file bloat
- **In-Memory Hashing**: Hash computation maintains O(n) for range
- **Lazy Initialization**: Log file created on first append, not initialization

## Security Considerations

- **Hash Verification Only**: SHA256 hashing detects tampering but doesn't prevent modifications by root/administrator
- **File System Security**: Rely on OS/file system permissions to protect audit log files
- **Storage**: Ensure audit logs are stored on separate, protected storage for regulatory compliance

## Location

`src/des/adapters/driven/logging/audit_logger.py`
`src/des/ports/driven_ports/audit_log_writer.py`

## See Also

- [DES Orchestrator API Reference](./des-orchestrator-api.md)
- [Recovery Guidance Handler API Reference](./recovery-guidance-handler-api.md)
- [Audit Log Refactor API Reference](./audit-log-refactor.md)
