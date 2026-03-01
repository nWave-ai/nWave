---
description: "Guided wizard to start a new feature. Asks what you want to build, recommends the right starting wave, and launches it."
argument-hint: '[feature-description] - Example: "Add rate limiting to the API gateway"'
disable-model-invocation: true
---

# NW-NEW: Start a New Feature

**Wave**: CROSS_WAVE (entry point)
**Agent**: Main Instance (self — wizard)
**Command**: `/nw:new`

## Overview

Conversational wizard that asks the user to describe their feature|classifies it|recommends a starting wave|launches it. Eliminates need to understand the 6-wave pipeline before using nWave.

You (the main Claude instance) run this wizard directly. No subagent delegation.

## Behavior Flow

### Step 1: Feature Description Intake

Ask the user to describe what they want to build. If provided as argument, use that.

If vague (fewer than 3 meaningful words or unclassifiable):
- Ask: **What system** is being changed?
- Ask: **What problem** are you solving?
- Ask: **Who benefits** from this change?
- Provide example: "Add rate limiting to prevent API abuse"

Do NOT proceed until you have a clear, actionable description.

### Step 2: Feature ID Derivation

Derive feature ID per rules in `~/.claude/nWave/data/wizard-shared-rules.md` (section: Feature ID Derivation).

Examples: "Add rate limiting to the API gateway" -> `rate-limiting-api-gateway` | "OAuth2 upgrade" -> `oauth2-upgrade` | "Implement a real-time notification system with WebSocket support for mobile and desktop clients" -> `real-time-notification-system-websocket`

Show derived ID via AskUserQuestion. Allow override with custom value.

### Step 3: Name Conflict Check

Check if `docs/feature/{feature-id}/` exists. If so, offer via AskUserQuestion:
1. **Continue that project** — switch to `/nw:continue`
2. **Start fresh with different name** — ask for distinguishing name
3. **Archive and restart** — move to `docs/feature/{feature-id}-archived-{date}/`

### Step 4: Clarifying Questions

Use AskUserQuestion:

**Q1: New or existing behavior?**
- New functionality that doesn't exist yet
- Changing/improving existing functionality
- Fixing a bug or regression

**Q2: Requirements readiness?**
- Clear requirements in my head but nothing written
- Rough idea, need to explore further
- Haven't validated whether problem is worth solving

### Step 5: Feature Classification

Based on description and answers, classify:
- **User-facing** — UI/UX visible to end users
- **Backend** — APIs, services, data processing
- **Infrastructure** — DevOps, CI/CD, tooling
- **Cross-cutting** — Spans multiple layers (auth, logging, etc.)

Show classification for user confirmation.

### Step 6: Greenfield vs Brownfield Detection

Scan filesystem:
- Check if `src/` or equivalent has code
- Check if `docs/feature/` has prior feature directories
- Check for existing test directories

No source code and no prior features -> **greenfield** | Otherwise -> **brownfield**

### Step 7: Wave Recommendation

Decision tree:
```
IF "fixing a bug":
    -> /nw:root-why ("Investigate the root cause first")
IF "haven't validated the problem":
    -> /nw:discover ("Validate the problem space before building")
IF "rough idea, need to explore":
    -> /nw:discuss ("Define requirements and acceptance criteria")
IF "clear requirements, nothing written":
    -> /nw:discuss ("Formalize requirements into user stories")
IF existing DISCUSS artifacts found:
    -> /nw:design ("Requirements exist, design the architecture")
IF existing DESIGN artifacts found:
    -> /nw:distill ("Architecture exists, create acceptance tests")
IF all prior waves complete:
    -> /nw:deliver ("Ready for implementation")
DEFAULT:
    -> /nw:discuss ("Start by defining what to build")
```

Show recommendation with rationale via AskUserQuestion: recommended wave command|why this wave (one sentence)|what it produces.

### Step 8: Launch

After user confirms, create project directory:
```bash
mkdir -p docs/feature/{feature-id}
```

Invoke recommended wave command by reading its task file and following instructions, passing feature ID as argument.

## Error Handling

| Error | Response |
|-------|----------|
| Vague description (< 3 meaningful words) | Ask follow-up questions with example |
| Name conflict with existing project | Offer continue/rename/archive options |
| User cannot classify feature type | Default to "cross-cutting", note uncertainty |
| No clear wave recommendation | Default to DISCUSS with explanation |

## Success Criteria

- [ ] User described feature in plain language
- [ ] Project ID derived and confirmed by user
- [ ] No name conflicts (or resolved)
- [ ] Feature classified by type
- [ ] Starting wave recommended with rationale
- [ ] User confirmed recommendation
- [ ] Wave command launched with correct feature ID

## Examples

### Example 1: Greenfield backend feature
```
/nw:new "Add rate limiting to the API gateway"
```
Derives `rate-limiting-api-gateway`, detects no prior artifacts (greenfield), asks clarifying questions. User says "new functionality, clear requirements." Recommends DISCUSS, launches `/nw:discuss "rate-limiting-api-gateway"`.

### Example 2: Bug fix
```
/nw:new "Fix authentication timeout errors"
```
Detects "fix" in description. User confirms bug. Recommends `/nw:root-why "authentication timeout errors"`.

### Example 3: Unclear problem
```
/nw:new "Build a customer feedback system"
```
User says they haven't validated whether customers want this. Recommends DISCOVER, launches `/nw:discover "customer-feedback-system"`.
