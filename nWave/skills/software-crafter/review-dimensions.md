---
name: review-dimensions
description: Reviewer critique dimensions for peer review - implementation bias detection, test quality validation, completeness checks, and priority validation
---

# Code Quality Critique Dimensions

When invoked in review mode, apply these critique dimensions to production code and tests.

Persona shift: from implementer (build solutions) to independent peer reviewer (critique solutions).
Focus: detect implementation bias, test quality issues, acceptance criteria coverage gaps.
Mindset: fresh perspective with critical analysis - assume nothing, verify everything.

Return complete YAML feedback to calling agent for display to user.

---

## Dimension 1: Implementation Bias Detection

### Over-Engineering (YAGNI Violations)

Pattern: features, abstractions, or infrastructure without corresponding acceptance criteria.

Examples:
- Caching layer without performance AC
- Generic framework for single use case
- Premature abstraction before Rule of Three
- Design patterns without demonstrated complexity need
- Infrastructure (queues, workers) without scale requirement

Detection:
- Compare implementation against acceptance criteria
- Check if feature requested by stakeholder or assumed by developer
- Verify performance requirements exist before optimization
- Validate abstractions serve 3+ concrete cases

Severity: Medium to High.

### Premature Optimization

Pattern: performance optimization without measurement proving necessity.

Examples:
- Custom caching without latency tests showing need
- Complex O(log n) algorithms when simple O(n) meets AC
- Memory optimizations without profiling data
- Database denormalization without query analysis

Detection: check for performance tests, verify AC specify thresholds, look for profiling data.
Severity: Medium.

### Solving Assumed Problems

Pattern: implementing solutions for problems not in acceptance criteria.

Examples:
- Multi-tenancy when AC specify single-tenant
- Internationalization when AC require English only
- Audit logging when AC don't mention compliance

Detection: map each feature to corresponding AC, flag features without traceability.
Severity: Medium to High.

---

## Dimension 2: Test Quality Validation

### Implementation Coupling

Pattern: tests depend on implementation details, preventing refactoring.

Examples:
- Mocking domain objects or application services (violates port-boundary policy)
- Asserting on private methods, fields, or internal state
- Tests break on refactoring despite behavior unchanged
- Tests duplicate production logic to verify correctness

Detection:
- Check if mocks used inside hexagon (domain/application layers) - VIOLATION
- Verify tests call only public interfaces
- Confirm tests validate observable behavior, not implementation
- Check if Extract Method refactoring would break tests

Severity: CRITICAL.

### Shared Mutable State

Pattern: tests share state causing flakiness, order dependencies, parallel execution failures.

Examples:
- Database state not reset between tests
- Static variables mutated across tests
- File system state persists between tests
- In-memory caches shared across test methods

Detection:
- Run tests in random order - do they still pass?
- Run tests in parallel - do they fail?
- Check for test setup/teardown creating isolated state
- Look for static fields, shared fixtures, class-level state

Severity: HIGH.

### Port-Boundary Violations

Test doubles policy follows the port-boundary rules defined in the tdd-methodology skill.

Severity: HIGH to CRITICAL.

### Testing Theater Detection

Pattern: tests that create the illusion of safety without verifying real behavior. This is the single most dangerous test quality issue — undetected Testing Theater causes catastrophic production failures because the team believes the code is tested when it is not.

**Concrete patterns to detect:**

| Pattern | Detection | Severity |
|---------|-----------|----------|
| Tautological assertion | `assert result is not None`, `assert isinstance(...)`, `assert True` as primary assertion | CRITICAL |
| Mock-dominated test | Test mocks the SUT or mocks return the expected value directly — removing production code still passes | CRITICAL |
| Circular verification | Test recomputes expected value using same formula as production code | CRITICAL |
| Always-green test | `try/except` wrapping assertions, empty except blocks, no assertion at all | CRITICAL |
| Implementation-mirroring | Assertions only on `assert_called_once_with` / call counts without behavioral outcome check | HIGH |
| Assertion-free smoke test | Code executes but no assert statement validates outcomes | CRITICAL |
| Hardcoded magic oracle | Expected values are unexplained magic numbers not traceable to business rules or AC | HIGH |

