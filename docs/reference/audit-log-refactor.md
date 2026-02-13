# Audit Log Refactor: API Reference

Complete API specification for the audit log system after the v1.x → v2.0 schema migration.

**Status**: Complete (v2.0)
**Last Updated**: 2026-02-13
**Migration**: step_path (v1.x) → feature_name + step_id (v2.0)

## Primary Locations

- `src/des/ports/driven_ports/audit_log_writer.py` — Port definition and `PortAuditEvent` dataclass
- `src/des/adapters/driven/logging/jsonl_audit_log_writer.py` — JSONL adapter implementation
- `src/des/application/orchestrator.py` — DES Orchestrator audit logging
- `src/des/application/subagent_stop_service.py` — SubagentStopService audit logging

---

## PortAuditEvent Dataclass

Located: `src/des/ports/driven_ports/audit_log_writer.py`

### Definition

```python
@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    timestamp: str
    feature_name: str | None = None
    step_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
```

### Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `event_type` | `str` | Yes | Event classification | `"HOOK_SUBAGENT_STOP_PASSED"` |
| `timestamp` | `str` | Yes | ISO 8601 UTC timestamp | `"2026-02-05T14:30:00Z"` |
| `feature_name` | `str \| None` | No | Feature/project identifier (optional) | `"audit-log-refactor"` |
| `step_id` | `str \| None` | No | Step identifier within feature (optional) | `"03-02"` |
| `data` | `dict[str, Any]` | No | Additional event-specific data | `{"tests_passed": 12}` |

### Immutability

The dataclass is frozen (`frozen=True`). Instances cannot be modified after creation.

---

## Event Types

Enumeration of all event types logged to the audit trail.

### Hook Validation Events

| Event Type | Fired By | Description | When |
|------------|----------|-------------|------|
| `HOOK_PRE_TOOL_USE_ALLOWED` | PreToolUseHook | Task invocation permitted | After pre-tool validation passes |
| `HOOK_PRE_TOOL_USE_BLOCKED` | PreToolUseHook | Task invocation rejected | Pre-tool validation failed |
| `HOOK_SUBAGENT_STOP_PASSED` | SubagentStopService | Step completion validated | Execution completed successfully |
| `HOOK_SUBAGENT_STOP_FAILED` | SubagentStopService | Step completion invalid | Completion validation failed |

### Scope Events

| Event Type | Fired By | Description | When |
|------------|----------|-------------|------|
| `SCOPE_VIOLATION` | SubagentStopService | Out-of-scope file modified | File modification outside scope |

### Task Invocation Events

| Event Type | Fired By | Description | When |
|------------|----------|-------------|------|
| `TASK_INVOCATION_STARTED` | DESOrchestrator | Agent execution begins | `render_prompt()` called |
| `TASK_INVOCATION_VALIDATED` | DESOrchestrator | Pre-invocation hooks passed | Template validation passed |

---

## JsonlAuditLogWriter Adapter

Located: `src/des/adapters/driven/logging/jsonl_audit_log_writer.py`

### Constructor

```python
def __init__(self, log_dir: str | Path | None = None) -> None:
    """Initialize with a log directory.

    Args:
        log_dir: Directory for audit log files (default: follows priority below)
    """
```

### Log Directory Resolution Priority

1. Explicit `log_dir` parameter (highest priority)
2. `DES_AUDIT_LOG_DIR` environment variable
3. `.nwave/des-config.json` `audit_log_dir` field (from config)
4. `.nwave/des/logs/` (project-local default)
5. `~/.claude/des/logs/` (global fallback)

### Method: log_event()

```python
def log_event(self, event: AuditEvent) -> None:
    """Append a single audit event to the log.

    Args:
        event: The AuditEvent to log

    Raises:
        OSError: If log directory cannot be created or written
    """
```

### JSON Serialization

**Entry Structure**:

```json
{
  "event": "HOOK_SUBAGENT_STOP_PASSED",
  "timestamp": "2026-02-05T14:30:00Z",
  "feature_name": "audit-log-refactor",
  "step_id": "03-02",
  "validation_errors": []
}
```

