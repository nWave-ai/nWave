---
name: nw-dr-review-criteria
description: Critique dimensions, severity framework, verdict decision matrix, and review output format for documentation assessment reviews
disable-model-invocation: true
---

# Documentation Review Criteria

## Critique Dimensions

### 1. Classification Accuracy

Verify type assignment against DIVIO decision tree.

Questions: Do cited signals support assigned type? | Contradicting signals ignored? | Confidence appropriate? | Decision tree leads to same classification?

Verification: 1) Run decision tree independently 2) Check positive signals present 3) Check for red flags 4) Verify confidence matches signal strength

Severity: if wrong classification leads to wrong verdict = blocking.

### 2. Validation Completeness

Verify all type-specific criteria checked. Questions: All items checked? | Pass/fail correct? | Issues properly located? | Any criteria missed?

**Tutorial** (required): completable without external refs | steps numbered/sequential | verifiable outcomes | no assumed knowledge | builds confidence

**How-to** (required): clear goal | assumes fundamentals | single task | completion indicator | no basics teaching

**Reference** (required): all params documented | return values | error conditions | examples | no narrative

**Explanation** (required): addresses "why" | context/reasoning | alternatives considered | no task steps | conceptual model

### 3. Collapse Detection Correctness

Verify all five anti-patterns checked with accurate findings.
- Tutorial creep: explanation >20% | How-to bloat: teaching basics | Reference narrative: prose in entries
- Explanation task drift: steps in explanation | Hybrid horror: 3+ quadrants

Verification: independently scan, count lines per quadrant, compare to documentarist's findings, flag discrepancies.

### 4. Recommendation Quality

Criteria: **Specific** (exact what/where) | **Actionable** (author knows next step) | **Prioritized** (important first) | **Justified** (why it matters) | **Root cause** (underlying issue)

Bad: "Improve the documentation", "Make it clearer"
Good: "Move explanation in section 3.2 (lines 45-60) to separate doc", "Add return value docs for login()"

### 5. Quality Score Accuracy

Verify six characteristics: Accuracy (factual claims verified?) | Completeness (gap analysis thorough?) | Clarity (Flesch 70-80?) | Consistency (style 95%+?) | Correctness (errors counted?) | Usability (structural assessment?)

Note: Documentarist cannot fully measure accuracy (needs expert) or usability (needs user testing). Verify limitations properly scoped.

### 6. Verdict Appropriateness

Verify verdict matches findings per decision matrix below.

## Severity Framework

| Level | Definition | Action |
|-------|-----------|--------|
| Blocking | Wrong classification/verdict, missed collapse making doc unusable | Must fix |
| High | Multiple criteria missed, collapse missed but usable | Should fix; may block |
| Medium | Single criterion missed, miscalibrated confidence, false positive | Recommended |
| Low | Format inconsistency, wording clarity | Optional |

**Reject**: any blocking | 3+ high | classification wrong | verdict contradicts findings
**Conditionally approve**: 1-2 high not affecting verdict | multiple medium but core correct
**Approve**: no blocking/high | medium noted but not blocking

## Verdict Decision Matrix

- **Approved**: all checks pass or low-only failures | no collapse | quality gates met (Flesch 70-80, purity 80%+)
- **Needs Revision**: medium/low failures only | no collapse | fixable without restructuring
- **Restructure Required**: collapse detected | purity <80% | multiple user needs | requires splitting

### Verification Algorithm
1. Count issues by severity 2. Check collapse_detection.clean 3. Check quality gates 4. Apply matrix 5. Compare to documentarist verdict 6. Flag discrepancy

## Review Output Format

```yaml
documentation_assessment_review:
  review_id: "doc_rev_{timestamp}"
  reviewer: "nw-documentarist-reviewer (Quill)"
  assessment_reviewed: "{path}"
  original_document: "{path}"

  classification_review:
    accurate: [boolean]
    confidence_appropriate: [boolean]
    independent_classification: "[your type]"
    match: [boolean]
    issues: [{issue, evidence, severity, recommendation}]

  validation_review:
    complete: [boolean]
    criteria_checked: "[X/Y required + Z/W additional]"
    missed_criteria: [list]
    issues: [{issue, severity, recommendation}]

  collapse_detection_review:
    accurate: [boolean]
    independent_findings: "[anti-patterns found]"
    false_positives: [count]
    missed_patterns: [list]
    issues: [{issue, severity, recommendation}]

  recommendation_review:
    quality: [high|medium|low]
    actionable: [boolean]
    properly_prioritized: [boolean]
    issues: [{issue, severity, improvement}]

  quality_score_review:
    accurate: [boolean]
    issues: [{score, issue, correction}]

  verdict_review:
    appropriate: [boolean]
    documentarist_verdict: "[their verdict]"
    recommended_verdict: "[your verdict]"
    verdict_match: [boolean]
    rationale: "{justification}"

  overall_assessment:
    assessment_quality: [high|medium|low]
    approval_status: [approved|rejected_pending_revisions|conditionally_approved|escalate_to_human]
    issue_summary: {blocking: N, high: N, medium: N, low: N}
    blocking_issues: [list]
    recommendations: [{priority, action}]
```

## Review Iteration Limits

Maximum 2 revision cycles. After cycle 2: escalate to human, return `approval_status: escalate_to_human` with rationale.
