# Reviewer Agents Reference

**Version**: 1.5.2
**Date**: 2026-01-22
**Status**: Production Ready

Quick reference for Layer 4 peer review agents - specifications, configuration, and lookup.

**Related Docs**:
- [How to invoke reviewers](../guides/how-to-invoke-reviewers.md) (how-to)
- [Layer 4 Implementation Summary](../guides/LAYER_4_IMPLEMENTATION_SUMMARY.md) (explanation)

---

## Reviewer Agents Matrix

| # | Primary Agent | Reviewer Agent | Persona | Focus |
|---|---------------|----------------|---------|-------|
| 1 | business-analyst | business-analyst-reviewer | Scout | Requirements bias, completeness, testability |
| 2 | solution-architect | solution-architect-reviewer | Atlas | Architectural bias, ADR quality, feasibility |
| 3 | acceptance-designer | acceptance-designer-reviewer | Sentinel | Happy path bias, GWT quality, coverage |
| 4 | software-crafter | software-crafter-reviewer | Mentor | Implementation bias, test coupling, complexity |
| 5 | knowledge-researcher | knowledge-researcher-reviewer | Scholar | Source bias, evidence quality, replicability |
| 6 | data-engineer | data-engineer-reviewer | Validator | Performance claims, query optimization, security |
| 7 | architecture-diagram-manager | architecture-diagram-manager-reviewer | Clarity | Visual clarity, consistency, accessibility |
| 8 | visual-2d-designer | visual-2d-designer-reviewer | Critic | 12 principles compliance, timing, readability |
| 9 | feature-completion-coordinator | feature-completion-coordinator-reviewer | Auditor | Handoff completeness, phase validation, traceability |
| 10 | root-cause-analyzer | root-cause-analyzer-reviewer | Logician | Causality logic, evidence quality, alternatives |
| 11 | walking-skeleton-helper | walking-skeleton-helper-reviewer | Minimalist | Minimal scope, E2E completeness, deployment viability |
| 12 | agent-forger | agent-forger-reviewer | Inspector | Template compliance, framework completeness, design patterns |

---

## Reviewer by Wave

### DISCUSS Wave
| Reviewer | When to Use |
|----------|-------------|
| business-analyst-reviewer | After requirements gathering |

### DESIGN Wave
| Reviewer | When to Use |
|----------|-------------|
| solution-architect-reviewer | After architecture design |
| architecture-diagram-manager-reviewer | After diagrams created |

### DISTILL Wave
| Reviewer | When to Use |
|----------|-------------|
| acceptance-designer-reviewer | After acceptance tests written |

### DEVELOP Wave
| Reviewer | When to Use |
|----------|-------------|
| software-crafter-reviewer | After implementation complete |
| data-engineer-reviewer | After database/query work |

### Cross-Wave
| Reviewer | When to Use |
|----------|-------------|
| knowledge-researcher-reviewer | After research completed |
| root-cause-analyzer-reviewer | After RCA investigation |
| visual-2d-designer-reviewer | After visual artifacts created |
| walking-skeleton-helper-reviewer | After skeleton implementation |
| feature-completion-coordinator-reviewer | After feature completion |
| agent-forger-reviewer | After agent creation |

---

## Agent Specification Files

**Location**: `nWave/agents/`

```
nWave/agents/
├── acceptance-designer-reviewer.md
├── agent-builder-reviewer.md
├── data-engineer-reviewer.md
├── devop-reviewer.md
├── documentarist-reviewer.md
├── illustrator-reviewer.md
├── product-discoverer-reviewer.md
├── product-owner-reviewer.md
├── researcher-reviewer.md
├── software-crafter-reviewer.md
├── solution-architect-reviewer.md
├── troubleshooter-reviewer.md
└── visual-architect-reviewer.md
```

