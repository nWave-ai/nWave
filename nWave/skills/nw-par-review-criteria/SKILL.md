---
name: nw-par-review-criteria
description: Quality dimensions and review checklist for devop reviews
disable-model-invocation: true
---

# DevOp Reviewer: Review Criteria

## Critique Dimension 1: Incomplete Phase Handoffs

**Pattern**: Phase handoffs missing required artifacts or approvals.

**Required per Phase**:
- DISCUSS: Requirements document + peer review approval
- DESIGN: Architecture document + ADRs + peer review approval
- DISTILL: Acceptance tests + peer review approval
- DELIVER: Production code + tests (100% passing) + peer review approval

**Severity**: critical. Verify all artifacts present and peer-reviewed before phase transition.

---

## Critique Dimension 2: Deployment Readiness Gaps

**Pattern**: Feature marked "ready" but missing production prerequisites.

**Required**: All tests passing (100%) | Production configuration complete | Monitoring/alerting configured | Runbook/operational docs created | Rollback plan documented.

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

### Technical Completion
- [ ] All acceptance tests passing with stakeholder validation
- [ ] Unit test coverage meeting project standards (>=80%)
- [ ] Integration test validation of cross-component functionality
- [ ] Code review completed with approval
- [ ] Static analysis and security scan passed
- [ ] Performance tested under realistic load

### Architecture Compliance
- [ ] Implementation aligns with architectural design
- [ ] Component boundaries and interfaces respected
- [ ] Security architecture implemented correctly

### Production Readiness
- [ ] Monitoring and alerting configured
- [ ] Logging and debugging capability validated
- [ ] Rollback procedure documented and tested
- [ ] Operational runbook complete
- [ ] Support team trained / knowledge transferred

### Business Completion
- [ ] All user stories completed with acceptance criteria met
- [ ] Business rules implemented and validated
- [ ] Stakeholder acceptance obtained
