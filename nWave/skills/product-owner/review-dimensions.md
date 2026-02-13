---
name: review-dimensions
description: Requirements quality critique dimensions for peer review - confirmation bias detection, completeness validation, clarity checks, testability assessment, and priority validation
---

# Requirements Quality Critique Dimensions

When invoked in review mode, apply these critique dimensions to requirements documents.

Persona shift: from requirements analyst to independent requirements reviewer.
Focus: detect confirmation bias, validate completeness, ensure clarity and testability.
Mindset: fresh perspective -- assume nothing, challenge assumptions, verify stakeholder needs.

Return complete YAML feedback to calling agent for display to user.

---

## Dimension 1: Confirmation Bias Detection

### Technology Bias
Pattern: requirements assume specific technology without stakeholder requirement.
Examples: "Deploy to AWS" when deployment not discussed, "Use PostgreSQL" in requirements instead of architecture.
Detection: check for technology specifics (cloud, database, frameworks). Verify stakeholder interviews mentioned these.
Severity: HIGH (constrains solution space unnecessarily).

### Happy Path Bias
Pattern: requirements focus on successful scenarios, minimal error/exception coverage.
Examples: login documented but account lockout missing, payment success but fraud/timeout/decline not specified.
Detection: count happy path stories vs error scenarios. Check each story has "sad path" alternatives.
Severity: CRITICAL (incomplete requirements, production error handling missing).

### Availability Bias
Pattern: requirements reflect recent experiences or familiar patterns over comprehensive analysis.
Examples: "Same auth as previous project" without validating fit, requirements mirror competitor without stakeholder validation.
Detection: check if requirements justified by stakeholder needs or "like previous project."
Severity: MEDIUM (sub-optimal solution, missed opportunities).

---

## Dimension 2: Completeness Validation

### Missing Stakeholder Perspectives
Stakeholder groups to verify: end users (primary, secondary, occasional), business owners/sponsors, operations/support teams, compliance/legal, technical teams.
Detection: list stakeholder groups in requirements, check each group's needs represented, verify conflicting needs documented.
Severity: HIGH.

### Missing Error Scenarios
Required error scenarios: invalid input validation, authentication/authorization failures, network timeouts, external service unavailability, data integrity violations, concurrent modification conflicts, resource exhaustion.
Detection: for each user story, check for corresponding error scenarios.
Severity: CRITICAL.

### Missing Non-Functional Requirements
NFRs to validate: performance (latency, throughput), security (auth, data protection), scalability (concurrent users, data volume), reliability (uptime, error rates), compliance (regulatory, legal), accessibility (WCAG).
Detection: check NFR section exists, each NFR has measurable criteria, stakeholders provided expectations.
Severity: CRITICAL.

---

## Dimension 3: Clarity and Measurability

### Vague Performance Requirements
Pattern: qualitative terms without quantitative thresholds.
Vague: "System should be fast", "User-friendly interface", "Handle large volumes", "Highly available."
Detection: identify qualitative adjectives (fast, large, friendly, high, secure). Check for corresponding quantitative threshold.
Severity: HIGH.

### Ambiguous Requirements
Pattern: requirements interpretable multiple ways by different readers.
Detection: check if two architects could design differently from same requirements. Look for words with multiple meanings. Verify pronouns have clear antecedents.
Severity: HIGH.

---

## Dimension 4: Testability

### Non-Testable Acceptance Criteria
Pattern: AC not observable, measurable, or automatable.
Bad: "System should be easy to use", "Code should be maintainable."
Good: "User completes checkout in 3 or fewer clicks, 95% success rate", "Cyclomatic complexity at most 10, test coverage at least 80%."
Detection: for each AC, ask "Can an automated test verify this?" Check if AC specifies observable behavior with measurable pass/fail criteria.
Severity: CRITICAL.

---

## Dimension 5: Priority Validation

### Questions to Ask

**Q1: Is this the largest bottleneck?**
Does timing data show this is the primary problem? Is there a larger problem being ignored?

**Q2: Were simpler alternatives considered?**
Does the document include rejected alternatives? Are rejection reasons evidence-based?

**Q3: Is constraint prioritization correct?**
Are user-mentioned constraints quantified by impact? Is a minority constraint dominating the solution?

**Q4: Is the approach data-justified?**
Is the key decision supported by quantitative data? Would different data lead to different approach?

### Failure Conditions
- FAIL if Q1 = NO (wrong problem being addressed)
- FAIL if Q2 = MISSING (no alternatives considered)
- FAIL if Q3 = INVERTED (minority constraint dominating)
- FAIL if Q4 = NO_DATA and this is performance optimization

---

## Review Output Format

```yaml
review_id: "req_rev_{YYYYMMDD_HHMMSS}"
reviewer: "product-owner (review mode)"
artifact: "{document path}"
iteration: {1 or 2}

strengths:
  - "{Positive aspect with specific example}"

issues_identified:
  confirmation_bias:
    - issue: "{Specific bias detected}"
      severity: "critical|high|medium|low"
      location: "{Section or US-ID}"
      recommendation: "{How to address}"

  completeness_gaps:
    - issue: "{Missing stakeholder/scenario/NFR}"
      severity: "critical|high"
      location: "{Section}"
      recommendation: "{What to add}"

  clarity_issues:
    - issue: "{Vague or ambiguous requirement}"
      severity: "high"
      location: "{Requirement ID}"
      recommendation: "{How to clarify}"

  testability_concerns:
    - issue: "{Non-testable AC}"
      severity: "critical"
      location: "{AC-ID}"
      recommendation: "{How to make testable}"

  priority_validation:
    q1_largest_bottleneck: "YES|NO|UNCLEAR"
    q2_simple_alternatives: "ADEQUATE|INADEQUATE|MISSING"
    q3_constraint_prioritization: "CORRECT|INVERTED|NOT_ANALYZED"
    q4_data_justified: "JUSTIFIED|UNJUSTIFIED|NO_DATA"
    verdict: "PASS|FAIL"

approval_status: "approved|rejected_pending_revisions|conditionally_approved"
critical_issues_count: {number}
high_issues_count: {number}
```

---

## Severity Classification

- **Critical**: non-testable AC, missing error scenarios, missing NFRs, wrong problem addressed
- **High**: technology bias, happy path bias, vague requirements, missing stakeholders
- **Medium**: availability bias, minor completeness gaps, ambiguous wording
- **Low**: documentation formatting, terminology consistency
