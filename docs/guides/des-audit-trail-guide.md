# DES Audit Trail Guide

## Overview

The Deterministic Execution System (DES) maintains an immutable audit trail of all nWave workflow executions. This provides complete traceability and enables compliance validation.

## Audit Trail Structure

### Location

`.nwave/des/logs/audit-YYYY-MM-DD.log` (project-local) or `~/.claude/des/logs/audit-YYYY-MM-DD.log` (global fallback)

### Format

JSONL (JSON Lines) - one JSON object per line, newline-delimited.

```json
{"timestamp": "2026-02-01T10:30:45.123Z", "event": "TASK_INVOCATION_STARTED", "step_id": "01-01", "project_id": "plugin-arch", "agent": "software-crafter"}
{"timestamp": "2026-02-01T10:30:45.456Z", "event": "PHASE_STARTED", "step_id": "01-01", "phase_name": "RED_UNIT"}
{"timestamp": "2026-02-01T10:35:22.789Z", "event": "PHASE_COMPLETED", "step_id": "01-01", "phase_name": "RED_UNIT", "outcome": "PASS"}
```

### File Rotation

- Daily logs with date rotation
- File format: `audit-YYYY-MM-DD.log`
- New file created at midnight UTC
- Previous day's file remains (append-only)

## Events Logged

| Event | Description | Fields |
|-------|-------------|--------|
| `TASK_INVOCATION_STARTED` | Agent execution begins | step_id, project_id, agent |
| `TASK_INVOCATION_VALIDATED` | Pre-invocation hooks passed | step_id, validations_passed |
| `PHASE_STARTED` | TDD phase begins | step_id, phase_name |
| `PHASE_COMPLETED` | TDD phase finishes | step_id, phase_name, outcome, duration_seconds |
| `SCOPE_VIOLATION` | File modified outside declared scope | file_path, scope_declaration |
| `TIMEOUT_WARNING` | Phase execution exceeding threshold | step_id, phase_name, threshold_seconds, actual_seconds |
| `COMMIT_CREATED` | Git commit created | step_id, commit_hash, message |

## Query Examples

### Find all scope violations

```bash
grep '"event":"SCOPE_VIOLATION"' .nwave/des/logs/audit-*.log | jq .
```

### Count violations by file

```bash
jq -r 'select(.event=="SCOPE_VIOLATION") | .file_path' .nwave/des/logs/audit-*.log | sort | uniq -c | sort -rn
```

### View phase execution timeline

```bash
jq -r 'select(.event | startswith("PHASE_")) | "\(.timestamp) \(.step_id) \(.phase_name) \(.outcome)"' .nwave/des/logs/audit-*.log
```

### Find slow phases

```bash
jq -r 'select(.event=="PHASE_COMPLETED") | select(.duration_seconds > 600) | "\(.step_id) \(.phase_name) \(.duration_seconds)s"' .nwave/des/logs/audit-*.log
```

### Export audit trail as CSV

```bash
jq -r '[.timestamp, .event, .step_id, .phase_name] | @csv' .nwave/des/logs/audit-*.log > audit.csv
```

## Retention Policy

| Time Period | Action |
|-------------|--------|
| Days 0-90 | Live logs in `.nwave/des/logs/` |
| Day 91+ | Archive to `docs/evolution/audit-archive/` |
| Manual cleanup | No automatic deletion |

## Immutability & Integrity

Each log entry includes:
- ISO 8601 timestamp (UTC)
- SHA256 content hash (for integrity verification)
- Sequence number (for ordering guarantees)

To verify integrity:

```bash
jq -r '.content_hash' .nwave/des/logs/audit-2026-02-01.log | \
  while read hash; do
    echo -n "$hash " && echo "$hash" | sha256sum | cut -d' ' -f1
  done
```

Hashes should match (one per line).

## Compliance Use Cases

### Audit Trail Query for Compliance Report

```bash
# Generate compliance report for project X, dates Y-Z
jq -r 'select(.project_id=="plugin-arch") | select(.timestamp >= "2026-02-01" and .timestamp <= "2026-02-28") | "\(.timestamp) \(.step_id) \(.event) \(.outcome)"' \
  .nwave/des/logs/audit-*.log > plugin-arch-audit-2026-02.txt
```

### Verify Complete Execution

```bash
# Ensure all steps were executed for project X
project="plugin-arch"
steps=$(jq -r "select(.project_id==\"$project\") | select(.event==\"PHASE_COMPLETED\") | .step_id" .nwave/des/logs/audit-*.log | sort -u)
echo "Executed steps: $steps"
```

### Check for Scope Compliance

```bash
# Verify no scope violations in project X
violations=$(jq -r "select(.project_id==\"$project\") | select(.event==\"SCOPE_VIOLATION\")" .nwave/des/logs/audit-*.log | wc -l)
if [ "$violations" -eq 0 ]; then
  echo "✅ No scope violations"
else
  echo "❌ Found $violations scope violations"
fi
```
