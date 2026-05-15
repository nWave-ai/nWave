---
name: nw-tdd-review-enforcement
description: Test design mandate enforcement, test budget validation, TDD phase validation (3-phase canon per ADR-025), and external validity checks for the software crafter reviewer
user-invocable: false
disable-model-invocation: true
---

# TDD Review Enforcement

Domain knowledge for reviewing TDD implementations against 5 test design mandates, test budget, TDD phase compliance (3-phase canon per ADR-025), and external validity.

---

## 5 Test Design Mandates

### Mandate 1: Observable Behavioral Outcomes
All assertions validate observable outcomes, never internal structure.

Observable: return values from driving ports | state changes via queries | side effects at driven port boundaries | exceptions from public API | business invariants

Violations: asserting private fields | verifying internal method call order | inspecting intermediate calculations | checking internal class instantiation

Severity: Blocker. Rewrite to assert observable outcomes only.

### Mandate 2: No Domain Layer Unit Tests
Zero unit tests of domain entities/value objects/services directly. Test indirectly through application service (driving port) tests.

Violations: imports domain entity (Order, Customer) | instantiates value object (Money, Email) | invokes domain service method

Exception: complex standalone algorithm with stable public interface (rare).
Severity: Blocker. Delete domain tests, add application service test.

### Mandate 3: Test Through Driving Ports
All unit tests enter through driving ports (application services, controllers, CLI handlers, event handlers). Never internal classes.

Detection: grep for internal imports (`from domain.entity`, `from internal.validator`).
Severity: Blocker. Rewrite through driving port.

### Mandate 4: Integration Tests for Adapters
Adapters have integration tests with real infrastructure (testcontainers, test servers). No mocked unit tests.

Violations: mocking IDbConnection | mocking SMTP client | stubs instead of real infrastructure
Acceptable: in-memory implementations if behavior-complete.
Severity: Blocker. Convert to integration test.

### Mandate 5: Parametrized Input Variations
Input variations of same behavior use parametrized tests, not duplicates.

Violations: test_valid_email_1/test_valid_email_2 | copy-pasted tests with only inputs changed
Severity: High. Consolidate into @pytest.mark.parametrize.

---

## Test Budget Validation

Formula: `max_unit_tests = 2 x number_of_distinct_behaviors`

A behavior = ONE observable outcome from a driving port action. Edge cases of same behavior = ONE (use parametrized).

### Counting Rules
One behavior: happy path for one operation | error handling for one error type | validation for one rule
Not a behavior: testing internal class | same behavior different inputs | testing getters/setters | testing framework code

