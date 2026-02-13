---
name: review-output-format
description: YAML output format and approval criteria for platform design reviews. Load when generating review feedback.
---

# Platform Review Output Format

## YAML Structure

```yaml
review_id: "platform_rev_{timestamp}"
reviewer: "nw-platform-architect-reviewer (Atlas)"
artifact_reviewed: "{path to platform design documents}"
review_date: "{ISO 8601 timestamp}"

external_validity_check:
  deployment_path_complete: "{PASS/FAIL}"
  observability_enabled: "{PASS/FAIL}"
  rollback_capability: "{PASS/FAIL}"
  security_gates_present: "{PASS/FAIL}"
  overall_status: "{PASS/FAIL/BLOCKER}"
  blocking_issues:
    - "{issue description if any}"

strengths:
  - category: "{pipeline/infrastructure/deployment/observability/security}"
    description: "{what is done well}"
    evidence: "{specific example from design}"

issues_identified:
  - id: 1
    category: "{pipeline/infrastructure/deployment/observability/security}"
    dimension: "{critique dimension name}"
    severity: "{blocker/critical/high/medium/low}"
    description: "{clear description}"
    impact: "{consequence if not addressed}"
    recommendation: "{specific, actionable fix}"
    evidence: "{where in the design this was found}"

dora_metrics_assessment:
  deployment_frequency_enabled: "{yes/no/partial}"
  lead_time_achievable: "{yes/no/partial}"
  change_failure_rate_trackable: "{yes/no/partial}"
  time_to_restore_measurable: "{yes/no/partial}"
  assessment_notes: "{specific observations}"

priority_validation:
  largest_bottleneck_addressed: "{YES/NO/UNCLEAR}"
  simple_alternatives_documented: "{ADEQUATE/INADEQUATE/MISSING}"
  constraint_prioritization: "{CORRECT/INVERTED/NOT_ANALYZED}"
  verdict: "{PASS/FAIL}"

recommendations:
  immediate:
    - "{must fix before approval}"
  short_term:
    - "{should fix soon}"
  long_term:
    - "{consider for future improvement}"

approval_status: "{approved/rejected_pending_revisions/conditionally_approved}"
conditions_for_approval:
  - "{condition if conditionally_approved}"
```

## Approval Criteria

**Approved**: No blocker or critical issues. High issues acknowledged with timeline.

**Conditionally approved**: No blockers. Critical issues have mitigation plan. High issues documented for follow-up.

**Rejected (pending revisions)**: Any blocker present, multiple critical issues without mitigation, or external validity check failed.
