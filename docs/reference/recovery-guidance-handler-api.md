# Recovery Guidance Handler API Reference

## Overview

The `RecoveryGuidanceHandler` is a core component of the DES (Deterministic Execution System) failure recovery framework. It generates context-specific recovery guidance when failures are detected during task execution, helping users understand what went wrong and how to resolve it.

## Class: RecoveryGuidanceHandler

```python
class RecoveryGuidanceHandler:
    """Generate recovery suggestions for different failure modes with WHY + HOW + ACTION guidance."""

    def __init__(self):
        """Initialize recovery guidance handler with failure mode templates."""
```

## Methods

### generate_recovery_suggestions()

Generates a list of recovery suggestions for a specific failure type and context.

**Signature:**
```python
def generate_recovery_suggestions(
    failure_type: str,
    context: Dict[str, Any]
) -> List[str]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `failure_type` | str | Yes | Type of failure: `"abandoned_phase"`, `"missing_artifacts"`, `"timeout"`, or `"unknown"` |
| `context` | Dict[str, Any] | Yes | Context dictionary with failure-specific information (see below) |

**Returns:**
- `List[str]` - List of formatted recovery suggestions (minimum 3), each with WHY + HOW + ACTION sections

**Supported Failure Types:**

#### abandoned_phase
Suggests recovery when a TDD phase was left in IN_PROGRESS state after agent execution.

**Expected context fields:**
- `phase` (str, optional): Name of the abandoned phase (e.g., "RED_UNIT", "GREEN_UNIT")
- `step_file` (str, optional): Path to the step JSON file
- `transcript_path` (str, optional): Path to agent transcript/logs

**Example suggestion:**
```
WHY: The agent left {phase} in IN_PROGRESS state, indicating it started but did not complete.
     This blocks the TDD cycle from progressing to the next phase.

HOW: Resetting the phase to NOT_EXECUTED allows the execution framework to retry the phase.
     The agent transcript will indicate why it originally failed.

ACTION: Review agent transcript at {transcript_path} for error details.
        Then execute: /nw:execute @software-crafter "{step_file}"
```

#### missing_artifacts
Suggests recovery when expected artifacts (test files, implementation) are missing.

**Expected context fields:**
- `artifact_type` (str, optional): Type of missing artifact (e.g., "unit_test", "implementation")
- `phase` (str, optional): TDD phase that should have created the artifact
- `step_file` (str, optional): Path to the step JSON file

#### timeout
Suggests recovery when task execution exceeded time limit.

**Expected context fields:**
- `phase` (str, optional): Phase that timed out
- `timeout_seconds` (int, optional): How long execution ran
- `step_file` (str, optional): Path to the step JSON file

#### unknown
Fallback suggestions for unclassified failures.

### handle_failure()

Generates recovery suggestions AND persists them to the step file's state.recovery_suggestions field.

**Signature:**
```python
def handle_failure(
    step_file_path: str,
    failure_type: str,
    context: Dict[str, Any]
) -> Dict[str, Any]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `step_file_path` | str | Yes | Path to the step JSON file to update |
| `failure_type` | str | Yes | Type of failure detected |
| `context` | Dict[str, Any] | Yes | Context dictionary with failure information |

**Returns:**
- `Dict[str, Any]` - Updated step file data with recovery_suggestions persisted to `state.recovery_suggestions` array

**Side Effects:**
- Reads step JSON file
- Generates recovery suggestions via `generate_recovery_suggestions()`
- Updates step file's `state.recovery_suggestions` field (creates if doesn't exist)
- Writes updated step file back to disk

### format_suggestion()

Formats a single recovery suggestion with structured WHY + HOW + ACTION sections.

**Signature:**
```python
def format_suggestion(
    why_text: str,
    how_text: str,
    actionable_command: str
) -> str
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `why_text` | str | Yes | Explanation of why the failure occurred |
| `how_text` | str | Yes | Explanation of how to resolve it |
| `actionable_command` | str | Yes | Specific command or action to execute |

**Returns:**
- `str` - Formatted suggestion combining all three sections with clear separators

**Format:**
```
WHY: {why_text}

HOW: {how_text}

ACTION: {actionable_command}
```

## Usage Examples

### Generate suggestions for abandoned phase

```python
from src.des.application.recovery_guidance_handler import RecoveryGuidanceHandler

handler = RecoveryGuidanceHandler()

# Generate suggestions when a phase was abandoned
suggestions = handler.generate_recovery_suggestions(
    failure_type="abandoned_phase",
    context={
        "phase": "GREEN_UNIT",
        "step_file": "docs/feature/auth/steps/01-01.json",
        "transcript_path": ".nwave/des/logs/agent-01-01-green-unit.log"
    }
)

# suggestions is a list with 3+ recovery suggestions
for i, suggestion in enumerate(suggestions, 1):
    print(f"Suggestion {i}:\n{suggestion}\n")
```

### Handle failure and persist suggestions

```python
handler = RecoveryGuidanceHandler()

# Generate AND persist recovery suggestions to step file
updated_step = handler.handle_failure(
    step_file_path="docs/feature/auth/steps/01-01.json",
    failure_type="abandoned_phase",
    context={
        "phase": "RED_ACCEPTANCE",
        "step_file": "docs/feature/auth/steps/01-01.json",
        "transcript_path": ".nwave/des/logs/agent-01-01-red-acceptance.log"
    }
)