**Rules**:
- `event` and `timestamp` are always present
- `feature_name` and `step_id` are included only if non-None
- `data` dict is merged into the top-level JSON object
- Keys are sorted alphabetically
- Compact JSON format (no pretty-printing, minimal whitespace)

### Log File Naming

- **Pattern**: `audit-YYYY-MM-DD.log`
- **Format**: JSONL (one JSON object per line)
- **Rotation**: Daily (new file created at UTC midnight)
- **Example**: `audit-2026-02-05.log`, `audit-2026-02-06.log`

---

## AuditLogWriter Port

Located: `src/des/ports/driven_ports/audit_log_writer.py`

### Abstract Interface

```python
class AuditLogWriter(ABC):
    @abstractmethod
    def log_event(self, event: AuditEvent) -> None:
        """Append a single audit event to the log."""
        ...
```

### Contract

- **Append-only**: No modification or deletion of existing entries
- **Timestamp requirement**: Each event must include ISO 8601 timestamp
- **Async safety**: No explicit thread-safety guarantee (implementation-specific)

### Implementations

| Implementation | Location | Description |
|----------------|----------|-------------|
| `JsonlAuditLogWriter` | `src/des/adapters/driven/logging/jsonl_audit_log_writer.py` | Writes to JSONL files with daily rotation |

---

## SubagentStopService Audit Logging

Located: `src/des/application/subagent_stop_service.py`

### HOOK_SUBAGENT_STOP_PASSED

**Event Data**:
```python
AuditEvent(
    event_type="HOOK_SUBAGENT_STOP_PASSED",
    timestamp="<ISO 8601>",
    feature_name="<project_id>",
    step_id="<step_id>",
    data={}  # Empty for passed validation
)
```

**JSON Output**:
```json
{
  "event": "HOOK_SUBAGENT_STOP_PASSED",
  "timestamp": "2026-02-05T14:30:00Z",
  "feature_name": "audit-log-refactor",
  "step_id": "03-02"
}
```

### HOOK_SUBAGENT_STOP_FAILED

**Event Data**:
```python
AuditEvent(
    event_type="HOOK_SUBAGENT_STOP_FAILED",
    timestamp="<ISO 8601>",
    feature_name="<project_id>",
    step_id="<step_id>",
    data={
        "validation_errors": ["error1", "error2"],
        "allowed_despite_failure": True  # Optional, only if allowed on second attempt
    }
)
```

**JSON Output**:
```json
{
  "allowed_despite_failure": true,
  "event": "HOOK_SUBAGENT_STOP_FAILED",
  "feature_name": "audit-log-refactor",
  "step_id": "03-02",
  "timestamp": "2026-02-05T14:30:00Z",
  "validation_errors": ["Missing required file", "Invalid YAML syntax"]
}
```

### SCOPE_VIOLATION

**Event Data**:
```python
AuditEvent(
    event_type="SCOPE_VIOLATION",
    timestamp="<ISO 8601>",
    feature_name="<project_id>",
    step_id="<step_id>",
    data={
        "out_of_scope_file": "/path/to/file"
    }
)
```

**JSON Output**:
```json
{
  "event": "SCOPE_VIOLATION",
  "feature_name": "audit-log-refactor",
  "out_of_scope_file": "/mnt/c/forbidden/file.txt",
  "step_id": "03-02",
  "timestamp": "2026-02-05T14:30:00Z"
}
```

---

## DESOrchestrator Audit Logging

Located: `src/des/application/orchestrator.py`

### TASK_INVOCATION_STARTED

**Logged by**: `render_prompt()` method
**Parameters**: `command`, `step_id`, `feature_name`, `agent`

**Event Data**:
```python
_log_audit_event(
    "TASK_INVOCATION_STARTED",
    command="/nw:execute",
    step_id="03-02",
    feature_name="audit-log-refactor",
    agent="software-crafter"
)
```

**JSON Output**:
```json
{
  "agent": "software-crafter",
  "command": "/nw:execute",
  "event": "TASK_INVOCATION_STARTED",
  "feature_name": "audit-log-refactor",
  "step_id": "03-02",
  "timestamp": "2026-02-05T14:30:00Z"
}
```

