---
description: "Detects current wave progress for a feature and resumes at the next step. Scans docs/feature/ for artifacts and shows a progress summary."
argument-hint: "[project-id] - Optional: omit to auto-detect from docs/feature/"
disable-model-invocation: true
---

# NW-CONTINUE: Resume a Feature

**Wave**: CROSS_WAVE (entry point)
**Agent**: Main Instance (self — wizard)
**Command**: `/nw:continue`

## Overview

Scans `docs/feature/` for active projects, detects which wave artifacts exist, displays a progress summary, and launches the next wave command. Eliminates manual artifact inspection when returning to a feature after hours or days away.

You (the main Claude instance) run this wizard directly. No subagent delegation for the wizard itself.

## Behavior Flow

### Step 1: Scan for Projects

If a project ID was provided as argument, use it directly.

Otherwise, scan `docs/feature/` for project directories:

```bash
ls -d docs/feature/*/
```

**If no directories found:**
Display: "No active projects found under `docs/feature/`."
Suggest: "Run `/nw:new` to start a new feature."
Stop here.

### Step 2: Project Selection (Multiple Projects)

If multiple project directories exist, list them ordered by most recent file modification:

For each project, find the most recently modified file:
```bash
find docs/feature/{project-id}/ -type f -printf '%T@ %p\n' | sort -rn | head -1
```

Present the list using AskUserQuestion:
- Show project name and last modified date
- Most recent first
- Ask user to select one

### Step 3: Wave Progress Detection

For the selected project, check each wave's artifacts:

| Wave | Complete When | In Progress When |
|------|--------------|-----------------|
| DISCOVER | `docs/discovery/problem-validation.md` AND `docs/discovery/lean-canvas.md` exist and are non-empty | `docs/discovery/` exists but required files missing or empty |
| DISCUSS | `docs/feature/{id}/discuss/requirements.md` AND `docs/feature/{id}/discuss/user-stories.md` exist and are non-empty | `docs/feature/{id}/discuss/` exists but required files missing or empty |
| DESIGN | `docs/feature/{id}/design/architecture-design.md` exists and is non-empty | `docs/feature/{id}/design/` exists but required file missing or empty |
| DEVOP | `docs/feature/{id}/deliver/platform-architecture.md` exists and is non-empty | `docs/feature/{id}/deliver/` exists but platform-architecture.md missing or empty |
| DISTILL | `docs/feature/{id}/distill/test-scenarios.md` exists and is non-empty | `docs/feature/{id}/distill/` exists but required file missing or empty |
| DELIVER | `docs/feature/{id}/execution-log.yaml` with all roadmap steps at COMMIT/PASS | `execution-log.yaml` exists with some steps incomplete |

"Not started" = neither directory nor required artifacts exist for that wave.

### Step 4: Anomaly Detection

Check for these issues before showing progress:

**Empty/corrupted artifacts:** For each "complete" artifact, verify file size > 0 bytes. If a key artifact is empty, flag it:
- "Warning: `requirements.md` exists but is empty (0 bytes). Recommend re-running DISCUSS wave."

**Non-adjacent waves (skipped waves):** If artifacts exist for non-consecutive waves (e.g., DISCUSS complete + DELIVER in progress, but no DESIGN or DISTILL), warn:
- "Warning: DESIGN and DISTILL waves were skipped. Options:"
  1. Fill the gap — start from DESIGN
  2. Continue DELIVER as-is
  3. Show all artifacts for manual review

### Step 5: DELIVER Progress Detail

If DELIVER is in progress, show step-level detail:

Read `docs/feature/{id}/execution-log.yaml`:
- Count steps with status COMMIT/PASS (completed)
- Find the first step without COMMIT/PASS (next step)

Read `.develop-progress.json` if it exists:
- Check for last failure point

Display: "DELIVER in progress: Steps 01-01 through 02-01 complete. Next: 02-02"

### Step 6: Progress Display

Show a per-wave summary:

```
Feature: {project-id}

  DISCOVER   ○ not started
  DISCUSS    ● complete
  DESIGN     ● complete
  DISTILL    ◐ in progress
  DELIVER    ○ not started

  Next: DISTILL — Create acceptance tests
```

Use ● for complete, ◐ for in progress, ○ for not started.

### Step 7: Recommendation and Launch

Recommend the next wave:
- If a wave is "in progress", recommend resuming it
- If the last complete wave has a clear successor, recommend that successor
- Show the recommendation with AskUserQuestion for confirmation

After confirmation, invoke the recommended wave command by reading its task file and following its instructions, passing the project ID as the argument.

## Error Handling

| Error | Response |
|-------|----------|
| No `docs/feature/` directory | Suggest `/nw:new` |
| Empty project directory (no artifacts at all) | Suggest `/nw:new` or re-running from DISCUSS |
| Corrupted artifact (0 bytes) | Flag file, recommend re-running that wave |
| Skipped waves (non-adjacent artifacts) | Warn, offer gap-fill or continue options |
| Cannot parse execution-log.yaml | Show raw file status, suggest manual review |

## Success Criteria

- [ ] Projects scanned from `docs/feature/`
- [ ] Project selected (auto or user choice)
- [ ] Wave progress detected accurately from artifact presence
- [ ] Anomalies flagged (empty files, skipped waves)
- [ ] DELIVER step-level progress shown when applicable
- [ ] Progress summary displayed
- [ ] Next wave recommended with rationale
- [ ] Wave command launched after user confirmation

## Examples

### Example 1: Single project, resume at DESIGN
```
/nw:continue
```
Wizard finds one project: `notification-service`. DISCUSS artifacts exist (complete), no DESIGN artifacts. Shows progress, recommends DESIGN. User confirms, wizard launches `/nw:design notification-service`.

### Example 2: DELIVER resume
```
/nw:continue rate-limiting
```
Wizard checks `rate-limiting` project. All waves through DISTILL complete, DELIVER in progress (steps 01-01 through 02-01 done). Shows "Next: step 02-02", launches `/nw:deliver "rate-limiting"`.

### Example 3: Multiple projects
```
/nw:continue
```
Wizard finds `rate-limiting` (modified today) and `user-notifications` (modified 3 days ago). Lists them, user picks `rate-limiting`. Wizard shows progress and recommends next wave.

### Example 4: No projects
```
/nw:continue
```
Wizard finds no `docs/feature/` directories. Shows "No active projects found" and suggests `/nw:new`.
