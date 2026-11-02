---
name: nw-par-review-criteria
description: Quality dimensions and review checklist for devop reviews
user-invocable: false
disable-model-invocation: true
---

# DevOp Reviewer: Review Criteria

Apply criteria only to the authorized operational/design scope and actual
deployment promise. This skill defines review dimensions, not a mandatory phase
sequence or artifact set. Existing authority and explicit no-rollout applicability
are valid. Project thresholds need their own evidence; percentages/time targets
below are not universal gates. Use the role-owned platform assessment in
`nw-typesafe-system-one`; local verified reasons and distinct real observations
decide findings, and scalar scores never compensate blockers.

Load `nw-cross-cutting-invariants` and apply `flow:findings-go-to-the-owner-directly` when exchanging findings or questions between roles.

## Critique Dimension 1: Handoff adequacy

Compare the supplied authority/evidence against the operational decisions actually
consumed by this task. A missing load-bearing interface, environment or recovery
fact is a concrete finding; no fixed DISCUSS/DESIGN/DISTILL/DELIVER artifact or
approval set is mandatory. DESIGN self-check is not an independent approval.
Severity follows the consequence of the specific gap, not a phase label.

---

## Critique Dimension 2: Deployment Readiness Gaps

**Pattern**: Feature marked "ready" but missing production prerequisites.

Require only the selected rollout's prerequisites: relevant current tests, configuration, promised telemetry, recovery and operational responsibilities. A document-only/no-rollout plan may be complete while live readiness remains unobserved; never require production validation outside authorization.

**Severity**: critical. Complete missing prerequisite before marking deployment-ready.

---

## Critique Dimension 3: Traceability Violations

**Pattern**: Cannot trace production code back to requirements.

**Required**: User stories map to acceptance tests | Acceptance tests map to production code | Code changes traceable to commits | All AC verified in production.

**Severity**: high. Establish traceability chain: user-story -> acceptance-tests -> code-commits.

---

## Critique Dimension 4: Priority Validation

**Purpose**: Validate roadmap addresses largest bottleneck first, not secondary concern.

### Questions

**Q1: Is this the largest bottleneck?**
Does timing data show primary problem? Larger problem being ignored? Assessment: YES / NO / UNCLEAR.

**Q2: Were simpler alternatives considered?**
Roadmap includes rejected alternatives? Rejection reasons evidence-based? Simpler solution achieves 80% benefit? Assessment: ADEQUATE / INADEQUATE / MISSING.

**Q3: Is constraint prioritization correct?**
Constraints quantified by impact? Architecture addresses constraint-free opportunities first? Minority constraint dominating? (flag if >50% of solution for <30% of problem). Assessment: CORRECT / INVERTED / NOT_ANALYZED.

**Q4: Is architecture data-justified?**
Key architectural decision supported by quantitative data? Different data leads to different architecture? Assessment: JUSTIFIED / UNJUSTIFIED / NO_DATA.

### Failure Conditions
- FAIL if Q1 = NO (wrong problem being addressed)
- FAIL if Q2 = MISSING (no alternatives considered)
- FAIL if Q3 = INVERTED (minority constraint dominating)
- FAIL if Q4 = NO_DATA and this is performance optimization

---

## Critique Dimension 5: Functional Integration

**Purpose**: Verify feature wired into system entry point -- prevents Testing Theatre.
A feature with 100% test coverage but 0% wiring tests is not complete.

**Validation Criteria**:
1. **Wiring test exists**: at least one acceptance test invokes feature through driving port
2. **Component integrated**: implemented component called from entry point module
3. **Boundary correct**: acceptance tests do not import internal components directly

**Gate failure response**: Block finalization | report specific integration gap with evidence | require integration step before completion.

---

## Quality Gate Checklist

### Applicable technical and architecture evidence
- Declared obligations have native tests/observations through their real boundaries.
- Required project checks and review are current; source/oracle/runtime identity is known.
- Interfaces, invariant owners, security and build/discovery agree with the selected design.
- Coverage, performance and security measures are supplied only where applicable,
  under project criteria; no universal coverage percentage or tooling requirement.

### Applicable operational evidence
- A selected live rollout has concrete promotion/failure/rollback conditions.
- Recovery and persistent-data claims distinguish designed plans from observed runs.
- Promised KPI/SLO signals trace to collection, alert/runbook and responsibility.
- Training/support/runbooks are required only when the authorized scope needs them.

### Scope and readiness
- All original promises and authorized human exclusions/amendments are respected.
- No producer-only reduction, missing required boundary or stale evidence is approved.
- Operational document review authorizes no deploy, infrastructure mutation or successor.
- Unknown/not-applicable carries a concrete cause; a no-rollout feature buys no fake IaC.
