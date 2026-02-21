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

Conversational wizard that asks the user to describe their feature, classifies it, recommends a starting wave, and launches it. Eliminates the need to understand the 6-wave pipeline before using nWave.

You (the main Claude instance) run this wizard directly. No subagent delegation for the wizard itself.

## Behavior Flow

### Step 1: Feature Description Intake

Ask the user to describe what they want to build in plain language. If they provided a description as an argument, use that.

If the description is vague (fewer than 3 meaningful words, or unclassifiable like "make things better"):
- Ask: **What system** is being changed?
- Ask: **What problem** are you solving?
- Ask: **Who benefits** from this change?
- Provide an example: "Add rate limiting to prevent API abuse"

Do NOT proceed until you have a clear, actionable description.

### Step 2: Project ID Derivation

Derive a kebab-case project ID from the description:

1. Strip common prefixes: "implement", "add", "create", "build"
2. Remove English stop words: "a", "the", "to", "for", "with", "and", "in", "on", "of"
3. Convert to kebab-case (lowercase, hyphens between words)
4. Limit to 5 hyphenated segments maximum

Examples:
- "Add rate limiting to the API gateway" → `rate-limiting-api-gateway`
- "OAuth2 upgrade" → `oauth2-upgrade`
- "Implement a real-time notification system with WebSocket support for mobile and desktop clients" → `real-time-notification-system-websocket`

Show the derived ID to the user using AskUserQuestion. Allow them to override it with a custom value.

### Step 3: Name Conflict Check

Check if `docs/feature/{project-id}/` already exists.

If it does, use AskUserQuestion to offer:
1. **Continue that project** — switch to `/nw:continue` for that project
2. **Start fresh with a different name** — ask for a distinguishing name
3. **Archive and restart** — move existing directory to `docs/feature/{project-id}-archived-{date}/`

### Step 4: Clarifying Questions

Use AskUserQuestion to ask:

**Question 1: New or existing behavior?**
- New functionality that doesn't exist yet
- Changing or improving existing functionality
- Fixing a bug or regression

**Question 2: Requirements readiness?**
- I have clear requirements in my head but nothing written down
- I have a rough idea but need to explore further
- I haven't validated whether this problem is worth solving yet

### Step 5: Feature Classification

Based on the description and answers, classify the feature type:
- **User-facing** — UI/UX functionality visible to end users
- **Backend** — APIs, services, data processing
- **Infrastructure** — DevOps, CI/CD, tooling
- **Cross-cutting** — Spans multiple layers (auth, logging, etc.)

Show the classification to the user for confirmation.

### Step 6: Greenfield vs Brownfield Detection

Scan the filesystem:
- Check if `src/` or equivalent source directory exists with code
- Check if `docs/feature/` has any prior feature directories
- Check for existing test directories

If no source code and no prior features → **greenfield**
If source code or prior features exist → **brownfield**

### Step 7: Wave Recommendation

Apply this decision tree:

```
IF "fixing a bug":
    → /nw:root-why ("Investigate the root cause first")

IF "haven't validated the problem":
    → /nw:discover ("Validate the problem space before building")

IF "rough idea, need to explore":
    → /nw:discuss ("Define requirements and acceptance criteria")

IF "clear requirements, nothing written":
    → /nw:discuss ("Formalize requirements into user stories")

IF existing DISCUSS artifacts found for this project:
    → /nw:design ("Requirements exist, design the architecture")

IF existing DESIGN artifacts found:
    → /nw:distill ("Architecture exists, create acceptance tests")

IF all prior waves complete:
    → /nw:deliver ("Ready for implementation")

DEFAULT:
    → /nw:discuss ("Start by defining what to build")
```

Show the recommendation with a clear rationale using AskUserQuestion. Include:
- The recommended wave command
- Why this wave (one sentence)
- What it will produce

### Step 8: Launch

After user confirms, create the project directory:

```bash
mkdir -p docs/feature/{project-id}
```

Then invoke the recommended wave command by reading its task file and following its instructions, passing the project ID as the argument.

## Error Handling

| Error | Response |
|-------|----------|
| Vague description (< 3 meaningful words) | Ask follow-up questions with example |
| Name conflict with existing project | Offer continue/rename/archive options |
| User cannot classify feature type | Default to "cross-cutting" and note uncertainty |
| No clear wave recommendation | Default to DISCUSS with explanation |

## Success Criteria

- [ ] User described feature in plain language
- [ ] Project ID derived and confirmed by user
- [ ] No name conflicts (or resolved)
- [ ] Feature classified by type
- [ ] Starting wave recommended with rationale
- [ ] User confirmed recommendation
- [ ] Wave command launched with correct project ID

## Examples

### Example 1: Greenfield backend feature
```
/nw:new "Add rate limiting to the API gateway"
```
Wizard derives `rate-limiting-api-gateway`, detects no prior artifacts (greenfield), asks clarifying questions. User says "new functionality, clear requirements." Wizard recommends DISCUSS wave, launches `/nw:discuss "rate-limiting-api-gateway"`.

### Example 2: Bug fix
```
/nw:new "Fix authentication timeout errors"
```
Wizard detects "fix" in description, asks clarifying questions. User confirms it's a bug. Wizard recommends `/nw:root-why "authentication timeout errors"`.

### Example 3: Unclear problem
```
/nw:new "Build a customer feedback system"
```
User says they haven't validated whether customers want this. Wizard recommends DISCOVER wave, launches `/nw:discover "customer-feedback-system"`.
