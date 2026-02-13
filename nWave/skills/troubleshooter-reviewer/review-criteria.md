---
name: review-criteria
description: Review dimensions and scoring for root cause analysis quality assessment
---

# Troubleshooter Review Criteria

Detailed review dimensions and scoring for root cause analysis quality assessment.

## Dimension 1: Causality Logic

Check each WHY-to-WHY link in the causal chain.

**Pass criteria**:
- Each causal link has a logical mechanism (not just correlation)
- No steps are skipped in the chain
- Alternative explanations are considered and eliminated with reasoning
- The chain reads coherently in both directions (forward and backward)

**Common failures**:
- Correlation assumed as causation ("X happened before Y, so X caused Y")
- Causal chain gaps (WHY 2 does not logically follow from WHY 1)
- Single-path tunnel vision (first plausible cause accepted without alternatives)

**Severity**: Critical -- wrong root cause leads to ineffective fixes.

## Dimension 2: Evidence Quality

Verify that findings are grounded in observable data, not assumptions.

**Pass criteria**:
- Each WHY level cites specific evidence (log entries, metrics, config state, reproduction steps)
- Evidence is verifiable by a third party
- Timeline of events supports the claimed causality
- Hypotheses are explicitly marked as unverified

**Common failures**:
- "Probably because..." without supporting data
- Vague references ("the logs show issues" without specifics)
- Mixing verified facts with speculation without labeling

**Severity**: High -- unreliable analysis undermines trust in conclusions.

## Dimension 3: Alternative Hypotheses

Verify the analysis explored competing explanations before concluding.

**Pass criteria**:
- At least 2 alternative causes considered at WHY levels 1-3
- Each alternative either pursued as a parallel branch or eliminated with evidence
- "Why not" reasoning documented for rejected alternatives

**Common failures**:
- Analysis stops at first plausible cause
- Alternatives mentioned but not evaluated
- Confirmation bias (evidence selectively supports a predetermined conclusion)

**Severity**: High -- may miss the actual root cause.

## Dimension 4: Five-WHY Depth

Verify the analysis reaches fundamental causes, not intermediate symptoms.

**Pass criteria**:
- Each branch reaches WHY level 5 (or explicitly justifies stopping earlier with evidence that a true root cause was found)
- Final root causes are actionable (a fix can be designed)
- Root causes explain the symptoms when traced forward

**Common failures**:
- Stopping at WHY 2-3 (intermediate cause, not root)
- WHY 5 is vague or philosophical rather than specific and actionable
- Branches abandoned partway through

**Severity**: High -- shallow analysis leads to band-aid fixes that recur.

## Dimension 5: Completeness and Coverage

Verify all observed symptoms are accounted for.

**Pass criteria**:
- All reported symptoms have at least one causal branch
- Root causes collectively explain all symptoms
- No orphan symptoms (observed but unanalyzed)
- Cross-cause validation: multiple root causes do not contradict each other

**Common failures**:
- Some symptoms ignored or hand-waved
- Root causes explain primary symptom but not secondary ones
- Contradictory root causes proposed without reconciliation

**Severity**: Medium -- incomplete analysis leaves unaddressed failure modes.

## Dimension 6: Solution Traceability

Verify proposed solutions map to identified root causes.

**Pass criteria**:
- Every root cause has at least one corresponding solution
- Solutions distinguish immediate mitigations from permanent fixes
- No "orphan solutions" (proposed fix without a traced root cause)
- Prevention strategies address systemic factors, not just the specific instance

**Common failures**:
- Solutions address symptoms rather than root causes
- Root cause identified but no corresponding fix proposed
- Generic recommendations not tied to specific findings

**Severity**: Medium -- untraceable solutions are guesses.

## Review Output Format

```yaml
review_id: "rca_rev_{timestamp}"
reviewer: "nw-troubleshooter-reviewer"

dimensions:
  causality_logic:
    score: 0-10
    issues: [{issue, severity, recommendation}]
  evidence_quality:
    score: 0-10
    issues: [{issue, severity, recommendation}]
  alternative_hypotheses:
    score: 0-10
    issues: [{issue, severity, recommendation}]
  five_why_depth:
    score: 0-10
    issues: [{issue, severity, recommendation}]
  completeness:
    score: 0-10
    issues: [{issue, severity, recommendation}]
  solution_traceability:
    score: 0-10
    issues: [{issue, severity, recommendation}]

overall_score: "average of dimension scores"
approval_status: "approved | revisions_required"
summary: "1-2 sentence assessment"
```

## Scoring Guide

- **9-10**: Exemplary. No issues or only minor style suggestions.
- **7-8**: Good. Minor issues that do not affect conclusions.
- **5-6**: Adequate. Issues that weaken but do not invalidate the analysis.
- **3-4**: Poor. Issues that may lead to incorrect conclusions.
- **1-2**: Failing. Fundamental flaws that invalidate the analysis.

**Approval threshold**: overall score >= 7 and no dimension scores below 5.
