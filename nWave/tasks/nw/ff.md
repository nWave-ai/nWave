---
description: "Fast-forwards through remaining waves end-to-end without stopping for review between waves. Use when scope is clear and you want to move fast."
argument-hint: '[feature-description] - Optional: --from=[discuss|design|devops|distill|deliver]'
disable-model-invocation: true
---

# NW-FF: Fast-Forward

**Wave**: CROSS_WAVE (entry point)
**Agent**: Main Instance (self — orchestrator)
**Command**: `/nw:ff`

## Overview

Chains remaining waves end-to-end after a single user confirmation. Detects current progress (like `/nw:continue`), shows the planned sequence, and runs each wave automatically — DISCUSS → DESIGN → DEVOPS → DISTILL → DELIVER — without stopping for review between waves.

You (the main Claude instance) run this orchestration directly. Each wave is invoked by reading its task file and following its instructions.

**DISCOVER is skipped by default.** DISCOVER requires interactive customer interview data that cannot be auto-generated. To include DISCOVER, use `--from=discover` explicitly.

## Behavior Flow

### Step 1: Input Parsing

Accept either:
- A feature description (new project): `/nw:ff "Add rate limiting"`
- A `--from` flag with optional project ID: `/nw:ff --from=distill rate-limiting`
- No arguments (auto-detect from `docs/feature/`)

### Step 2: Project Resolution

**If a feature description is provided (new project):**

Derive project ID using the same rules as `/nw:new`:
1. Strip prefixes: "implement", "add", "create", "build"
2. Remove stop words: "a", "the", "to", "for", "with", "and", "in", "on", "of"
3. Kebab-case, max 5 segments

Show derived ID, allow override via AskUserQuestion.
Create `docs/feature/{project-id}/` directory.

**If no description (existing project):**

Scan `docs/feature/` for projects (same as `/nw:continue` Step 1-2).
If multiple, ask user to select.

### Step 3: Detect Current Progress

Check wave artifacts using the same detection rules as `/nw:continue`:

| Wave | Complete When | In Progress When |
|------|--------------|-----------------|
| DISCOVER | `docs/discovery/problem-validation.md` AND `docs/discovery/lean-canvas.md` exist and are non-empty | `docs/discovery/` exists but required files missing or empty |
| DISCUSS | `docs/feature/{id}/discuss/requirements.md` AND `docs/feature/{id}/discuss/user-stories.md` exist and are non-empty | `docs/feature/{id}/discuss/` exists but required files missing or empty |
| DESIGN | `docs/feature/{id}/design/architecture-design.md` exists and is non-empty | `docs/feature/{id}/design/` exists but required file missing or empty |
| DEVOP | `docs/feature/{id}/deliver/platform-architecture.md` exists and is non-empty | `docs/feature/{id}/deliver/` exists but platform-architecture.md missing or empty |
| DISTILL | `docs/feature/{id}/distill/test-scenarios.md` exists and is non-empty | `docs/feature/{id}/distill/` exists but required file missing or empty |
| DELIVER | `docs/feature/{id}/execution-log.yaml` with all roadmap steps at COMMIT/PASS | `execution-log.yaml` exists with some steps incomplete |

### Step 4: Determine Wave Sequence

Default wave order (DISCOVER skipped):
```
DISCUSS → DESIGN → DEVOPS → DISTILL → DELIVER
```

**If `--from` flag provided:**
- Validate that all prerequisite wave artifacts exist
- If prerequisites missing, list them and refuse to proceed:
  "Cannot start from DISTILL — DESIGN artifacts are missing. Run `/nw:continue` to fill the gap."
- Start the sequence from the specified wave

**If no `--from` flag:**
- Find the first incomplete wave in the sequence
- Start from there

### Step 5: Show Plan and Confirm

Display the planned sequence:

```
Feature: {project-id}

  Fast-forward plan:
    1. DISCUSS  — Define requirements and user stories
    2. DESIGN   — Architecture and technology selection
    3. DEVOPS   — Platform and infrastructure readiness
    4. DISTILL  — Acceptance tests (Given-When-Then)
    5. DELIVER  — TDD implementation

  This will run all 5 waves without stopping for review.
```

If some waves are already complete, show them as skipped:

```
  Fast-forward plan:
    ✓ DISCUSS  — complete
    ✓ DESIGN   — complete
    1. DEVOPS   — Platform and infrastructure readiness
    2. DISTILL  — Acceptance tests (Given-When-Then)
    3. DELIVER  — TDD implementation

  3 waves will execute without stopping.
```

Use AskUserQuestion for one-time confirmation before starting.

### Step 6: Sequential Execution

For each wave in the sequence:

1. Read the wave's task file (`nWave/tasks/nw/{wave}.md`)
2. Follow its instructions — invoke the appropriate agent via Task tool as the task file directs
3. Wait for the wave to complete
4. Verify output artifacts exist (check the wave detection rules from Step 3)
5. If artifacts are missing after the wave completes, treat as a failure
6. Proceed to the next wave

Between waves, show a brief status:
```
✓ DISCUSS complete — requirements.md, user-stories.md created
  Starting DESIGN...
```

### Step 7: Failure Handling

If any wave fails mid-pipeline:

1. **Stop immediately** — do not proceed to the next wave
2. Show the error clearly:
   ```
   ✗ DESIGN failed
     Error: [error details]

     Progress saved. Run /nw:continue to resume from DESIGN.
   ```
3. Suggest `/nw:continue` for manual resume after fixing the issue
4. Do NOT retry automatically — the user needs to understand what went wrong

### Step 8: Completion

When all waves complete:

```
✓ Fast-forward complete for {project-id}

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
| No feature description and no existing projects | Suggest `/nw:new` |
| `--from` wave has missing prerequisites | List missing artifacts, refuse to proceed |
| Wave failure mid-pipeline | Stop, show error, suggest `/nw:continue` |
| Artifact verification fails after wave completion | Treat as wave failure |
| Name conflict on new project | Same as `/nw:new` conflict handling |

## Success Criteria

- [ ] Project resolved (new or existing)
- [ ] Current progress detected accurately
- [ ] Planned wave sequence shown to user
- [ ] User confirmed one-time before execution
- [ ] Each wave executed in sequence
- [ ] Output artifacts verified between waves
- [ ] Failure stops pipeline with clear error and `/nw:continue` suggestion
- [ ] Completion summary shown

## Examples

### Example 1: Full fast-forward from scratch
```
/nw:ff "Upgrade authentication to OAuth2"
```
Wizard derives `oauth2-upgrade`, detects no prior artifacts, shows plan: DISCUSS → DESIGN → DEVOPS → DISTILL → DELIVER. User confirms. All 5 waves execute in sequence.

### Example 2: Fast-forward from mid-pipeline
```
/nw:ff
```
Wizard finds `notification-service` with DISCUSS complete. Shows plan: DESIGN → DEVOPS → DISTILL → DELIVER. User confirms. 4 waves execute.

### Example 3: Fast-forward with --from flag
```
/nw:ff --from=distill rate-limiting
```
Wizard validates DESIGN artifacts exist for `rate-limiting`. Shows plan: DISTILL → DELIVER. User confirms. 2 waves execute.

### Example 4: Fast-forward with failure
```
/nw:ff "Add payment processing"
```
DISCUSS succeeds, DESIGN succeeds, DEVOPS fails. Pipeline stops. Shows error and suggests `/nw:continue` to resume from DEVOPS.
