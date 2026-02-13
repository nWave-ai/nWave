# Step Template: mapped_scenario Field Reference

**Document Type**: Reference
**Last Updated**: 2026-01-24
**Template Location**: `~/.claude/templates/step-tdd-cycle-schema.json`

## Overview

This reference documents the `mapped_scenario` field added to step template JSON files to enforce step-to-scenario mapping in Outside-In TDD.

## Field Location in Schema

```json
{
  "tdd_cycle": {
    "acceptance_test": {
      "scenario_name": "...",
      "test_file": "...",
      "test_file_format": "feature",
      "scenario_index": 0,
      "initially_ignored": true,
      "is_walking_skeleton": false,
      "mapped_scenario": {                    // ← NEW FIELD
        "description": "...",
        "scenario_function": "...",
        "scenario_description": "...",
        "mapping_type": "feature",
        "valid_mapping_types": ["feature", "infrastructure", "refactoring"],
        "notes": "..."
      }
    }
  }
}
```

## Field Specification

### `mapped_scenario` Object

**Purpose**: Track which acceptance test scenario each step implements.

**Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `description` | string | Yes | Human-readable description of the mapping relationship |
| `scenario_function` | string | Conditional | Name of test function (e.g., `test_scenario_001_execute_command`) - optional for infrastructure/refactoring steps |
| `scenario_description` | string | Yes | Plain English description of what the scenario tests |
| `mapping_type` | string | Yes | Type of mapping: `feature`, `infrastructure`, or `refactoring` |
| `valid_mapping_types` | array | Reference | Valid values for mapping_type |
| `notes` | string | No | Additional context or exceptions |

## Mapping Types

### Feature (`feature`)

**Use for**: Normal acceptance test scenario that drives feature implementation.

**Requirements**:
- `scenario_function` MUST be populated
- `scenario_function` MUST match acceptance test file function name
- Step should make exactly 1 acceptance test pass (RED → GREEN)
- Must be counted toward step-to-scenario mapping validation

**Example**:
```json
{
  "mapped_scenario": {
    "description": "This step implements the test for execute command DES validation marker",
    "scenario_function": "test_scenario_001_execute_command",
    "scenario_description": "Execute command includes DES validation marker",
    "mapping_type": "feature",
    "valid_mapping_types": ["feature", "infrastructure", "refactoring"],
    "notes": null
  }
}
```

### Infrastructure (`infrastructure`)

**Use for**: Setup steps that don't have acceptance test scenarios (database migration, environment config, third-party provisioning).

**Requirements**:
- `scenario_function` MUST be empty/null
- `scenario_description` should document manual verification approach
- Step does NOT count toward feature scenario mapping validation
- Must be explicitly marked to skip scenario count validation

**Example**:
```json
{
  "mapped_scenario": {
    "description": "Infrastructure setup: Database migration for DES validation markers table",
    "scenario_function": null,
    "scenario_description": "Creates VALIDATION_MARKERS table in PostgreSQL; verified via SQL query",
    "mapping_type": "infrastructure",
    "valid_mapping_types": ["feature", "infrastructure", "refactoring"],
    "notes": "Manual verification: SELECT COUNT(*) FROM VALIDATION_MARKERS;"
  }
}
```

### Refactoring (`refactoring`)

**Use for**: Refactoring-only steps that improve code without changing behavior.

**Requirements**:
- `scenario_function` MUST be empty/null
- `scenario_description` should explain refactoring scope
- All acceptance tests must remain passing before and after
- Step does NOT count toward feature scenario mapping validation

**Example**:
```json
{
  "mapped_scenario": {
    "description": "Refactoring: Extract validation logic to separate class",
    "scenario_function": null,
    "scenario_description": "Refactor DES validation into ValidationMarkerService class; all tests remain passing",
    "mapping_type": "refactoring",
    "valid_mapping_types": ["feature", "infrastructure", "refactoring"],
    "notes": "No acceptance test changes; purely architectural improvement"
  }
}
```

## Validation Rules

### For Feature Steps
```javascript
// Validation rules enforced by /nw:deliver and /nw:execute
if (step.mapped_scenario.mapping_type === "feature") {
  assert(step.mapped_scenario.scenario_function !== null,
         "Feature steps MUST have scenario_function");
  assert(step.mapped_scenario.scenario_function.startsWith("test_"),
         "scenario_function must be valid test function name");
  // Count this step toward feature mapping validation
  count_feature_steps++;
}
```

### For Infrastructure/Refactoring Steps
```javascript
if (["infrastructure", "refactoring"].includes(step.mapped_scenario.mapping_type)) {
  assert(step.mapped_scenario.scenario_function === null,
         "Infrastructure/refactoring steps must NOT have scenario_function");
  // Do NOT count toward feature mapping validation
  count_feature_steps += 0;
}
```

### Master Validation: Step-to-Scenario Mapping
```javascript
// Enforced by /nw:deliver command before COMMIT phase
const num_acceptance_scenarios = count_test_functions(acceptance_test_file);
const num_feature_steps = steps.filter(s => s.mapped_scenario.mapping_type === "feature").length;

assert(num_feature_steps === num_acceptance_scenarios,
       `Step-to-Scenario Mapping Violated: ${num_feature_steps} feature steps != ${num_acceptance_scenarios} scenarios`);
```

## Example: Complete Step File with Mapping

