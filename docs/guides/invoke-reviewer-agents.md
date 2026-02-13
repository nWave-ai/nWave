# How to Invoke Reviewer Agents

**Version**: 1.5.2
**Date**: 2026-01-22
**Status**: Production Ready

Step-by-step guide to requesting peer reviews from Layer 4 reviewer agents.

**Prerequisites**: Familiarity with Task tool and wave workflows.

**Related Docs**:
- [Reviewer Agents Reference](../reference/reviewer-agents-reference.md) (lookup)
- [Layer 4 Implementation Summary](5-layer-testing-implementation.md) (concepts)

---

## Quick Start

Copy-paste this to request a review:

```
Use the Task tool to invoke the business-analyst-reviewer agent.
Read the specification from nWave/agents/business-analyst-reviewer.md
Review the artifact at docs/requirements/requirements.md
Provide YAML feedback with strengths, issues, recommendations, and approval_status.
```

---

## Method 1: Task Tool Invocation

The primary method to invoke reviewers.

### Step 1: Identify Reviewer

Match your artifact type to the reviewer:

| Artifact Type | Reviewer to Use |
|--------------|-----------------|
| Requirements | business-analyst-reviewer |
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
    nWave/agents/{reviewer-name}.md

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

## Method 2: Direct Agent Activation

For interactive review sessions.

### Step 1: Request Persona Activation

```
Read nWave/agents/acceptance-designer-reviewer.md and activate as the Sentinel persona.
```

### Step 2: Provide Artifact

```
Review the acceptance tests at tests/acceptance/features/checkout.feature
```

### Step 3: Receive Interactive Feedback

The agent adopts the reviewer persona and provides conversational feedback.

---

## Method 3: Workflow Integration

Add review steps to wave workflows.

### In DISCUSS Wave

After requirements gathering:

```
1. Create requirements (business-analyst)
2. REVIEW requirements (business-analyst-reviewer) <- Add this
3. Handoff to DESIGN wave
```

### In DISTILL Wave

After test creation:

```
1. Create acceptance tests (acceptance-designer)
2. REVIEW tests (acceptance-designer-reviewer) <- Add this
3. Handoff to DEVELOP wave
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

### Reviewer Not Found

**Symptom**: "Reviewer agent not found"

**Solution**: Use Task tool with explicit spec path:
```
Read nWave/agents/{reviewer-name}.md and adopt that persona
```

### No Feedback Returned

**Symptom**: Review completes but no structured feedback

**Solution**: Explicitly request YAML format:
```
Provide feedback in YAML format with:
- strengths
- issues_identified (include severity: critical/high/medium/low)
- recommendations
- approval_status (approved/rejected_pending_revisions/conditionally_approved)
```

### Review Takes Too Long

**Symptom**: Reviewer produces extensive analysis

**Solution**: Scope the review:
```
Focus only on:
1. Confirmation bias detection
2. Completeness gaps
3. Testability concerns

Skip: style, formatting, minor improvements
```

---

## Examples

### Example: Requirements Review

```markdown
I need peer review on my requirements document.

<Task>
  subagent_type: general-purpose
  description: Requirements peer review
  prompt: |
    You are the business-analyst-reviewer (Scout persona).

    Read: nWave/agents/business-analyst-reviewer.md

    Review: docs/requirements/checkout-requirements.md

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
    You are the acceptance-designer-reviewer (Sentinel persona).

    Read: nWave/agents/acceptance-designer-reviewer.md

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
    You are the solution-architect-reviewer (Atlas persona).

    Read: nWave/agents/solution-architect-reviewer.md

    Review: docs/architecture/system-architecture.md

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

After invoking a reviewer, verify:

- [ ] Reviewer persona adopted correctly
- [ ] Artifact path correct and accessible
- [ ] YAML feedback received with all sections
- [ ] Approval status clearly stated
- [ ] Critical/high issues have recommendations
- [ ] Iteration number tracked (max 2)

---

**Last Updated**: 2026-01-21
**Type**: How-to Guide
**Purity**: 95%+
