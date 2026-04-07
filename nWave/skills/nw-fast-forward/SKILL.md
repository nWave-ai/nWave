---
name: nw-fast-forward
description: "Fast-forwards through remaining waves end-to-end without stopping for review between waves."
user-invocable: false
argument-hint: '[feature-description] - Optional: --from=[discuss|design|devops|distill|deliver]'
---

# NW-FAST-FORWARD: Fast-Forward

**Wave**: CROSS_WAVE (entry point) | **Agent**: Main Instance (self — orchestrator) | **Command**: `/nw-fast-forward`

## Overview

Chains remaining waves end-to-end after single user confirmation. Detects current progress (like `/nw-continue`), shows planned sequence, runs each wave automatically — DISCUSS > DESIGN > DEVOPS > DISTILL > DELIVER — without stopping between waves.

You (main Claude instance) run this orchestration directly. Each wave invoked by reading its task file.

**DISCOVER skipped by default** — requires interactive customer interview data that cannot be auto-generated. Use `--from=discover` to include.

## Behavior Flow

### Step 1: Input Parsing

Accept: feature description (new project)|`--from` flag with optional feature ID|no arguments (auto-detect from `docs/feature/`)

### Step 2: Project Resolution

**New project (description provided):** Derive feature ID per `~/.claude/nWave/skills/common/wizard-shared-rules.md` (Feature ID Derivation). Show derived ID, allow override via AskUserQuestion. Create `docs/feature/{feature-id}/`.

**Existing project (no description):** Scan `docs/feature/` (same as `/nw-continue` Step 1-2). If multiple, ask user to select.

### Step 3: Detect Current Progress

Check wave artifacts using Wave Detection Rules in `~/.claude/nWave/skills/common/wizard-shared-rules.md`.

### Step 4: Determine Wave Sequence

Default order (DISCOVER skipped): DISCUSS > DESIGN > DEVOPS > DISTILL > DELIVER

**With `--from` flag:** Validate prerequisite artifacts exist. If missing: "Cannot start from {wave} — {missing} artifacts missing. Run `/nw-continue` to fill the gap." Start from specified wave.

**Without `--from`:** Find first incomplete wave, start from there.

### Step 5: Show Plan and Confirm

```
Feature: {feature-id}

  Fast-forward plan:
    1. DISCUSS  — Define requirements and user stories
    2. DESIGN   — Architecture and technology selection
    3. DEVOPS   — Platform and infrastructure readiness
    4. DISTILL  — Acceptance tests (Given-When-Then)
    5. DELIVER  — TDD implementation

  This will run all 5 waves without stopping for review.
```

If some waves complete, show as skipped:
```
  Fast-forward plan:
    ✓ DISCUSS  — complete
    ✓ DESIGN   — complete
    1. DEVOPS   — Platform and infrastructure readiness
    2. DISTILL  — Acceptance tests (Given-When-Then)
    3. DELIVER  — TDD implementation

  3 waves will execute without stopping.
```

One-time confirmation via AskUserQuestion.

### Step 6: Sequential Execution

For each wave:
1. Read task file (`nWave/tasks/nw/{wave}.md`)
2. Follow instructions — invoke appropriate agent via Task tool
3. Wait for completion
4. Verify output artifacts exist (wave detection rules)
5. Missing artifacts after wave = failure
6. Proceed to next wave

Between waves show brief status:
```
✓ DISCUSS complete — user-stories.md, story-map.md created
  Starting DESIGN...
```

### Step 7: Failure Handling

If any wave fails:
1. **Stop immediately** — do not proceed
2. Show error:
   ```
   ✗ {WAVE} failed
     Error: [details]
     Progress saved. Run /nw-continue to resume from {WAVE}.
   ```
3. Suggest `/nw-continue` for manual resume
4. Do NOT retry automatically

### Step 8: Completion

```
✓ Fast-forward complete for {feature-id}

  DISCUSS   ● complete
  DESIGN    ● complete
  DEVOPS    ● complete
  DISTILL   ● complete
  DELIVER   ● complete

  All acceptance tests pass. Feature is ready.
```

## Error Handling

| Error | Response |
|-------|----------|
| No description and no existing projects | Suggest `/nw-new` |
| `--from` with missing prerequisites | List missing artifacts, refuse |
| Wave failure mid-pipeline | Stop, show error, suggest `/nw-continue` |
| Artifact verification fails after wave | Treat as wave failure |
| Name conflict on new project | Same as `/nw-new` conflict handling |

## Success Criteria

- [ ] Project resolved (new or existing)
- [ ] Current progress detected accurately
- [ ] Planned wave sequence shown to user
- [ ] User confirmed one-time before execution
- [ ] Each wave executed in sequence
- [ ] Output artifacts verified between waves
- [ ] Failure stops pipeline with clear error and `/nw-continue` suggestion
- [ ] Completion summary shown

## Examples

### Example 1: Full fast-forward from scratch
```
/nw-fast-forward "Upgrade authentication to OAuth2"
```
Wizard derives `oauth2-upgrade`, detects no prior artifacts, shows plan: DISCUSS > DESIGN > DEVOPS > DISTILL > DELIVER. User confirms. All 5 waves execute in sequence.

### Example 2: Fast-forward from mid-pipeline
```
/nw-fast-forward
```
Wizard finds `notification-service` with DISCUSS complete. Shows plan: DESIGN > DEVOPS > DISTILL > DELIVER. User confirms. 4 waves execute.

### Example 3: Fast-forward with --from flag
```
/nw-fast-forward --from=distill rate-limiting
```
Wizard validates DESIGN artifacts exist for `rate-limiting`. Shows plan: DISTILL > DELIVER. User confirms. 2 waves execute.

### Example 4: Fast-forward with failure
```
/nw-fast-forward "Add payment processing"
```
DISCUSS succeeds, DESIGN succeeds, DEVOPS fails. Pipeline stops. Shows error and suggests `/nw-continue` to resume from DEVOPS.
