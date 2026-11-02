---
name: nw-sc-review-dimensions
description: Reviewer critique dimensions for peer review - implementation bias detection, test quality validation, completeness checks, and priority validation
user-invocable: false
disable-model-invocation: true
---

# Code Quality Critique Dimensions

When invoked in review mode, apply these critique dimensions to production code and tests.

Persona shift: from implementer (build solutions) to independent peer reviewer (critique solutions).
Focus: detect implementation bias | test quality issues | acceptance criteria coverage gaps.
Mindset: fresh perspective with critical analysis - assume nothing, verify everything.

Supply complete findings and a plain diagnostic judgment.

---

## Dimension 1: Implementation Bias Detection

### Over-Engineering (YAGNI Violations)

Pattern: features, abstractions, or infrastructure without corresponding acceptance criteria.

Examples: Caching layer without performance AC | Generic framework for single use case | Premature abstraction before Rule of Three | Design patterns without demonstrated complexity need | Infrastructure (queues, workers) without scale requirement.

Detection: Compare implementation against AC | Check if feature requested by stakeholder or assumed by developer | Verify performance requirements exist before optimization | Validate abstractions serve 3+ concrete cases.

Severity: Medium to High.

### Premature Optimization

Pattern: performance optimization without measurement proving necessity.

Examples: Custom caching without latency tests showing need | Complex O(log n) algorithms when simple O(n) meets AC | Memory optimizations without profiling data | Database denormalization without query analysis.

Detection: check for performance tests | verify AC specify thresholds | look for profiling data.
Severity: Medium.

### Solving Assumed Problems

Pattern: implementing solutions for problems not in acceptance criteria.

Examples: Multi-tenancy when AC specify single-tenant | Internationalization when AC require English only | Audit logging when AC don't mention compliance.

Detection: map each feature to corresponding AC, flag features without traceability.
Severity: Medium to High.

---

## Dimension 2: Test Quality Validation

### Implementation Coupling

Pattern: tests depend on implementation details, preventing refactoring.

Examples: Mocking domain objects or application services (violates port-boundary policy) | Asserting on private methods/fields/internal state | Tests break on refactoring despite behavior unchanged | Tests duplicate production logic to verify correctness.

Detection: Check if mocks used inside hexagon (domain/application layers) - VIOLATION | Verify tests call only public interfaces | Confirm tests validate observable behavior, not implementation | Check if Extract Method refactoring would break tests.

Severity: CRITICAL.

### Test Time

Pattern: a test exceeds the default budgets in a feature without a granted derogation, or exceeds its feature's derogation, or adapter fault injection exists in a feature without a granted derogation (`test:feedback-loop-budget` in `nw-cross-cutting-invariants`). Fault injection a granted derogation covers, including one the user elected to run in the default suite, is not a finding.

Detection: Measure every test in the diff with native per-test timing over at least nine sequential runs and judge it on the median, two or more runs over the budget on the same test also being a finding | Compare against the design's budgets and the feature's derogation ADR, if the design cites one | Check each formal law has a fast executable projection in the default suite.

Severity: CRITICAL when no granted derogation covers the overrun; reviewers never grant one.

### Shared Mutable State

Pattern: tests share state causing flakiness, order dependencies, parallel execution failures.

Examples: Database state not reset between tests | Static variables mutated across tests | File system state persists between tests | In-memory caches shared across test methods.

Detection: Run tests in random order - do they still pass? | Run tests in parallel - do they fail? | Check for test setup/teardown creating isolated state | Look for static fields, shared fixtures, class-level state.

Severity: HIGH.

### Port-Boundary Violations

Test doubles policy follows the port-boundary rules defined in the tdd-methodology skill.

Severity: HIGH to CRITICAL.

### Testing Theater Detection

Pattern: tests creating illusion of safety without verifying real behavior. Single most dangerous test quality issue -- undetected Testing Theater causes catastrophic production failures because the team believes code is tested when it is not.

**Concrete patterns to detect:**

| Pattern | Detection | Severity |
|---------|-----------|----------|
| Zero-assertion test | Test method contains no `assert` statement at all | BLOCKER |
| Tautological assertion | `assert result is not None`, `assert isinstance(...)`, `assert True`, `assertEqual(x, x)` as primary assertion | BLOCKER |
| Mock-dominated test | Test mocks the SUT or mocks return the expected value directly -- removing production code still passes | BLOCKER |
| Circular verification | Test recomputes expected value using same formula as production code | BLOCKER |
| Always-green test | `try/except` wrapping assertions, empty except blocks, bare `pass` in test body | BLOCKER |
| Fully-mocked SUT | Every dependency of the SUT is mocked -- test verifies mock wiring, not behavior | BLOCKER |
| Implementation-mirroring | Assertions only on `assert_called_once_with` / call counts without behavioral outcome check | HIGH |
| Assertion-free smoke test | Code executes but asserts only that no exception was thrown (unless that IS the stated requirement) | BLOCKER |
| Misleading test name | Test name says "validates X" or "rejects X" but assertion checks unrelated Y | HIGH |
| Hardcoded magic oracle | Expected values are unexplained magic numbers not traceable to business rules or AC | HIGH |

**Review checklist (apply to every new/modified test):**
1. Delete the production code this test covers -- does the test fail? If not: THEATER.
2. Introduce a logic bug (wrong calculation, swapped condition) -- does the test catch it? If not: THEATER.
3. Is every expected value traceable to an acceptance criterion or business rule? If not: SUSPICIOUS.
4. Does the test assert on observable behavior (return values, state changes, side effects at port boundaries)? If it only asserts on types, existence, or internal calls: THEATER.