# Suggestions are now persisted to:
# updated_step["state"]["recovery_suggestions"] = [list of suggestions]
```

### Format a single suggestion

```python
handler = RecoveryGuidanceHandler()

suggestion = handler.format_suggestion(
    why_text="The agent failed to implement the required functionality",
    how_text="Review the test expectations and implement the missing code",
    actionable_command='Execute: /nw:execute @software-crafter "docs/feature/auth/steps/01-02.json"'
)

print(suggestion)
# Output:
# WHY: The agent failed to implement the required functionality
#
# HOW: Review the test expectations and implement the missing code
#
# ACTION: Execute: /nw:execute @software-crafter "docs/feature/auth/steps/01-02.json"
```

## Failure Mode Templates

The handler provides pre-built suggestion templates for common failure scenarios:

### Abandoned Phase (3+ suggestions)

1. **Reset and Retry**: Suggests resetting the phase state to NOT_EXECUTED and retrying execution
2. **Review Transcript**: Recommends reviewing agent transcript to understand why the phase was abandoned
3. **Check Context**: Suggests examining the phase execution context to identify missing prerequisites

### Missing Artifacts (2+ suggestions)

1. **Create Manually**: Instructions for manually creating missing test or implementation files
2. **Retry Generation**: Suggests re-executing the phase to generate artifacts

### Timeout (2+ suggestions)

1. **Increase Timeout**: Recommends increasing the timeout threshold for slow operations
2. **Optimize Code**: Suggests optimizing code performance to complete within time limit

## Integration with DES Framework

### SubagentStopHook Integration

The `SubagentStopHook` class uses `RecoveryGuidanceHandler` to detect failures after agent execution:

```python
from src.des.application.hooks import SubagentStopHook
from src.des.application.recovery_guidance_handler import RecoveryGuidanceHandler

hook = SubagentStopHook()
handler = RecoveryGuidanceHandler()

# After agent completes execution
result = hook.on_agent_complete(step_file_path)

# If failures detected, generate recovery guidance
if result.abandoned_phases:
    for phase_name in result.abandoned_phases:
        suggestions = handler.generate_recovery_suggestions(
            failure_type="abandoned_phase",
            context={
                "phase": phase_name,
                "step_file": step_file_path,
                "transcript_path": ".nwave/des/logs/..."
            }
        )
```

## Recovery Suggestion Format

All recovery suggestions follow a consistent structure:

```
WHY: [Explanation of the failure cause and impact on the TDD cycle]

HOW: [Explanation of the resolution approach and how it helps]

ACTION: [Specific, actionable command or instruction to resolve the issue]
```

### Example

```
WHY: The RED_ACCEPTANCE phase detected the acceptance test failed, but the agent
     did not complete PHASE 3 (RED_UNIT). This leaves the execution in an
     inconsistent state where unit tests are not yet defined.

HOW: Completing RED_UNIT will define the unit test contract before implementing.
     This follows the TDD discipline of RED → GREEN → REFACTOR.

ACTION: Execute: /nw:execute @software-crafter "docs/feature/auth/steps/01-01.json"
        The framework will resume from PHASE 3 (RED_UNIT).
```

## Error Handling

### Handling Missing Context

The handler gracefully handles missing context fields by using sensible defaults:

```python
# Missing phase name
suggestions = handler.generate_recovery_suggestions(
    failure_type="abandoned_phase",
    context={"step_file": "docs/feature/auth/steps/01-01.json"}
)
# Suggestion will reference "the abandoned phase" instead of specific phase name

# Missing transcript path
suggestions = handler.generate_recovery_suggestions(
    failure_type="abandoned_phase",
    context={"phase": "RED_UNIT"}
)
# Suggestion will not reference transcript location
```

### Unknown Failure Type

If an unknown failure_type is provided, the handler falls back to generic suggestions:

```python
suggestions = handler.generate_recovery_suggestions(
    failure_type="unknown_failure",
    context={}
)
# Returns 2+ generic recovery suggestions
```

## Persisting Suggestions to Step File

When `handle_failure()` is called, suggestions are persisted in the step JSON with this structure:

```json
{
  "state": {
    "recovery_suggestions": [
      "WHY: ...\n\nHOW: ...\n\nACTION: ...",
      "WHY: ...\n\nHOW: ...\n\nACTION: ...",
      "WHY: ...\n\nHOW: ...\n\nACTION: ..."
    ]
  }
}
```

## Testing

Unit tests verify:
- Suggestion generation for each failure type
- Proper formatting of WHY + HOW + ACTION sections
- Context variable substitution
- Persistence to step file
- Default values for missing context
- Multiple suggestions (3+) for complex failures
- Actionable elements (commands, paths, phase names)

See `tests/unit/des/test_recovery_guidance_handler.py` for comprehensive test suite.

## Location

`src/des/application/recovery_guidance_handler.py`

## See Also

- [DES Orchestrator API Reference](./des-orchestrator-api.md)
- [Audit Trail Compliance Verification](./audit-trail-compliance-verification.md)
- [Audit Log Refactor API Reference](./audit-log-refactor.md)

## Testing

Comprehensive test suite: `tests/unit/des/test_recovery_guidance_handler.py`