```json
{
  "task_specification": {
    "task_id": "01-01",
    "acceptance_test_scenario": "test_scenario_001_execute_command",
    "acceptance_test_file": "tests/acceptance/test_us001_des_markers.py",
    "description": "Implement code to make test_scenario_001 pass (RED → GREEN)"
  },
  "tdd_cycle": {
    "acceptance_test": {
      "scenario_name": "test_scenario_001_execute_command",
      "test_file": "tests/acceptance/test_us001_des_markers.py",
      "test_file_format": "py_pytest",
      "scenario_index": 0,
      "initially_ignored": false,
      "is_walking_skeleton": true,
      "mapped_scenario": {
        "description": "Step 01-01 makes test_scenario_001 pass: Execute command includes DES validation marker",
        "scenario_function": "test_scenario_001_execute_command",
        "scenario_description": "When /execute command runs, DES validation marker is included in marker registry",
        "mapping_type": "feature",
        "valid_mapping_types": ["feature", "infrastructure", "refactoring"],
        "notes": null
      }
    },
    "expected_unit_tests": [
      "tests/unit/test_des_marker_registry.py::test_marker_registry_creation",
      "tests/unit/test_des_marker_registry.py::test_execute_command_marker_registration"
    ],
    "mock_boundaries": {
      "allowed_ports": ["FileSystemAdapter", "LoggingPort"],
      "forbidden_domain_classes": ["CommandParser"],
      "in_memory_adapters": ["InMemoryMarkerRegistry"]
    },
    "tdd_phase_tracking": {
      "current_phase": "NOT_STARTED",
      "active_e2e_test": "test_scenario_001_execute_command",
      "inactive_e2e_tests": "All other @skip scenarios remain disabled",
      "phases_completed": []
    },
    "phase_execution_log": [
      {
        "phase_name": "PREPARE",
        "phase_index": 0,
        "status": "NOT_EXECUTED",
        "started_at": null,
        "ended_at": null,
        "duration_minutes": null,
        "outcome": null,
        "outcome_details": null,
        "artifacts_created": [],
        "artifacts_modified": [],
        "test_results": {"total": null, "passed": null, "failed": null, "skipped": null},
        "notes": null,
        "blocked_by": null,
        "history": []
      }
    ]
  },
  "quality_gates": {
    "acceptance_test_must_fail_first": true,
    "unit_tests_must_fail_first": true,
    "no_mocks_inside_hexagon": true,
    "business_language_required": true,
    "refactor_level": 4,
    "in_memory_test_ratio_target": 0.8,
    "validation_after_each_phase": true,
    "validation_after_each_review": true,
    "validation_after_each_refactor": true,
    "all_14_phases_mandatory": true,
    "phase_documentation_required": true
  }
}
```

## Integration Points

### `/nw:deliver` Command (roadmap and step generation)
- Injects `mapped_scenario` when generating step files from roadmap
- Reads `acceptance_test_scenario` from roadmap step
- Validates scenario function exists in acceptance test file
- Sets `mapping_type` to `feature` by default

### `/nw:deliver` Command (solution-architect)
- Must include `acceptance_test_scenario` in each step definition
- Must match exactly to test function names
- Agent reads acceptance tests BEFORE creating roadmap

### `/nw:deliver` Wave Orchestrator
- Counts feature steps vs. acceptance scenarios
- Blocks roadmap creation if count mismatch detected
- Validation enforced during roadmap generation

### `/nw:execute` Command (software-crafter)
- Uses `mapped_scenario` to determine which test to run in Phase 2 (RED)
- Uses `mapped_scenario` to verify which test passes in Phase 6 (GREEN)
- Validates no regressions in other tests

## Error Messages

### Mapping Type Mismatch
```
❌ ERROR: Invalid mapping_type "feature_infra" in step 01-03
   Valid types: feature, infrastructure, refactoring
```

### Missing scenario_function for Feature
```
❌ ERROR: Feature step 01-01 missing required field scenario_function
   Feature steps MUST specify which test they implement
   Fix: Add "scenario_function": "test_scenario_001_execute_command"
```

### Feature/Infrastructure Confusion
```
❌ ERROR: Step 01-04 is type "infrastructure" but has scenario_function
   Infrastructure steps MUST NOT have scenario_function (no acceptance test)
   Fix: Set scenario_function to null OR change mapping_type to "feature"
```

### Scenario Function Not Found
```
❌ ERROR: Scenario function "test_scenario_007_missing" not found
   Searched in: tests/acceptance/test_us001_*.py
   Available scenarios: test_scenario_001_*, test_scenario_002_*, test_scenario_003_*
   Fix: Use exact test function name from acceptance test file
```

### Step-to-Scenario Mapping Violation
```
❌ CRITICAL: Step-to-Scenario Mapping Violated
   Acceptance scenarios: 4
   Feature steps: 11
   REQUIRED: number of feature steps MUST equal number of scenarios
   Reason: Outside-In TDD discipline requires 1 step per scenario

   Fix options:
   1. Reduce 7 steps by merging into existing scenario steps
   2. Add 7 more acceptance test scenarios
   3. Re-classify extra steps as "infrastructure" type

   Reference: docs/reference/step-template-mapped-scenario-field.md
```

## Best Practices

1. **Always map to acceptance tests**: Each feature step should trace directly to business scenario
2. **Use infrastructure type for setup**: Don't inflate feature step count with setup steps
3. **Document mapping clearly**: Use descriptive text in `scenario_description`
4. **Validate before split**: Ensure acceptance test exists before creating step file
5. **Keep mapping stable**: Don't change scenario_function between split and execute phases

## Related Documentation

- **How-to Guide**: [Execute DELIVER Wave with Step-to-Scenario Mapping](../guides/how-to-deliver-wave-step-scenario-mapping.md)
- **Template File**: `~/.claude/templates/step-tdd-cycle-schema.json` (installed via `nwave-ai install`)
- **Command Reference**: [nWave Commands Reference](./nwave-commands-reference.md)

---

**Document Owner**: AI-Craft Team
**Last Review**: 2026-01-24
**Schema Version**: 2.0.0
