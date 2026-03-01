# How to Invoke Reviewer Agents

**Version**: 1.5.2
**Date**: 2026-01-22
**Status**: Production Ready

Step-by-step guide to requesting peer reviews from reviewer agents.

**Prerequisites**: Familiarity with Task tool and wave workflows.

**Related**: [Reviewer Agents Reference](../reference/agents/index.md)

---

## Quick Start

Request a review via the Task tool:

```
Use Task tool:
subagent_type: general-purpose
prompt: Read ~/.claude/agents/nw/nw-{reviewer-name}.md
        Review docs/feature/{feature-id}/{wave}/{artifact}.md
        Return YAML: strengths, issues, recommendations, approval_status
```

---

## Method 1: Task Tool Invocation

The primary method to invoke reviewers.

### Step 1: Identify Reviewer

Match your artifact type to the reviewer:

| Artifact Type | Reviewer to Use |
|--------------|-----------------|
| Requirements | product-owner-reviewer |
| Architecture | solution-architect-reviewer |
| Acceptance tests | acceptance-designer-reviewer |
| Implementation | software-crafter-reviewer |

### Step 2: Invoke via Task Tool

```markdown
<Task>
  subagent_type: general-purpose
  description: Invoke {reviewer-name}
  prompt: |
    You are the {reviewer-name} agent.

    Read the complete agent specification from:
    ~/.claude/agents/nw/nw-{reviewer-name}.md

    Review the artifact at:
    {path-to-artifact}

    Conduct peer review following the specification.
    Provide structured YAML feedback:
    - strengths
    - issues_identified (with severity)
    - recommendations
    - approval_status
</Task>
```

### Step 3: Interpret Feedback

The reviewer returns YAML:

```yaml
approval_status: "rejected_pending_revisions"
issues_identified:
  confirmation_bias:
    - issue: "Technology assumption without rationale"
      severity: "critical"
      recommendation: "Re-elicit constraints"
```

**Actions by status**:
- `approved` -> Proceed to handoff
- `rejected_pending_revisions` -> Address issues, resubmit
- `conditionally_approved` -> Proceed with documented caveats

---

## Method 2: Interactive Review

Request persona activation in the chat:

```
Read ~/.claude/agents/nw/nw-{reviewer-name}.md and activate as the {reviewer-name} agent.

Review the artifact at {path-to-artifact}

Provide conversational feedback on:
1. Completeness
2. Consistency
3. Quality issues
4. Approval recommendation
```

---

## Method 3: Add Review Steps to Workflows

Add review steps to wave workflows.

### After DISCUSS wave
```
1. Create requirements (product-owner)
2. Review requirements (product-owner-reviewer)  <- Add this step
3. Proceed to DESIGN
```

### After DISTILL wave
```
1. Create acceptance tests (acceptance-designer)
2. Review tests (acceptance-designer-reviewer)  <- Add this step
3. Proceed to DELIVER
```

---

## Revision Workflow

When reviewer returns `rejected_pending_revisions`:

### Step 1: Address Critical/High Issues

Focus on critical and high severity issues first:

```yaml
issues_identified:
  confirmation_bias:
    - issue: "AWS assumption without requirement"
      severity: "critical"  # <- Fix this first
```

### Step 2: Revise Artifact

Update your artifact to address the issues.

### Step 3: Resubmit for Review

```
The artifact has been revised. Please re-review:
{path-to-revised-artifact}

Issues addressed:
- Removed AWS assumption, added deployment constraints section
- Quantified performance requirements (2s p95)
```

### Step 4: Await Approval

The reviewer validates revisions and returns updated status.

**Iteration limit**: Maximum 2 iterations. If not approved after 2 iterations, escalate to human facilitator.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Reviewer not found | Use Task tool with full spec path: `Read ~/.claude/agents/nw/nw-{reviewer-name}.md` |
| No structured feedback | Explicitly request YAML with: `approval_status`, `issues_identified` (with severity), `recommendations` |
| Review too lengthy | Scope it: "Focus only on: 1) confirmation bias, 2) completeness gaps, 3) testability. Skip style/formatting." |

---

## Examples

### Example: Requirements Review

```markdown
I need peer review on my requirements document.

<Task>
  subagent_type: general-purpose
  description: Requirements peer review
  prompt: |
    You are the product-owner-reviewer persona.

    Read: ~/.claude/agents/nw/nw-product-owner-reviewer.md

    Review: docs/feature/{feature-id}/discuss/checkout-requirements.md

    Focus on:
    1. Confirmation bias (technology assumptions)
    2. Completeness (missing scenarios/stakeholders)
    3. Clarity (vague requirements)
    4. Testability (measurable acceptance criteria)

    Provide YAML feedback with approval_status.
</Task>
```

### Example: Acceptance Test Review

```markdown
Please review my acceptance tests for happy path bias.

<Task>
  subagent_type: general-purpose
  description: Acceptance test review
  prompt: |
    You are the acceptance-designer-reviewer persona.

    Read: ~/.claude/agents/nw/nw-acceptance-designer-reviewer.md

    Review: tests/acceptance/features/checkout.feature

    Focus on:
    1. Happy path bias (error scenario coverage)
    2. GWT format compliance
    3. Business language purity
    4. Coverage completeness

    Provide YAML feedback with approval_status.
</Task>
```

### Example: Architecture Review

```markdown
Review my architecture design for feasibility.

<Task>
  subagent_type: general-purpose
  description: Architecture peer review
  prompt: |
    You are the solution-architect-reviewer persona.

    Read: ~/.claude/agents/nw/nw-solution-architect-reviewer.md

    Review: docs/feature/{feature-id}/design/architecture-design.md

    Focus on:
    1. Architectural bias (premature technology choices)
    2. ADR quality (complete decision records)
    3. Feasibility (implementation viability)
    4. Testability (component boundaries)

    Provide YAML feedback with approval_status.
</Task>
```

---

## Verification Checklist

- [ ] Reviewer persona loaded correctly
- [ ] Artifact path correct
- [ ] YAML feedback received with all sections
- [ ] Approval status stated
- [ ] Critical/high issues have recommendations
- [ ] Tracked iteration count (max 2)