---

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AICRAFT_LAYER4_ENABLED` | Enable Layer 4 reviews | `true` |
| `AICRAFT_MAX_ITERATIONS` | Maximum review iterations | `2` |
| `AICRAFT_AUTO_TRIGGER` | Auto-trigger after Layer 1 | `true` |
| `AICRAFT_BLOCK_HANDOFF` | Block handoff without approval | `true` |

### Configuration File

**Location**: `.nwave/layer4.yaml`

```yaml
layer_4_config:
  enabled: true

  automation:
    auto_trigger_after_layer_1: true
    auto_iterate: true
    max_iterations: 2

  quality_gates:
    block_handoff_without_approval: true
    escalate_after_max_iterations: true

  reviewers:
    business-analyst-reviewer:
      enabled: true
      auto_invoke_on: ["DISCUSS wave completion"]

    solution-architect-reviewer:
      enabled: true
      auto_invoke_on: ["DESIGN wave completion"]

    acceptance-designer-reviewer:
      enabled: true
      auto_invoke_on: ["DISTILL wave completion"]

    software-crafter-reviewer:
      enabled: true
      auto_invoke_on: ["DEVELOP wave completion"]

  metrics:
    collect_review_metrics: true
    export_to: ["prometheus", "datadog"]

  escalation:
    human_facilitator_email: "team-lead@example.com"
    escalation_timeout: "5 minutes"
```

---

## Review Feedback Format

Reviewers output structured YAML feedback:

```yaml
review_id: "rev_{timestamp}_{artifact_name}"
reviewer: "business-analyst-reviewer"
artifact: "docs/requirements/requirements.md"

strengths:
  - "Clear acceptance criteria for checkout flow"
  - "Well-defined user personas"

issues_identified:
  confirmation_bias:
    - issue: "Technology assumption without stakeholder requirement"
      impact: "May constrain solution options unnecessarily"
      recommendation: "Re-elicit deployment constraints from stakeholders"
      severity: "critical"

  completeness:
    - issue: "Missing error scenarios for payment failure"
      impact: "Incomplete test coverage"
      recommendation: "Add scenarios: card declined, timeout, fraud detection"
      severity: "high"

recommendations:
  - "Address critical issues before DESIGN wave"
  - "Quantify performance requirements"
  - "Add compliance requirements (PCI-DSS)"

approval_status: "rejected_pending_revisions"
iteration: 1
max_iterations: 2
```

### Approval Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| `approved` | All quality criteria met | Proceed to handoff |
| `rejected_pending_revisions` | Issues require fixes | Revise and resubmit |
| `conditionally_approved` | Minor issues, can proceed | Document caveats |

### Severity Levels

| Severity | Definition | Action |
|----------|------------|--------|
| `critical` | Blocks progression, must fix | Fix before resubmission |
| `high` | Significant impact, should fix | Fix before resubmission |
| `medium` | Moderate impact | Fix if time permits |
| `low` | Minor improvement | Optional |

---

## Handoff Triggers

### Wave Completion Triggers

| Transition | Reviewer Required |
|------------|-------------------|
| DISCUSS -> DESIGN | business-analyst-reviewer |
| DESIGN -> DISTILL | solution-architect-reviewer |
| DISTILL -> DEVELOP | acceptance-designer-reviewer |
| DEVELOP -> DELIVER | software-crafter-reviewer |

### Quality Gate Configuration

```yaml
handoff_quality_gate:
  condition: reviewer_approval_obtained == true
  on_failure:
    action: block_handoff
    message: "Artifact requires peer review approval before handoff"
    next_step: invoke_reviewer
```

---

## Metrics Reference

### Review Effectiveness

| Metric | Target | Description |
|--------|--------|-------------|
| Issues per review | > 3 | Reviewer finding value |
| First iteration approval | 40-60% | Balanced difficulty |
| Critical issues caught | > 0.5 per review | Preventing defects |

### Revision Cycle

| Metric | Target | Alert |
|--------|--------|-------|
| Iterations to approval | <= 1.5 | > 1.8 indicates problems |
| Revision cycle time | < 2 days | > 5 days is bottleneck |
| Issue resolution rate | > 90% | < 80% indicates quality problems |

### Quality Impact

| Metric | Target | Baseline |
|--------|--------|----------|
| Handoff rejection post-review | < 10% | 30-40% without review |
| Defect escape rate | < 5% | Issues missed by reviewer |

---

## Troubleshooting Quick Reference

| Symptom | Cause | Solution |
|---------|-------|----------|
| "Reviewer not found" | Reviewers not in build | Use Task tool manual invocation |
| Review not triggered | Layer 4 disabled | Check `AICRAFT_LAYER4_ENABLED` |
| Infinite loop | Max iterations not set | Set `max_iterations: 2` |
| No feedback | Wrong output format | Check YAML structure |

---

**Last Updated**: 2026-01-21
**Type**: Reference
**Purity**: 98%+
