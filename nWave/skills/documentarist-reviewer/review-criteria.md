---
name: review-criteria
description: Critique dimensions, severity framework, verdict decision matrix, and review output format for documentation assessment reviews
---

# Documentation Review Criteria

## Critique Dimensions

### 1. Classification Accuracy

Verify the documentarist's type assignment against the DIVIO decision tree.

Questions to ask:
- Do cited signals actually support the assigned type?
- Are there contradicting signals that were ignored?
- Is confidence level appropriate given the evidence?
- Would the decision tree lead to the same classification?

Verification steps:
1. Run classification decision tree independently
2. Check all positive signals for assigned type are present
3. Check for red flags that contradict classification
4. Verify confidence matches signal strength

Severity: if wrong classification leads to wrong verdict, treat as blocking.

### 2. Validation Completeness

Verify all type-specific validation criteria were checked.

Questions to ask:
- Were all type-specific validation items checked?
- Are checklist results accurate (pass/fail correctly assigned)?
- Are issues properly located (line/section references)?
- Were any validation criteria missed?

#### Validation Checklists by Type

**Tutorial** (required):
- New user can complete without external references
- Steps are numbered and sequential
- Each step has verifiable outcome
- No assumed prior knowledge
- Builds confidence, not just competence

**How-to** (required):
- Clear, specific goal stated
- Assumes reader knows fundamentals
- Focuses on single task
- Ends with task completion
- No teaching of basics

**Reference** (required):
- All parameters documented
- Return values specified
- Error conditions listed
- Examples provided
- No narrative explanation

**Explanation** (required):
- Addresses "why" not just "what"
- Provides context and reasoning
- Discusses alternatives considered
- No task-completion steps
- Builds conceptual model

### 3. Collapse Detection Correctness

Verify all five anti-patterns were checked and findings are accurate.

Anti-patterns to verify:
- **Tutorial creep**: Explanation content >20% in tutorial
- **How-to bloat**: Teaching basics in how-to
- **Reference narrative**: Prose paragraphs in reference entries
- **Explanation task drift**: Step-by-step instructions in explanation
- **Hybrid horror**: Content from 3+ quadrants

Verification steps:
1. Independently scan document for each anti-pattern
2. Count lines per quadrant to verify percentages
3. Compare your findings to documentarist's findings
4. Flag discrepancies

### 4. Recommendation Quality

Assess whether recommendations are actionable, specific, and prioritized.

Quality criteria:
- **Specific**: Says exactly what to change, where (line/section reference)
- **Actionable**: Author knows what to do next without further guidance
- **Prioritized**: Most important issues first
- **Justified**: Explains why it matters for documentation quality
- **Root cause**: Addresses underlying issue, not just symptoms

Bad examples: "Improve the documentation", "Make it clearer", "Consider revising"
Good examples: "Move explanation in section 3.2 (lines 45-60) to separate doc", "Add return value documentation for login()", "Remove teaching content from how-to; link to tutorial instead"

### 5. Quality Score Accuracy

Verify scores are justified and properly scoped.

Six characteristics to verify:
- **Accuracy**: Factual claims verified or flagged for expert review?
- **Completeness**: Gap analysis thorough?
- **Clarity**: Flesch score in 70-80 range or explained why not?
- **Consistency**: Style compliance 95%+ or issues noted?
- **Correctness**: Spelling/grammar errors counted accurately?
- **Usability**: Structural usability assessed?

Note: Documentarist cannot fully measure accuracy (requires expert review) or usability (requires user testing). Verify these limitations are properly scoped rather than claimed with false precision.

### 6. Verdict Appropriateness

Verify the verdict matches findings using the decision matrix below.

## Severity Framework

### Levels

| Level | Definition | Action |
|-------|-----------|--------|
| Blocking | Wrong classification/verdict, missed collapse making doc unusable | Must fix before proceeding |
| High | Multiple validation criteria missed, collapse missed but doc usable | Should fix; may block |
| Medium | Single criterion missed, slightly miscalibrated confidence, false positive | Recommended to fix |
| Low | Format inconsistency, wording clarity | Optional |

### Blocking Rules

**Reject** when: any blocking issue, 3+ high issues, classification demonstrably wrong, verdict contradicts findings.

**Conditionally approve** when: 1-2 high issues not affecting verdict, multiple medium issues but core assessment correct.

**Approve** when: no blocking or high issues, medium issues noted but not blocking.

## Verdict Decision Matrix

### Approved
- All validation checks pass or only low severity failures
- No collapse detected
- Quality gates met (Flesch 70-80, type purity 80%+)

### Needs Revision
- Medium or low severity validation failures only
- No collapse detected
- Issues fixable without restructuring

### Restructure Required
- Collapse detected (any anti-pattern triggered)
- Type purity below 80%
- Document serves multiple user needs
- Cannot be fixed without splitting

### Verification Algorithm
1. Count issues by severity
2. Check collapse_detection.clean
3. Check quality gates (readability, type_purity)
4. Apply matrix above
5. Compare to documentarist's verdict
6. Flag discrepancy if mismatch

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

- Maximum 2 revision cycles
- After cycle 2: escalate to human review if issues remain
- Return `approval_status: escalate_to_human` with rationale
