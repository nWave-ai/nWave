---
name: tdd-review-enforcement
description: Test design mandate enforcement, test budget validation, 5-phase TDD validation, and external validity checks for the software crafter reviewer
---

# TDD Review Enforcement

Domain knowledge for reviewing TDD implementations against the 5 test design mandates, test budget formula, 5-phase validation, and external validity.

---

## 5 Test Design Mandates

### Mandate 1: Observable Behavioral Outcomes

All test assertions validate observable outcomes, never internal structure.

Observable: return values from driving ports, state changes via queries, side effects at driven port boundaries, exceptions from public API, business invariants.

Violations: asserting private field values, verifying internal method call order, inspecting intermediate calculations, checking which internal classes are instantiated.

Severity: Blocker. Rewrite tests to assert observable outcomes only.

### Mandate 2: No Domain Layer Unit Tests

Zero unit tests of domain entities, value objects, or domain services directly. They are tested indirectly through application service (driving port) tests.

Violations: test file imports domain entity (Order, Customer), test instantiates value object directly (Money, Email), test invokes domain service method.

Exception: complex standalone algorithm with stable public interface (rare).

Severity: Blocker. Delete domain tests, add application service test instead.

### Mandate 3: Test Through Driving Ports

All unit tests enter through driving ports (application services, controllers, CLI handlers, event handlers). Never through internal classes.

Detection: grep test files for internal class imports (`from domain.entity`, `from internal.validator`).

Severity: Blocker. Rewrite through driving port.

### Mandate 4: Integration Tests for Adapters

Adapters have integration tests with real infrastructure (testcontainers, test servers). No mocked unit tests for adapters.

Violations: adapter test mocks IDbConnection, mocks SMTP client, uses stub instead of real infrastructure.

Acceptable: in-memory implementations if behavior-complete.

Severity: Blocker. Convert to integration test with real infrastructure.

### Mandate 5: Parametrized Input Variations

Input variations of same behavior use parametrized tests, not duplicate test methods.

Violations: test_valid_email_1/test_valid_email_2, copy-pasted tests with only inputs changed.

Severity: High. Consolidate into @pytest.mark.parametrize or equivalent.

---

## Test Budget Validation

Formula: `max_unit_tests = 2 x number_of_distinct_behaviors`

A behavior is ONE observable outcome from a driving port action. Edge cases of the same behavior count as ONE behavior (use parametrized tests).

### Counting Rules

One behavior: happy path for one operation, error handling for one error type, validation for one rule.

Not a behavior: testing internal class directly, same behavior with different inputs, testing getters/setters, testing framework code.

### Enforcement Steps

1. Count distinct behaviors in acceptance criteria
2. Calculate: `budget = 2 x behavior_count`
3. Count actual unit test methods (parametrized cases do not add to count)
4. Pass: actual <= budget. Fail: actual > budget (Blocker)

### Example Finding

```
TEST BUDGET VALIDATION: FAILED

Acceptance Criteria Analysis:
- "User can register with valid email" = 1 behavior
- "Invalid email format rejected" = 1 behavior
- "Duplicate email rejected" = 1 behavior

Budget: 3 behaviors x 2 = 6 unit tests maximum
Actual: 14 unit tests

Violations:
1. Budget exceeded: 14 > 6 (Blocker)
2. Internal class testing: test_user_validator.py tests UserValidator directly (Blocker)
3. Parameterization missing: 5 separate tests for valid email variations

Required: delete internal tests, consolidate via parametrize, re-submit
```

---

## 5-Phase TDD Validation

Verify all 5 phases present in execution-log.yaml: PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT.

### Phase Checks

- Phase completeness: all 5 entries present (Blocker if missing)
- Phase outcomes: all PASS (Blocker if any FAIL)
- Sequential execution: correct order by timestamps
- Test pass discipline: 100% green after GREEN, COMMIT

### Quality Gates to Verify

| Gate | Description | Phase |
|------|-------------|-------|
| G1 | Exactly one acceptance test active | PREPARE |
| G2 | Acceptance test fails for valid reason | RED_ACCEPTANCE |
| G3 | Unit test fails on assertion | RED_UNIT |
| G4 | No mocks inside hexagon | RED_UNIT |
| G5 | Business language in tests | GREEN |
| G6 | All tests green | GREEN |
| G7 | 100% passing before commit | COMMIT |
| G8 | Test count within budget | RED_UNIT |

Gates G2, G4, G7, G8 are Blockers if not verified.

Note: Review and refactoring quality are verified at deliver-level Phase 4 (Adversarial Review).

### Walking Skeleton Override

When reviewing a walking skeleton step (is_walking_skeleton: true):
- Do not flag missing unit tests (inner TDD loop skipped)
- Verify exactly one E2E test proves end-to-end wiring
- Thinnest slice acceptable (hardcoded values OK)
- RED_UNIT and GREEN phases may be SKIPPED with reason "NOT_APPLICABLE: walking skeleton"

---

## External Validity Check

Verify that features are invocable through entry points, not just existing in code.

Question: "If I follow these steps exactly, will the feature WORK or just EXIST?"

### Criteria

1. Acceptance tests import entry point modules, not internal components (Blocker)
2. At least one test invokes feature through user-facing entry point (High)
3. Implemented component is wired into system entry point (Blocker)

### Example Finding

```
EXTERNAL VALIDITY CHECK: FAILED

Issue: All 6 acceptance tests import des.validator.TemplateValidator directly.
No test imports des.orchestrator.DESOrchestrator (the entry point).

Consequence: Tests pass, coverage is 100%, but TemplateValidator is never
called in production because DESOrchestrator doesn't use it.

Required: update acceptance test to invoke through entry point, wire component.
```

---

## Approval Decision Logic

### Approved
All 5 phases present, all PASS, all gates satisfied, zero defects, test count within budget, no internal class tests.

### Rejected
Missing phases, any FAIL outcome, any defect of any severity, test budget exceeded, internal class tested directly. Zero tolerance: do not approve with known defects.

### Escalation
More than 2 review iterations, persistent gate failures, unresolved architectural violations. Escalate to tech lead.
