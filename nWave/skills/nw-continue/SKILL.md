---
name: nw-continue
description: "Detects current wave progress for a feature and resumes at the next step. Scans docs/feature/ for artifacts."
user-invocable: false
argument-hint: '[feature-id] - Optional: omit to auto-detect from docs/feature/'
---

# NW-CONTINUE: Resume a Feature

**Wave**: CROSS_WAVE (entry point) | **Agent**: Main Instance (self — wizard) | **Command**: `/nw-continue`

## Overview

Scans `docs/feature/` for active projects, detects wave artifacts, displays progress summary, launches next wave command. Eliminates manual artifact inspection when returning after hours/days.

You (main Claude instance) run this wizard directly. No subagent delegation.

## Behavior Flow

### Step 1: Scan for Projects

If project ID provided as argument, use it directly.

Otherwise scan `docs/feature/` for project directories:
```bash
ls -d docs/feature/*/
```

**No directories found:** Display "No active projects found under `docs/feature/`." Suggest `/nw-new`. Stop.

### Step 2: Project Selection (Multiple Projects)

If multiple directories exist, list by most recent file modification:
```bash
find docs/feature/{feature-id}/ -type f -printf '%T@ %p\n' | sort -rn | head -1
```

Present via AskUserQuestion: project name|last modified date|most recent first. Ask user to select.

### Step 3: Wave Progress Detection

Check each wave's artifacts using Wave Detection Rules in `~/.claude/nWave/skills/common/wizard-shared-rules.md`.

### Step 4: Anomaly Detection

Check before showing progress:

**Empty/corrupted artifacts:** Verify file size > 0 for each "complete" artifact. If empty, flag: "Warning: `user-stories.md` exists but is empty (0 bytes). Recommend re-running DISCUSS wave."

**Non-adjacent waves (skipped):** If artifacts exist for non-consecutive waves (e.g., DISCUSS + DELIVER but no DESIGN/DISTILL), warn with options:
1. Fill the gap — start from missing wave
2. Continue as-is
3. Show all artifacts for manual review

### Step 5: DELIVER Progress Detail

If DELIVER in progress, show step-level detail:
- Read `docs/feature/{id}/deliver/execution-log.json`: count COMMIT/PASS steps, find first without COMMIT/PASS
- Read `.develop-progress.json` if exists: check last failure point
- Display: "DELIVER in progress: Steps 01-01 through 02-01 complete. Next: 02-02"

### Step 6: Progress Display

```
Feature: {feature-id}

  DISCOVER   ○ not started
  DISCUSS    ● complete
  DESIGN     ● complete
  DISTILL    ◐ in progress
  DELIVER    ○ not started

  Next: DISTILL — Create acceptance tests
```

Symbols: ● complete | ◐ in progress | ○ not started

### Step 7: Recommendation and Launch

Recommend next wave: resume in-progress wave|successor of last complete wave. Show via AskUserQuestion for confirmation. After confirmation, invoke recommended wave command by reading its task file, passing project ID as argument.

## Error Handling

| Error | Response |
|-------|----------|
| No `docs/feature/` directory | Suggest `/nw-new` |
| Empty project directory | Suggest `/nw-new` or re-run from DISCUSS |
| Corrupted artifact (0 bytes) | Flag file, recommend re-running that wave |
| Skipped waves | Warn, offer gap-fill or continue options |
| Cannot parse execution-log.json | Show raw file status, suggest manual review |

## Success Criteria

- [ ] Projects scanned from `docs/feature/`
- [ ] Project selected (auto or user choice)
- [ ] Wave progress detected accurately from artifact presence
- [ ] Anomalies flagged (empty files, skipped waves)
- [ ] DELIVER step-level progress shown when applicable
- [ ] Progress summary displayed
- [ ] Next wave recommended and launched after user confirmation

## Examples

### Example 1: Single project, resume at DESIGN
```
/nw-continue
```
Wizard finds one project: `notification-service`. DISCUSS artifacts exist (complete), no DESIGN artifacts. Shows progress, recommends DESIGN. User confirms, wizard launches `/nw-design notification-service`.

### Example 2: DELIVER resume
```
/nw-continue rate-limiting
```
Wizard checks `rate-limiting` project. All waves through DISTILL complete, DELIVER in progress (steps 01-01 through 02-01 done). Shows "Next: step 02-02", launches `/nw-deliver "rate-limiting"`.

### Example 3: Multiple projects
```
/nw-continue
```
Wizard finds `rate-limiting` (modified today) and `user-notifications` (modified 3 days ago). Lists them, user picks `rate-limiting`. Wizard shows progress and recommends next wave.

### Example 4: No projects
```
/nw-continue
```
Wizard finds no `docs/feature/` directories. Shows "No active projects found" and suggests `/nw-new`.