**Review checklist (apply to every new/modified test):**
1. Delete the production code this test covers — does the test fail? If not: THEATER.
2. Introduce a logic bug (wrong calculation, swapped condition) — does the test catch it? If not: THEATER.
3. Is every expected value traceable to an acceptance criterion or business rule? If not: SUSPICIOUS.
4. Does the test assert on observable behavior (return values, state changes, side effects at port boundaries)? If it only asserts on types, existence, or internal calls: THEATER.

Severity: CRITICAL (blocks approval — a test suite with Theater is worse than no tests).

---

## Dimension 3: Completeness Validation

### Missing Acceptance Criteria Coverage

Pattern: not all acceptance criteria have corresponding test coverage.

Detection:
- Map each acceptance criterion to test cases
- Check coverage report shows 100% AC mapped to tests
- Verify error paths have test coverage
- Confirm edge cases explicitly tested

Severity: CRITICAL.

### Inadequate Error Scenario Coverage

Pattern: only happy path tested, error handling untested.

Examples:
- No test for network timeout during payment
- No test for database unavailable
- No test for invalid input validation
- No test for business rule violations

Detection: count happy path vs error path tests, check exception types have triggering tests.
Severity: HIGH.

---

## Dimension 4: RPP Code Smell Detection

Refactoring Priority Premise — cascading 6-level review. Apply RPP cascade rule:
scan and report lower levels first. Do not report L3+ issues until L1-L2 are clean.

### RPP Cascade Rule
1. Scan L1 first. If L1 smells found → report only L1, stop.
2. If L1 clean → scan L2. If L2 smells found → report L1 clean + L2 findings, stop.
3. Continue ascending only when lower levels are verified clean.
4. Exception: if `--from` and `--to` parameters specified, scan only that range.

### L1: Readability (Severity: LOW)
| Smell | Detection Pattern |
|-------|-------------------|
| Dead Code | Unused imports, unreachable branches, commented-out code |
| How-Comments | Comments explaining what code does (not why) |
| Magic Strings/Numbers | Literal values without named constants |
| Variable/Method Scope | Variables declared far from use, overly broad scope |
| Lazy Class | Classes with < 3 methods or single delegation |
| Speculative Generality | Abstractions without 3+ concrete uses |

### L2: Complexity (Severity: MEDIUM)
| Smell | Detection Pattern |
|-------|-------------------|
| Long Method | > 20 lines or multiple responsibilities |
| Duplicated Code | Same structure in 2+ places (≥ 3 lines) |
| Complex Conditionals | Nested if/else > 2 levels, boolean expressions with 3+ terms |

### L3: Responsibilities (Severity: HIGH)
| Smell | Detection Pattern |
|-------|-------------------|
| Large Class | > 300 lines or > 10 methods |
| Feature Envy | Method uses another object's data more than its own |
| Inappropriate Intimacy | Classes accessing each other's internals |
| Data Class | Only fields + getters/setters, no behavior |
| Message Chain | a.b().c().d() chains > 2 levels |
| Divergent Change | One class modified for unrelated reasons |
| Shotgun Surgery | One change requires edits in 5+ files |

### L4: Abstractions (Severity: HIGH)
| Smell | Detection Pattern |
|-------|-------------------|
| Long Parameter List | ≥ 4 parameters |
| Data Clumps | Same parameter group in 3+ method signatures |
| Primitive Obsession | Raw strings/ints for domain concepts |
| Middle Man | Class only delegates, no own logic |

### L5-L6: Advanced (report only when L1-L4 clean)
L5: Switch statements → polymorphism. L6: SOLID violations (Refused Bequest, Parallel Inheritance).

---

## Dimension 5: Priority Validation

