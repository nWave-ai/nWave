---
name: nw-tr-review-criteria
description: Review dimensions and scoring for root cause analysis quality assessment
disable-model-invocation: true
---

# Troubleshooter Review Criteria

Review dimensions and scoring for root cause analysis quality assessment.

## Dimension 1: Causality Logic

Check each WHY-to-WHY link.

Pass: logical mechanism (not just correlation) | no skipped steps | alternatives considered/eliminated | chain reads coherently both directions

Failures: correlation assumed as causation | causal chain gaps | single-path tunnel vision (first plausible cause accepted)

Severity: Critical -- wrong root cause = ineffective fixes.

## Dimension 2: Evidence Quality

Verify findings grounded in observable data.

Pass: each WHY cites specific evidence (logs, metrics, config, repro steps) | evidence verifiable by third party | timeline supports causality | hypotheses marked unverified

Failures: "Probably because..." without data | vague references ("logs show issues") | mixing facts with speculation unlabeled

Severity: High -- unreliable analysis undermines trust.

## Dimension 3: Alternative Hypotheses

Verify competing explanations explored.

Pass: 2+ alternatives at WHY 1-3 | each pursued or eliminated with evidence | "why not" reasoning documented

Failures: stops at first plausible cause | alternatives mentioned but unevaluated | confirmation bias

Severity: High -- may miss actual root cause.

## Dimension 4: Five-WHY Depth

Verify analysis reaches fundamental causes.

Pass: each branch reaches WHY 5 (or justifies stopping with evidence) | final causes are actionable | causes explain symptoms when traced forward

Failures: stopping at WHY 2-3 | WHY 5 vague/philosophical not actionable | branches abandoned

Severity: High -- shallow analysis = band-aid fixes that recur.

## Dimension 5: Completeness and Coverage

Verify all symptoms accounted for.

Pass: all symptoms have causal branch | root causes collectively explain all | no orphan symptoms | cross-cause validation (no contradictions)

Failures: symptoms ignored | root causes explain primary but not secondary | contradictory causes without reconciliation

Severity: Medium -- incomplete analysis leaves unaddressed failures.

## Dimension 6: Solution Traceability

Verify solutions map to root causes.

Pass: every root cause has solution | immediate mitigations vs permanent fixes distinguished | no orphan solutions | prevention addresses systemic factors

Failures: solutions address symptoms not causes | root cause without fix | generic recommendations untied to findings

Severity: Medium -- untraceable solutions are guesses.

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

- **9-10**: Exemplary. No issues or minor style only.
- **7-8**: Good. Minor issues not affecting conclusions.
- **5-6**: Adequate. Issues weaken but don't invalidate.
- **3-4**: Poor. Issues may lead to incorrect conclusions.
- **1-2**: Failing. Fundamental flaws invalidate analysis.

**Approval threshold**: overall >= 7 and no dimension below 5.