### TASK_INVOCATION_VALIDATED

**Logged by**: `render_prompt()` method (after validation passes)
**Parameters**: `command`, `step_id`, `feature_name`, `status`, `outcome`

**Event Data**:
```python
_log_audit_event(
    "TASK_INVOCATION_VALIDATED",
    command="/nw:execute",
    step_id="03-02",
    feature_name="audit-log-refactor",
    status="VALIDATED",
    outcome="success"
)
```

**JSON Output**:
```json
{
  "command": "/nw:execute",
  "event": "TASK_INVOCATION_VALIDATED",
  "feature_name": "audit-log-refactor",
  "outcome": "success",
  "status": "VALIDATED",
  "step_id": "03-02",
  "timestamp": "2026-02-05T14:30:00Z"
}
```

---

## Schema Migration: v1.x → v2.0

### Before (v1.x)

**Field**: `step_path` (file system path string)

**JSON Example**:
```json
{
  "event": "HOOK_SUBAGENT_STOP_PASSED",
  "timestamp": "2026-02-05T14:30:00Z",
  "step_path": "docs/feature/audit-log-refactor/steps/03-02.yaml",
  "phase_name": "GREEN",
  "data": {}
}
```

### After (v2.0)

**Fields**: `feature_name` + `step_id` (semantic identifiers)

**JSON Example**:
```json
{
  "event": "HOOK_SUBAGENT_STOP_PASSED",
  "timestamp": "2026-02-05T14:30:00Z",
  "feature_name": "audit-log-refactor",
  "step_id": "03-02",
  "phase_name": "GREEN"
}
```

### Migration Mapping

| v1.x Field | v2.0 Replacement | Extraction Rule |
|-----------|------------------|-----------------|
| `step_path` | `feature_name` | Extract from path: `docs/feature/{feature_name}/steps/...` |
| `step_path` | `step_id` | Extract from path: `...steps/{step_id}.yaml` |

### Query Migration

| Task | v1.x Query | v2.0 Query |
|------|-----------|-----------|
| Filter by feature | `jq 'select(.step_path \| contains("audit-log-refactor"))'` | `jq 'select(.feature_name=="audit-log-refactor")'` |
| Filter by step | `jq 'select(.step_path \| contains("03-02"))'` | `jq 'select(.step_id=="03-02")'` |
| Count by feature | `grep '"step_path"' \| jq -r '.step_path' \| cut -d/ -f3 \| sort \| uniq -c` | `jq -r '.feature_name' \| sort \| uniq -c` |
| Feature + step | `jq 'select(.step_path \| contains("audit-log/") and .step_path \| contains("03-02"))'` | `jq 'select(.feature_name=="audit-log-refactor" and .step_id=="03-02")'` |

---

## jq Query Reference

### Basic Filtering

```bash
# All events for a specific feature
jq 'select(.feature_name=="audit-log-refactor")' audit-*.log

# All events for a specific step
jq 'select(.feature_name=="audit-log-refactor" and .step_id=="03-02")' audit-*.log

# All events of a specific type
jq 'select(.event=="HOOK_SUBAGENT_STOP_PASSED")' audit-*.log

# Events with validation failures
jq 'select(.event=="HOOK_SUBAGENT_STOP_FAILED")' audit-*.log
```

### Aggregation

```bash
# Count events by feature
jq -r '.feature_name' audit-*.log | sort | uniq -c

# Count failures by feature
jq 'select(.event=="HOOK_SUBAGENT_STOP_FAILED") | .feature_name' audit-*.log | sort | uniq -c

# Count violations by step within a feature
jq -r 'select(.event=="SCOPE_VIOLATION" and .feature_name=="audit-log-refactor") | .step_id' audit-*.log | sort | uniq -c

# Group failures by error message
jq -r 'select(.event=="HOOK_SUBAGENT_STOP_FAILED") | .validation_errors[]' audit-*.log | sort | uniq -c
```