### Enforcement Steps
1. Count distinct behaviors in AC | 2. Calculate `budget = 2 x count`
3. Count actual test methods (parametrized cases don't add) | 4. Pass: actual <= budget. Fail: actual > budget (Blocker)

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

## TDD Phase Validation (3-phase canon, ADR-025)

Verify TDD phases in execution-log.json. **Current canonical (ADR-025, 2026-05-07): 3-phase cycle — RED → GREEN → COMMIT.** RED absorbs the legacy PREPARE / RED_ACCEPTANCE / RED_UNIT phases — it unskips the AT scaffold authored by DISTILL, verifies fail-for-right-reason, and writes PBT unit tests ONLY when the AT requires them to reach GREEN.

**Legacy 5-phase contract (ADR-024 era)**: PREPARE / RED_ACCEPTANCE / RED_UNIT / GREEN / COMMIT — preserved for audit-log replay of pre-2026-05-07 commits. Existing execution-log.json files using the 5-phase contract remain valid; the gates below apply equivalently to merged phases under the 3-phase canon.

### Phase Checks
- Completeness: all phases present per the schema version in use (Blocker if missing) | Outcomes: all PASS (Blocker if FAIL)
- Sequential execution: correct order by timestamps | Test discipline: 100% green after GREEN, COMMIT

### Quality Gates

| Gate | Description | Phase (3-phase canon) | Legacy phase (5-phase) |
|------|-------------|-----------------------|------------------------|
| G1 | Exactly one acceptance test active | RED | PREPARE |
| G2 | Acceptance test fails for valid reason | RED | RED_ACCEPTANCE |
| G3 | Unit test fails on assertion (when authored) | RED | RED_UNIT |
| G4 | No mocks inside hexagon | RED | RED_UNIT |
| G5 | Business language in tests | GREEN | GREEN |
| G6 | All tests green | GREEN | GREEN |
| G7 | 100% passing before commit | COMMIT | COMMIT |
| G8 | Test count within budget | RED | RED_UNIT |
| G9 | No test modifications to accommodate implementation | GREEN | GREEN |

Gates G2, G4, G7, G8, G9 are Blockers if not verified.

Note: Review/refactoring quality verified at deliver-level Phase 4 (Adversarial Review).

### Walking Skeleton Override
When `is_walking_skeleton: true`: don't flag missing unit tests | verify exactly one E2E test | thinnest slice OK (hardcoded values) | unit-test authoring inside RED may be skipped (3-phase canon) or RED_UNIT/GREEN entries SKIPPED with "NOT_APPLICABLE: walking skeleton" (5-phase legacy logs).

---

## External Validity Check

Verify features are invocable through entry points, not just existing in code.

Question: "If I follow these steps, will the feature WORK or just EXIST?"

### Criteria
1. Acceptance tests import entry point modules, not internals (Blocker)
2. At least one test invokes through user-facing entry point (High)
3. Component wired into system entry point (Blocker)

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

## Test Modification Detection (ALWAYS BLOCKER)

The single worst TDD violation: modifying a test to make it pass instead of fixing the implementation. This inverts the TDD feedback loop -- the test no longer protects behavior. Instant rejection, no exceptions, no conditional approval.

### Detection Signals

| Signal | How to Detect | Severity |
|--------|---------------|----------|
| Test + implementation changed in same commit | Git diff shows test file edits alongside production code edits during GREEN phase | BLOCKER |
| Assertion weakened | `assertEquals(expected, actual)` changed to `assertNotNull(actual)` or `assertTrue(result)` | BLOCKER |
| Expectations reduced | Test previously checked 5 fields, now checks 1-2 | BLOCKER |
| Test deleted or skipped | `@skip`, `@pytest.mark.skip`, `@Disabled`, `xfail`, entire test method removed | BLOCKER |
| Deferred fix comments | `# TODO: fix later`, `# temporarily relaxed`, `# workaround`, `# adjusted for now` in test files | BLOCKER |
| Assertion count decreased | Previous commit had N assertions, current has fewer for same test | BLOCKER |

### Review Procedure

1. Compare test files at start of RED phase vs end of GREEN phase
2. If any test file was modified during GREEN: flag for detailed inspection
3. Check each modification against the signals table above
4. If modification is purely additive (new assertions, new test methods): PASS
5. If modification weakens, removes, or relaxes any existing assertion: BLOCKER -- reject immediately

### Legitimate Test Changes (Not Violations)

- Renaming test methods for clarity (no assertion changes)
- Adding new assertions to existing tests (strengthening, not weakening)
- Fixing a genuine test bug identified and approved by product owner (requires `ESCALATION_NEEDED` marker in execution log)
- Parametrization refactoring that preserves all original assertions

### Example Finding

```
TEST MODIFICATION DETECTION: BLOCKER

File: tests/unit/test_order_service.py
Commit: abc123 (GREEN phase)

Before (RED phase):
  assert result.total == Decimal("150.00")
  assert result.tax == Decimal("15.00")
  assert result.items == 3
  assert result.status == OrderStatus.CONFIRMED

After (GREEN phase):
  assert result is not None  # <-- weakened from 4 specific assertions to existence check

Verdict: REJECTED. Implementation could not satisfy the original assertions.
The crafter modified the test instead of fixing the implementation.
Required: revert test to RED-phase version, fix implementation to satisfy original assertions.
```

---

## Fixture Theater Detection (ALWAYS BLOCKER)

Acceptance tests pass because test fixtures implement the expected behavior directly, rather than exercising production code through the driving port. The tests verify the correct outcome from the wrong source. This is a form of Testing Theater where the entire GREEN phase is fraudulent -- no production code was changed.

### Detection Signals

| Signal | How to Detect | Severity |
|--------|---------------|----------|
| No production files in git diff | `git diff --name-only` after GREEN shows only test files, none of the `files_to_modify` entries | BLOCKER |
| Given steps create end-state | Test Given/Arrange steps construct the expected output directly instead of setting up preconditions for production code | BLOCKER |
| Fixture implements behavior | Test helper/fixture contains domain logic that should live in production code | BLOCKER |
| RED-to-GREEN without production changes | Acceptance test flips from failing to passing but `git diff --stat` shows zero production file changes | BLOCKER |

### Review Procedure

1. After GREEN phase, run `git diff --name-only` and compare against `files_to_modify` from the roadmap step
2. Every file listed in `files_to_modify` MUST appear in the diff (excluding test files). If any production file is missing: BLOCKER
3. Apply the **deletion test**: "If I revert ALL changes to test files and fixtures, does the acceptance test still pass with ONLY the production code changes?" If yes: production code is doing the work (PASS). If the test cannot pass without fixture changes: BLOCKER
4. Inspect test Given/Arrange sections for domain logic that belongs in production code

### Legitimate Exceptions (Not Violations)

- Step explicitly tagged as test-only (e.g., `files_to_modify` lists only test files)
- Documentation-only steps where no production code is expected
- Hash update steps where the production change is a constant update in a test file

### Example Finding

```
FIXTURE THEATER DETECTION: BLOCKER

Step: 02-01 (implement gitignore support in DES plugin)
Files to modify: [src/des/adapters/.../des_plugin.py]

git diff --name-only after GREEN:
  tests/des/acceptance/test_plugin_gitignore.py  (fixture modified)
  tests/conftest.py                               (helper added)

Missing from diff: src/des/adapters/.../des_plugin.py

Verdict: REJECTED. Agent modified test fixtures to produce expected state
instead of implementing production code in des_plugin.py.
The acceptance test passes because the fixture creates the expected output,
not because the driving port (DESPlugin.install()) produces it.
Required: revert fixture changes, implement production code in des_plugin.py.
```

---

## Escalation Verification

When a crafter gets stuck, the correct action is to escalate -- not to silently weaken tests. The reviewer verifies proper escalation protocol was followed.

### What to Check

1. **ESCALATION_NEEDED markers**: execution-log.json should contain `escalation_needed: true` with reason if the crafter hit a wall
2. **Three-attempt rule**: evidence of at least 3 distinct implementation attempts before any test change (check GREEN phase attempts in execution log)
3. **Product owner approval**: any requirement-driven test change must reference explicit PO approval (e.g., `po_approved: true` or `requirement_change: {ticket}` in execution log)

### Escalation Failures

| Failure | Detection | Severity |
|---------|-----------|----------|
| Silent test modification | No escalation marker + test weakened | BLOCKER |
| Insufficient attempts | Fewer than 3 GREEN attempts before test change | BLOCKER |
| Missing PO approval | Test changed for "requirement change" without PO reference | BLOCKER |
| Proper escalation | `ESCALATION_NEEDED` marker present, 3+ attempts logged | PASS (reviewer verifies test change validity) |

---

## Approval Decision Logic

### Approved
All required phases present per schema version (3-phase canon: RED/GREEN/COMMIT; legacy 5-phase: PREPARE/RED_ACCEPTANCE/RED_UNIT/GREEN/COMMIT), all PASS, all gates satisfied (G1-G9), zero defects, budget met, no internal class tests, no test modifications, no testing theater.

### Rejected
Missing phases | any FAIL | any defect | budget exceeded | internal class tested | test modified to accommodate implementation (G9) | testing theater detected | silent test modification without escalation. Zero tolerance.

### Escalation
>2 review iterations | persistent gate failures | unresolved architectural violations | crafter properly escalated (ESCALATION_NEEDED marker present with 3+ attempts). Escalate to tech lead.
