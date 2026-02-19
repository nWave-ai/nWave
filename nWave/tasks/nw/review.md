---
description: "Dispatches an expert reviewer agent to critique workflow artifacts. Use when a roadmap, implementation, or step needs quality review before proceeding."
argument-hint: '[agent] [artifact-type] [artifact-path] - Example: @software-crafter task "roadmap.yaml"'
---

# NW-REVIEW: Expert Critique and Quality Assurance

**Wave**: CROSS_WAVE
**Agent**: Dynamic (nw-*-reviewer)

## Overview

Dispatches an expert reviewer agent to critique workflow artifacts. Takes a base agent name, appends `-reviewer` to derive the reviewer agent, and invokes it with the artifact. The reviewer agent owns all review methodology, criteria, and output format.

## Review Philosophy: Radical Candor

Every review MUST embody Radical Candor -- kind AND clear, specific AND sincere:

- **Care personally**: Acknowledge what works. Understand the author's intent before critiquing. Include at least one genuine `praise:` comment per review.
- **Challenge directly**: Be specific about what is wrong and WHY. Ground feedback in evidence and consequences, not preference. Never soften a security or data-loss issue.
- **Avoid ruinous empathy**: Never "LGTM" when there are real issues. Hedging language ("maybe consider possibly...") on blocking concerns is a review failure.
- **Avoid obnoxious aggression**: Never "this is terrible" without a constructive alternative. Focus on the work, not the author. Explain the "why" behind every critique.

## Feedback Format: Conventional Comments

All review findings MUST use Conventional Comments labels:

| Label | Purpose | Blocking? |
|---|---|---|
| `praise:` | Highlight something done well (genuine, not filler) | No |
| `issue (blocking):` | Specific problem that must be resolved before proceeding | Yes |
| `issue (blocking, security):` | Security vulnerability -- maximum directness | Yes |
| `suggestion:` | Propose improvement with reasoning | Varies -- mark `(blocking)` or `(non-blocking)` |
| `nitpick (non-blocking):` | Trivial, preference-based | No |
| `question (non-blocking):` | Seek clarification before assuming | No |
| `thought (non-blocking):` | Share an idea sparked by the review | No |

Findings MUST be priority-ordered: blocking issues first, then suggestions, then nitpicks/praise.

## Approval Criteria

| Verdict | Criteria |
|---|---|
| **APPROVED** | No blocking issues. Non-blocking feedback is advisory. |
| **NEEDS_REVISION** | Blocking issues exist. Author must address before proceeding. Each blocking issue clearly enumerated. |
| **REJECTED** | Fundamental design problems requiring significant rework. Rare -- explain thoroughly and offer alternatives. |

## Syntax

```
/nw:review @{agent-name} {artifact-type} "{artifact-path}" [step_id={id}] [--dimensions=rpp] [--from=1] [--to=3]
```

**Parameters:**
- `@{agent-name}` - Base agent (e.g., `@nw-software-crafter`). The `-reviewer` suffix is appended automatically.
- `{artifact-type}` - One of: `baseline`, `roadmap`, `step`, `task`, `implementation`
- `{artifact-path}` - Path to the artifact file (resolved to absolute)
- `step_id={id}` - Required for step and implementation reviews
- `--dimensions=rpp` - Triggers RPP code smell scan alongside standard review (Dimension 4)
- `--from=N` - Start RPP level (default: 1). Requires `--dimensions=rpp`
- `--to=N` - End RPP level (default: 6). Requires `--dimensions=rpp`

## Agent Derivation

The reviewer agent name is derived by appending `-reviewer` to the base agent:

| User provides | Reviewer invoked |
|---|---|
| `@nw-software-crafter` | `nw-software-crafter-reviewer` |
| `@nw-solution-architect` | `nw-solution-architect-reviewer` |
| `@nw-platform-architect` | `nw-platform-architect-reviewer` |

All `-reviewer` agents use Haiku model for cost efficiency.

## Agent Invocation

Parse parameters, validate, then invoke via Task tool:

```
@{agent-name}-reviewer

Review {artifact-type}: {absolute-artifact-path} [step_id={id}]
```

The reviewer agent handles everything: reading the artifact, applying domain expertise, generating structured critique, and updating the original artifact file with review metadata.

## Validation (before invoking)

1. Base agent name exists (strip `@` prefix, check against agent registry)
2. Artifact type is valid (baseline, roadmap, step, task, implementation)
3. Artifact file exists at the resolved absolute path
4. step_id provided when artifact type is `step` or `implementation`

On validation failure, return a specific error message and stop.

## Success Criteria

- [ ] Reviewer agent invoked (not self-performed)
- [ ] Original artifact file updated with review metadata
- [ ] Review includes severity levels and approval status (APPROVED, NEEDS_REVISION, REJECTED)

## Examples

### Example 1: Step review
```
/nw:review @nw-software-crafter step "docs/feature/auth-upgrade/execution-log.yaml" step_id=02-01
```
Parses to: invoke `nw-software-crafter-reviewer` with step review of the execution log, step 02-01.

### Example 2: Roadmap review
```
/nw:review @nw-solution-architect roadmap "docs/feature/auth-upgrade/roadmap.yaml"
```
Parses to: invoke `nw-solution-architect-reviewer` with roadmap review.

### Example 3: Implementation review
```
/nw:review @nw-platform-architect implementation "docs/feature/auth-upgrade/execution-log.yaml" step_id=01-01
```
Parses to: invoke `nw-platform-architect-reviewer` with implementation review of step 01-01.

### Example 4: RPP code quality review
```
/nw:review @nw-software-crafter implementation "src/des/" --dimensions=rpp --from=1 --to=3
```
Parses to: invoke `nw-software-crafter-reviewer` with implementation review + RPP L1-L3 code smell detection using cascade rule.

## Error Messages

- Invalid agent: "Unknown agent: {name}. Check available agents with /nw:agents."
- Invalid type: "Invalid artifact type: {type}. Use: baseline, roadmap, step, task, implementation."
- Missing file: "Artifact not found: {path}."
- Missing step_id: "step_id required for {type} reviews."

## Next Wave

**Handoff To**: Depends on review outcome (rework or proceed to next workflow step)
**Deliverables**: Updated artifact file with embedded review metadata

## Expected Outputs

```
Updated artifact file (roadmap.yaml, execution-log.yaml, etc.) with reviews section
```
