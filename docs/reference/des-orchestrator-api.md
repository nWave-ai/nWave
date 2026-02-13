# DES Orchestrator API Reference

## Overview

The `DESOrchestrator` provides the main entry point for DES (Deterministic Execution System) functionality including template validation, execution coordination, and timeout/turn discipline.

## Core Methods

### `validate_prompt(prompt: str) -> ValidationResult`

Validates a prompt for mandatory sections and TDD phases before task invocation.

**Parameters:**
- `prompt`: The full prompt text to validate

**Returns:**
- `ValidationResult` with status, errors, and `task_invocation_allowed` flag

### `execute_step(step_file_path: str, timeout_thresholds: list[int] | None = None) -> ExecuteStepResult`

Executes a single atomic step with turn counting and timeout monitoring.

**Parameters:**
- `step_file_path`: Path to step JSON file
- `timeout_thresholds`: Optional list of threshold percentages (e.g., [50, 75, 90])

**Returns:**
- `ExecuteStepResult` with success status, warnings emitted, and execution metrics

**Added in:** DES-US004 (Timeout and Turn Discipline)

### `request_extension(request: ExtensionRequest) -> ApprovalResult`

Requests a timeout/turn extension during step execution.

**Parameters:**
- `request`: ExtensionRequest with justification, requested turns/minutes, and context

**Returns:**
- `ApprovalResult` with approval decision and rationale

**Added in:** DES-US004 (Timeout and Turn Discipline)

## Related Components

- `TemplateValidator`: Pre-invocation validation
- `SubagentStopHook`: Post-execution validation
- `TurnCounter`: Turn tracking per phase
- `TimeoutMonitor`: Timeout warning emission
- `ExtensionApprovalEngine`: Extension request evaluation

## Location

`src/des/application/orchestrator.py`

## See Also

- [Recovery Guidance Handler API](./recovery-guidance-handler-api.md)
- [Audit Trail Compliance Verification](./audit-trail-compliance-verification.md)
- [Audit Log Refactor API Reference](./audit-log-refactor.md)
