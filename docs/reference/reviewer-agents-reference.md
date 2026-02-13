# Reviewer Agents Reference

**Version**: 2.1.0
**Date**: 2026-02-13
**Status**: Production Ready

Quick reference for peer review agents - specifications, configuration, and lookup.

**Related Docs**:
- [How to invoke reviewers](../guides/invoke-reviewer-agents.md) (how-to)

---

## Reviewer Agents Matrix

| # | Primary Agent | Reviewer Agent | Focus |
|---|---------------|----------------|-------|
| 1 | product-discoverer | product-discoverer-reviewer | Discovery evidence quality, sample sizes, bias detection |
| 2 | product-owner | product-owner-reviewer | Requirements bias, completeness, testability |
| 3 | solution-architect | solution-architect-reviewer | Architectural bias, ADR quality, feasibility |
| 4 | platform-architect | platform-architect-reviewer | Deployment readiness, CI/CD quality, infrastructure |
| 5 | acceptance-designer | acceptance-designer-reviewer | Happy path bias, GWT quality, coverage |
| 6 | software-crafter | software-crafter-reviewer | Implementation bias, test coupling, complexity |
| 7 | researcher | researcher-reviewer | Source bias, evidence quality, replicability |
| 8 | troubleshooter | troubleshooter-reviewer | Causality logic, evidence quality, alternatives |
| 9 | data-engineer | data-engineer-reviewer | Performance claims, query optimization, security |
| 10 | documentarist | documentarist-reviewer | DIVIO compliance, classification accuracy, collapse detection |
| 11 | agent-builder | agent-builder-reviewer | Template compliance, framework completeness, design patterns |

---

## Reviewer by Wave

### DISCOVER Wave
| Reviewer | When to Use |
|----------|-------------|
| product-discoverer-reviewer | After discovery research and validation |

### DISCUSS Wave
| Reviewer | When to Use |
|----------|-------------|
| product-owner-reviewer | After requirements gathering |

### DESIGN Wave
| Reviewer | When to Use |
|----------|-------------|
| solution-architect-reviewer | After architecture design |

### DEVOP Wave
| Reviewer | When to Use |
|----------|-------------|
| platform-architect-reviewer | After platform/infrastructure design |

### DISTILL Wave
| Reviewer | When to Use |
|----------|-------------|
| acceptance-designer-reviewer | After acceptance tests written |

### DELIVER Wave
| Reviewer | When to Use |
|----------|-------------|
| software-crafter-reviewer | After implementation complete |
| data-engineer-reviewer | After database/query work |

### Cross-Wave
| Reviewer | When to Use |
|----------|-------------|
| researcher-reviewer | After research completed |
| troubleshooter-reviewer | After RCA investigation |
| documentarist-reviewer | After documentation created |
| agent-builder-reviewer | After agent creation |

---

## Agent Specification Files

**Location**: `~/.claude/agents/nw/`

```
~/.claude/agents/nw/
├── nw-acceptance-designer-reviewer.md
├── nw-agent-builder-reviewer.md
├── nw-data-engineer-reviewer.md
├── nw-documentarist-reviewer.md
├── nw-platform-architect-reviewer.md
├── nw-product-discoverer-reviewer.md
├── nw-product-owner-reviewer.md
├── nw-researcher-reviewer.md
├── nw-software-crafter-reviewer.md
├── nw-solution-architect-reviewer.md
└── nw-troubleshooter-reviewer.md
```

---

## Review Feedback Format

Reviewers output structured YAML feedback:

```yaml
review_id: "rev_{timestamp}_{artifact_name}"
reviewer: "product-owner-reviewer"
artifact: "docs/feature/{feature-name}/discuss/requirements.md"

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

**Last Updated**: 2026-02-13
**Type**: Reference
**Purity**: 98%+