Severity: BLOCKER for zero-assertion, tautological, mock-dominated, circular, always-green, fully-mocked SUT, and assertion-free patterns. HIGH for implementation-mirroring, misleading names, and hardcoded oracles. A test suite with Theater is worse than no tests -- it creates false confidence.

### Producer-Authored Tests

The acceptance designer owns every test; the recorded oracle and its supports
are legitimately part of the candidate diff. The implementation author adds no
unit tests and never edits, weakens, skips or deletes a recorded test. A test
path the candidate adds or changes beyond the recorded oracle is a finding of
category `test_modification`, severity blocker; the recommendation removes it
and moves the design quality into the production code.

---

## Dimension 3: Completeness Validation

### Missing Acceptance Criteria Coverage

Pattern: not all acceptance criteria have corresponding test coverage.

Detection: Map each AC to test cases | Check coverage report shows 100% AC mapped to tests | Verify error paths have test coverage | Confirm edge cases explicitly tested.

Severity: CRITICAL.

### Inadequate Error Scenario Coverage

Pattern: only happy path tested, error handling untested.

Examples: No test for network timeout during payment | No test for database unavailable | No test for invalid input validation | No test for business rule violations.

Detection: count happy path vs error path tests | check exception types have triggering tests.
Severity: HIGH.

---

## Dimension 4: Design Quality

Judge every changed unit against the method the producer applied; the skills
are the single source, this dimension does not restate them.

- **Quality axes** of `nw-code-craftsmanship`: readable, encapsulated,
  declarative, modular, performant, maintainable, decoupled, cohesive, secure.
  Report each violated axis with file:line and the observed evidence.
- **Bound paradigm**:
  - `object_oriented`: the Object Calisthenics, the Code Smells Hierarchy and
    the Refactoring Priority Premise of `nw-code-design-oo`, strict in domain
    and application code (adapters, DTOs and framework glue exempt). An anemic
    domain entity, or an application transaction script that holds a domain
    decision, is a finding of owner `design` when the DESIGN prescribed it and
    of owner `implementation` otherwise.
  - `functional`: the Functional Core and the refactoring order of
    `nw-code-design-fp`; a domain decision inside effectful code, or a declared
    law the diff breaks, is a finding.
  - `procedural`: the universal rules of `nw-code-craftsmanship` only.
- **Wrong state unrepresentable**: a rule the code checks at runtime that the
  types could make impossible is a finding (`nw-certainty-by-construction`).

Scan every Refactoring Priority Premise level and report every finding,
ordered by level, lowest first: a lower-level smell never hides a higher one,
and the producer removes them in that order.

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

## Review findings

For each finding supply:

| Fact | Content |
|---|---|
| Location | Supplied file:line, test identity or missing-obligation locator |
| Obligation | Violated criterion, authority fact or design rule |
| Observation | Concrete evidence, critique dimension and severity; distinguish measured facts from uncertainty |
| Remediation | Actionable correction for the artifact owner |
| Owner | Oracle, design, implementation or product |

Include testing-theater counterexamples, test modifications and paradigm-specific
design findings under the applicable obligation. Keep all independently actionable
findings; one defect does not hide another. The acceptance designer owns oracle
corrections. Preserve candidate source/oracle bytes and artifact ownership.
Host owns models and checker execution.
The final reviewer owns selection and sufficiency of the touched-file selected tests.
It reuses a complete applicable native result (host, CI or the normal commit hook)
whose source, test, argv and runtime inputs are unchanged, citing its original operator
and run; it executes only missing or affected checks, once. Reuse never waives a check.
Each run it executes is recorded with `nwdes review observation add` before it closes the review.
Selection is mechanical, never memory-picked. Each run text carries actual argv,
exit status, stdout and stderr, including empty or incomplete selection and absent
tooling. Missing, unrun or failing required evidence is a finding.

Summarize the judgment, supporting observations and capability or evidence limits.
Acceptance requires sufficient evidence; uncertainty is not a passing observation.
Leave the assessed artifact unchanged and return plain findings.

---

## Severity Classification

**Blocker** (instant rejection, no discussion): Testing Theater patterns (zero-assertion, tautological, mock-dominated, circular, always-green, fully-mocked SUT, assertion-free) | Test modification to accommodate implementation (G9 violation) | A test path added or changed beyond the recorded oracle.

**Critical** (must resolve before handoff): Test coupling to implementation (prevents refactoring) | Missing AC test coverage | Port-boundary violations in critical paths | Anemic domain entity or domain decision in an application transaction script (OO) | Domain decision inside effectful code (FP) | Insecure input, path or command handling.

**High** (strongly recommend resolving): Shared mutable state in tests | Major over-engineering | Inadequate error scenario coverage.

**Medium** (address if time permits): Premature optimization | Solving assumed problems.

**Low** (enhancement suggestions): Naming improvements outside the changed units.

**Design quality -> Severity Mapping:**
- Medium: RPP L1-L2 smells (readability, complexity) in changed units
- High: RPP L3-L6 smells, an Object Calisthenics violation in domain or application code, a violated quality axis
- Critical: as listed above

---

## Review Iteration Rules
- Iteration 1: comprehensive review with all critique dimensions
- Iteration 2 (if needed): verify critical/high issues resolved, check for new issues
- Max iterations: 2
- Escalation: if not approved after 2 iterations, escalate to human facilitator