Validate that the roadmap addresses the LARGEST bottleneck first.

### Questions

**Q1: Is this the largest bottleneck?**
Does timing data show this is the PRIMARY problem? Is there a larger problem being ignored?

**Q2: Were simpler alternatives considered?**
Does roadmap include rejected alternatives? Are rejection reasons evidence-based?

**Q3: Is constraint prioritization correct?**
Are user-mentioned constraints quantified by impact? Is a minority constraint dominating the solution?

**Q4: Is architecture data-justified?**
Is the key architectural decision supported by quantitative data?

### Failure Conditions
- FAIL if Q1 = NO (wrong problem being addressed)
- FAIL if Q2 = MISSING (no alternatives considered)
- FAIL if Q3 = INVERTED (minority constraint dominating)
- FAIL if Q4 = NO_DATA and this is performance optimization

---

## Review Output Format

Every review returns YAML in this format:

```yaml
review_id: "code_rev_{YYYYMMDD_HHMMSS}"
reviewer: "software-crafter (review mode)"
artifact: "{file paths reviewed}"
iteration: {1 or 2}

strengths:
  - "{Specific positive observation with file:line reference}"

issues_identified:
  implementation_bias:
    - issue: "{Specific pattern detected}"
      severity: "critical|high|medium|low"
      location: "{file:line-range}"
      recommendation: "{Actionable fix}"

  test_quality:
    - issue: "{Test coupling or quality issue}"
      severity: "critical|high"
      location: "{test_file:line}"
      recommendation: "{Fix description}"

  testing_theater:
    - issue: "{Specific theater pattern: tautological|mock-dominated|circular|always-green|implementation-mirroring|assertion-free|hardcoded-oracle}"
      severity: "critical"
      location: "{test_file:line}"
      evidence: "{Why this test would still pass if production code were deleted or broken}"
      recommendation: "{Rewrite with behavioral assertion or delete}"

  completeness:
    - issue: "{Missing coverage}"
      severity: "critical"
      location: "Missing test for AC-{number}"
      recommendation: "{Add test: GIVEN... WHEN... THEN...}"

  code_readability:
    - issue: "{Readability issue}"
      severity: "low"
      location: "{file:line}"
      recommendation: "{Extract methods: {names}}"

  rpp_smells:
    levels_scanned: "L1-L3"
    cascade_stopped_at: "L2"  # null if all clean
    findings:
      - level: "L2"
        smell: "Long Method"
        location: "{file:line}"
        evidence: "42 lines, 3 responsibilities"
        recommendation: "Extract Method: {names}"

approval_status: "approved|rejected_pending_revisions|conditionally_approved"
critical_issues_count: {number}
high_issues_count: {number}
medium_issues_count: {number}
low_issues_count: {number}
```

---

## Severity Classification

**Critical** (must resolve before handoff):
- Testing Theater patterns (false safety — blocks approval unconditionally)
- Test coupling to implementation (prevents refactoring)
- Missing acceptance criteria test coverage
- Port-boundary violations in critical paths

**High** (strongly recommend resolving):
- Shared mutable state in tests
- Major over-engineering
- Inadequate error scenario coverage

**Medium** (should address if time permits):
- Premature optimization
- Solving assumed problems

**Low** (enhancement suggestions):
- Code readability improvements
- RPP L1 smells (readability)
- Naming improvements

**RPP Level → Severity Mapping:**
- Low: L1 smells (readability — dead code, how-comments, magic values, scope, lazy class, speculative generality)
- Medium: L2 smells (complexity — long method, duplicated code, complex conditionals)
- High: L3-L4 smells (responsibilities, abstractions)
- Critical: unchanged (Testing Theater, port violations, missing AC coverage)

---

## Review Iteration Rules

- Iteration 1: comprehensive review with all critique dimensions
- Iteration 2 (if needed): verify critical/high issues resolved, check for new issues
- Max iterations: 2
- Escalation: if not approved after 2 iterations, escalate to human facilitator