### Timeline Analysis

```bash
# View phase execution timeline
jq -r 'select(.event | startswith("PHASE_")) | "\(.timestamp) \(.feature_name) \(.step_id) \(.phase_name) \(.event)"' audit-*.log

# Task invocation timeline
jq -r 'select(.event | startswith("TASK_INVOCATION")) | "\(.timestamp) \(.feature_name) \(.command) \(.outcome)"' audit-*.log

# All events for a feature in chronological order
jq -r 'select(.feature_name=="audit-log-refactor") | "\(.timestamp) \(.event)"' audit-*.log | sort
```

### Scope Violations

```bash
# All scope violations
jq 'select(.event=="SCOPE_VIOLATION")' audit-*.log

# Scope violations by feature
jq -r 'select(.event=="SCOPE_VIOLATION") | .feature_name' audit-*.log | sort | uniq -c

# Files modified outside scope
jq -r 'select(.event=="SCOPE_VIOLATION") | "\(.feature_name) \(.step_id) \(.out_of_scope_file)"' audit-*.log
```

---

## Log Directory Configuration

### Environment Variable

```bash
export DES_AUDIT_LOG_DIR="/custom/audit/path"
```

### Config File

**Location**: `.nwave/des-config.json`

**Schema**:
```json
{
  "audit_log_dir": "/path/to/audit/logs"
}
```

### Priority Resolution

1. `DES_AUDIT_LOG_DIR` environment variable (if set and writable)
2. `audit_log_dir` from `.nwave/des-config.json` (if file exists and valid)
3. `.nwave/des/logs/` (project-local default)
4. `~/.claude/des/logs/` (global fallback, always writable)

---

## Backward Compatibility

### Optional Fields

The v2.0 schema maintains backward compatibility:
- `feature_name` and `step_id` are optional (`str | None`)
- Events without these fields are still valid
- Serialization skips None values (not included in JSON)

### Mixed-Schema Support

Systems can handle logs containing both v1.x and v2.0 events:
- v1.x events have `step_path` (no `feature_name`/`step_id`)
- v2.0 events have `feature_name`/`step_id` (no `step_path`)
- Queries must account for missing fields: `jq '.feature_name // "unknown"'`

---

## Performance Characteristics

### Write Performance

- **Append operation**: O(1) per event
- **File rotation**: Daily (negligible overhead)
- **Log directory creation**: One-time at initialization

### Read Performance (jq queries)

| Query Type | Complexity | Example |
|-----------|-----------|---------|
| Filter by field | O(n) | `jq 'select(.feature_name=="...")'` |
| Count aggregation | O(n) | `sort \| uniq -c` |
| Timeline sort | O(n log n) | `sort` by timestamp |
| All queries on files | O(n × m) | n = events, m = files |

---

## Error Handling

### JsonlAuditLogWriter Errors

| Error | Condition | Recovery |
|-------|-----------|----------|
| `OSError` | Log directory cannot be created | Fallback to global `~/.claude/des/logs/` |
| `PermissionError` | No write permission to log directory | Try next priority in resolution chain |
| JSON serialization fails | Event contains non-serializable object | Log as string representation |

### Missing Configuration

| Scenario | Behavior | Log Location |
|----------|----------|--------------|
| No `DES_AUDIT_LOG_DIR` | Check `.nwave/des-config.json` | Falls back to defaults |
| Invalid config JSON | Ignore file, use next priority | Falls back to defaults |
| No project-local path | Use global fallback | `~/.claude/des/logs/` |

---

## Related Documentation

- [DES Orchestrator API Reference](./des-orchestrator-api.md) — Main entry point for DES functionality
- [Recovery Guidance Handler API Reference](./recovery-guidance-handler-api.md) — Failure recovery guidance generation
- [Audit Trail Compliance Verification](./audit-trail-compliance-verification.md) — Audit trail integrity and compliance

---

**Version**: 2.0 (stable)
**Status**: Complete and Tested (797 mutants killed, 100% mutation score)
**Compliance**: JSONL format, append-only, immutable events
**Last Verified**: 2026-02-13
