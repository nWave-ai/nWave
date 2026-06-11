---
name: nw-review
description: "Dispatches an expert reviewer agent to critique workflow artifacts. Use when a roadmap, implementation, or step needs quality review before proceeding."
user-invocable: true
argument-hint: '[agent] [artifact-type] [artifact-path] - Example: @software-crafter task "roadmap.json"'
---

# NW-REVIEW: Expert Critique and Quality Assurance

**Wave**: CROSS_WAVE
**Agent**: Dynamic (nw-*-reviewer)

## Overview

Dispatches expert reviewer agent to critique workflow artifacts. Takes base agent name, appends `-reviewer`, invokes with artifact. Reviewer agent owns all review methodology|criteria|output format.

## Review Philosophy: Radical Candor

Every review MUST embody Radical Candor — kind AND clear, specific AND sincere:

- **Care personally**: Acknowledge what works. Understand author's intent before critiquing. Include at least one genuine `praise:` per review.
- **Challenge directly**: Be specific about what is wrong and WHY. Ground feedback in evidence|consequences, not preference. Never soften security/data-loss issues.
- **Avoid ruinous empathy**: Never "LGTM" when real issues exist. Hedging ("maybe consider possibly...") on blocking concerns is a review failure.
- **Avoid obnoxious aggression**: Never "this is terrible" without constructive alternative. Focus on work, not author. Explain "why" behind every critique.

## Feedback Format: Conventional Comments

All findings MUST use Conventional Comments labels:

| Label | Purpose | Blocking? |
|---|---|---|
| `praise:` | Highlight something done well (genuine, not filler) | No |
| `issue (blocking):` | Must be resolved before proceeding | Yes |
| `issue (blocking, security):` | Security vulnerability — maximum directness | Yes |
| `suggestion:` | Propose improvement with reasoning | Mark `(blocking)` or `(non-blocking)` |
| `nitpick (non-blocking):` | Trivial, preference-based | No |
| `question (non-blocking):` | Seek clarification before assuming | No |
| `thought (non-blocking):` | Idea sparked by the review | No |

Findings MUST be priority-ordered: blocking issues first, then suggestions, then nitpicks/praise.

## Approval Criteria

| Verdict | Criteria |
|---|---|
| **APPROVED** | No blocking issues. Non-blocking feedback is advisory. |
| **NEEDS_REVISION** | Blocking issues exist. Author must address. Each blocking issue enumerated. |
| **REJECTED** | Fundamental design problems requiring significant rework. Rare — explain thoroughly, offer alternatives. |

## Syntax

```
/nw-review @{agent-name} {artifact-type} "{artifact-path}" [step_id={id}] [--dimensions=rpp] [--from=1] [--to=3]
```

**Parameters:**
- `@{agent-name}` - Base agent (e.g., `@nw-software-crafter`). `-reviewer` suffix appended automatically.
- `{artifact-type}` - One of: `baseline`, `roadmap`, `step`, `task`, `implementation`
- `{artifact-path}` - Path to artifact file (resolved to absolute)
- `step_id={id}` - Required for step and implementation reviews
- `--dimensions=rpp` - Triggers RPP code smell scan alongside standard review (Dimension 4)
- `--from=N` / `--to=N` - RPP level range (default: 1-6). Requires `--dimensions=rpp`

## Rigor Profile Integration

Before dispatching the reviewer agent, read rigor config from `.nwave/des-config.json` (key: `rigor`). If absent, use standard defaults.

- **`review_enabled`**: If `false`, skip the review entirely. Output: "Review skipped per rigor profile (review_enabled=false)."
- **`reviewer_model`**: Pass as `model` parameter to Task tool. If `"skip"`, skip the review. Overrides the default Haiku model.
- **`double_review`**: If `true` and called from deliver Phase 4, the caller is responsible for invoking review twice.

## Agent Derivation

| User provides | Reviewer invoked |
|---|---|
| `@nw-software-crafter` | `nw-software-crafter-reviewer` |
| `@nw-solution-architect` | `nw-solution-architect-reviewer` |
| `@nw-platform-architect` | `nw-platform-architect-reviewer` |

Default model: Haiku (overridden by `rigor.reviewer_model` when set).

## Agent Invocation

1. **Parse parameters** — Strip `@` from agent name, resolve artifact path to absolute, extract optional step_id, dimensions, from/to range. Gate: all parameters parsed.
2. **Read rigor config** — Read `.nwave/des-config.json` key `rigor`. If absent, use standard defaults. Gate: rigor profile loaded or defaults applied.
3. **Validate inputs** — Run all four validation checks below. Gate: zero validation failures.
4. **Apply rigor overrides** — Check `review_enabled` (skip if false), determine model from `reviewer_model` (default: haiku, skip if "skip"). Gate: execution decision made.
5. **Invoke reviewer** — Call Task tool with `subagent_type="{agent-name}-reviewer"`, resolved model, and prompt `"Review {artifact-type}: {absolute-artifact-path} [step_id={id}]"`. Reviewer handles reading artifact, applying domain expertise, generating structured critique, updating original artifact with review metadata. Gate: Task tool invoked.

## Validation (before invoking)

1. **Agent exists** — Strip `@`, check agent name against agent registry. Gate: agent found or return "Unknown agent: {name}. Check available agents with /nw-agents."
2. **Artifact type valid** — Confirm type is one of: baseline, roadmap, step, task, implementation. Gate: type valid or return "Invalid artifact type: {type}. Use: baseline, roadmap, step, task, implementation."
3. **Artifact file exists** — Resolve to absolute path and confirm file exists. Gate: file found or return "Artifact not found: {path}."
4. **step_id present when required** — Require step_id when artifact type is `step` or `implementation`. Gate: step_id provided or return "step_id required for {type} reviews."

## Success Criteria

- [ ] Reviewer agent invoked (not self-performed)
- [ ] Original artifact file updated with review metadata
- [ ] Review includes severity levels and approval status (APPROVED, NEEDS_REVISION, REJECTED)

## Examples

### Example 1: Step review
```
/nw-review @nw-software-crafter step "docs/feature/auth-upgrade/execution-log.json" step_id=02-01
```
Invokes `nw-software-crafter-reviewer` with step review of execution log, step 02-01.

### Example 2: Roadmap review
```
/nw-review @nw-solution-architect roadmap "docs/feature/auth-upgrade/roadmap.json"
```
Invokes `nw-solution-architect-reviewer` with roadmap review.

### Example 3: Implementation review
```
/nw-review @nw-platform-architect implementation "docs/feature/auth-upgrade/execution-log.json" step_id=01-01
```
Invokes `nw-platform-architect-reviewer` with implementation review of step 01-01.

### Example 4: RPP code quality review
```
/nw-review @nw-software-crafter implementation "src/des/" --dimensions=rpp --from=1 --to=3
```
Invokes `nw-software-crafter-reviewer` with implementation review + RPP L1-L3 code smell detection using cascade rule.

## Error Messages

- Invalid agent: "Unknown agent: {name}. Check available agents with /nw-agents."
- Invalid type: "Invalid artifact type: {type}. Use: baseline, roadmap, step, task, implementation."
- Missing file: "Artifact not found: {path}."
- Missing step_id: "step_id required for {type} reviews."

## Next Wave

**Handoff To**: Depends on review outcome (rework or proceed)
**Deliverables**: Updated artifact file with embedded review metadata

## Expected Outputs

```
Updated artifact file (roadmap.json, execution-log.json, etc.) with reviews section
```
