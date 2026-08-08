---
description: "Archives a completed feature to docs/evolution/, migrates lasting artifacts to permanent directories, preserves the feature workspace, and cleans session artifacts. Use after all implementation steps pass and mutation testing completes."
disable-model-invocation: true
argument-hint: '[agent] [feature-id] - Example: @platform-architect "auth-upgrade"'
---

# NW-FINALIZE: Feature Completion and Archive

**Wave**: CROSS_WAVE
**Agent**: @nw-platform-architect (default) or specified agent

## Overview

Finalize a completed feature: verify all steps done|create evolution document|migrate lasting artifacts to permanent directories|preserve the feature workspace|clean session artifacts. Agent gathers project data|analyzes execution history|writes summaries|migrates|preserves the source history.

`docs/feature/{feature-id}/` is the **feature workspace** — it is populated during active nWave waves (DISCUSS through DELIVER). At finalize, artifacts with lasting value are **copied** to permanent directories. WHEN finalize completes, the system SHALL retain `docs/feature/{feature-id}/`: the wave matrix derives status from this directory, so removing it would make finalized features disappear from the matrix. Only session markers and resume state are deleted.

## Usage

```
/nw-finalize @{agent} "{feature-id}"
```

## Context Files Required

- docs/feature/{feature-id}/deliver/roadmap.json - Original project plan
- docs/feature/{feature-id}/deliver/execution-log.json - Step execution history

## Pre-Dispatch Gate: All Steps Complete

Before dispatching, verify all steps are done — prevents archiving incomplete features.

Parse execution-log.json, verify every step has status DONE. If any step is not DONE, block finalization and list incomplete steps with current status. Do not dispatch until all steps complete.

## Phases

### Phase A — Evolution Document

**IF** `docs/evolution/*-{feature-id}.md` already exists, STOP with "ALREADY FINALIZED: {feature-id} — see docs/evolution/{file}. Re-run with --force to re-migrate." Do not write a second evolution doc and do not re-copy any artifact. Preserving the workspace makes this command re-runnable; without this check a second run writes a conflicting post-mortem and overwrites permanent copies edited since the first run.

Create `docs/evolution/YYYY-MM-DD-{feature-id}.md` with:
- Feature summary, business context, key decisions
- Steps completed (from execution-log.json)
- Key wave decisions (extracted from `*/wave-decisions.md` files)
- Lessons learned, issues encountered
- Links to migrated permanent artifacts

### Phase B — Migrate Lasting Artifacts

Scan `docs/feature/{feature-id}/` and migrate artifacts with lasting value to permanent directories. Create destination directories as needed.

#### Destination Map

| Source (feature workspace) | Destination (permanent) | Condition |
|---|---|---|
| `design/architecture-design.md` | `docs/architecture/{feature}/` | If exists |
| `design/component-boundaries.md` | `docs/architecture/{feature}/` | If exists |
| `design/technology-stack.md` | `docs/architecture/{feature}/` | If exists |
| `design/data-models.md` | `docs/architecture/{feature}/` | If exists |
| `design/adrs/ADR-*.md` | `docs/adrs/` | Flat namespace, cross-feature |
| `distill/test-scenarios.md` | `docs/scenarios/{feature}/` | Scenario-to-story traceability |
| `distill/walking-skeleton.md` | `docs/scenarios/{feature}/` | Walking skeleton specification |
| `discuss/journey-*.yaml` | `docs/ux/{feature}/` | If UX journeys exist |
| `discuss/journey-*-visual.md` | `docs/ux/{feature}/` | If UX visuals exist |

Research docs (`docs/research/`) are already in a permanent location — no migration needed.

#### What NOT to Migrate (stays in the workspace)

These are process scaffolding: they have no readership outside the feature, so
they are NOT copied to the permanent directories. They are NOT deleted either —
they remain in `docs/feature/{feature-id}/` as the feature's history.

**"Not migrated" means "not copied". It never means "deleted".** The only files
finalize removes are the session artifacts named in Phase C.

| File pattern | Why it is not copied |
|---|---|
| `deliver/execution-log.json` | Audit trail summarized in the evolution doc; the log itself stays, `des-verify-integrity` and `/nw-continue` read it |
| `deliver/roadmap.json` | Step plan — superseded by the evolution doc + git history for outside readers |
| `design/review-*.md` | Review findings summarized in the evolution doc |
| `distill/acceptance-review.md` | Test review — the tests themselves live in `tests/` |
| `discuss/dor-validation.md` | Process gate, no lasting audience |
| `discuss/shared-artifacts-registry.md` | Process scaffolding (if it exists) |
| `*/wave-decisions.md` | Key decisions extracted into the evolution doc |

### Phase C — Remove Session Artifacts

1. List ONLY the removal candidates, by exact path — `docs/feature/{feature-id}/deliver/.develop-progress.json` and `.nwave/des/deliver-session.json` (the latter sits outside the feature workspace; list it explicitly). This is the deletion set, not an inventory of the workspace.
2. Show that exact list to the user for approval. The user approves the set that will be deleted, and nothing wider.
3. Preserve the workspace — `docs/feature/{feature-id}/` is NOT deleted. The wave matrix derives status from this directory. Removing it would make finalized features disappear from the matrix. The evolution doc in `docs/evolution/` is the summary; the feature directory is the history.
4. On approval, delete exactly the approved paths. Do NOT delete wave artifacts (discuss/, design/, distill/, deliver/), and do NOT delete anything matched by a pattern rather than named in the approved list. IF a file looks temporary but was not approved, leave it.

**NEVER delete without user approval.** Show exactly what will be deleted.

### Phase D — Post-Finalize Verification

1. Verify all migrated files exist in their destinations
2. Update architecture doc statuses from "FUTURE DESIGN" to "IMPLEMENTED"
3. Optionally invoke /nw-document for reference docs (skip with --skip-docs)
4. Commit in logical groups:
   - Commit 1: evolution doc + migrated artifacts
   - Commit 2: session-artifact cleanup (feature workspace itself retained)

## Agent Invocation

@{agent}

Finalize: {feature-id}

**Key constraints:**
- Follow the 4-phase process (A → B → C → D) in order
- Create evolution document BEFORE migration (needs source files)
- Migrate BEFORE cleanup (preserves artifacts)
- Always show cleanup list and wait for user approval
- Commit and push after approval

## Progress Tracking

The invoked agent MUST create a task list from its workflow phases at the start of execution using TaskCreate. Each phase becomes a task with the gate condition as completion criterion. Mark tasks in_progress when starting each phase and completed when the gate passes. This gives the user real-time visibility into progress.

## Success Criteria

- [ ] All steps verified DONE before dispatch
- [ ] Evolution document created in docs/evolution/
- [ ] Architecture docs migrated to docs/architecture/{feature}/
- [ ] ADRs migrated to docs/adrs/ (if any)
- [ ] Scenario docs migrated to docs/scenarios/{feature}/ (if any)
- [ ] UX journeys migrated to docs/ux/{feature}/ (if any)
- [ ] User approved the session-artifact cleanup list
- [ ] Workspace directory retained: docs/feature/{feature-id}/ (wave artifacts intact)
- [ ] Session artifacts deleted: .nwave/des/deliver-session.json, .develop-progress.json, temp files
- [ ] Architecture docs updated to "IMPLEMENTED" status
- [ ] Committed and pushed

## Permanent Directory Structure

```
docs/
  adrs/                  # ADR-NNN-{slug}.md (flat, cross-feature)
  architecture/          # Design docs by feature
    {feature}/
      architecture-design.md
      component-boundaries.md
      data-models.md
      technology-stack.md
  decisions/             # Product decisions by feature (optional)
    {feature}/
  evolution/             # Post-mortem summaries
    YYYY-MM-DD-{feature-id}.md
  research/              # Research docs (flat, cross-feature)
  scenarios/             # Acceptance test documentation by feature
    {feature}/
      test-scenarios.md
      walking-skeleton.md
  ux/                    # UX specs and journeys by feature
    {feature}/
      journey-*.yaml
      journey-*-visual.md
```

## Error Handling

| Error | Response |
|-------|----------|
| Invalid agent name | "Invalid agent. Available: nw-researcher, nw-software-crafter, nw-solution-architect, nw-product-owner, nw-acceptance-designer, nw-platform-architect" |
| Missing feature ID | "Usage: /nw-finalize @agent 'feature-id'" |
| Project directory not found | "Project not found: docs/feature/{feature-id}/" |
| Incomplete steps | Block finalization, list incomplete steps |
| No files to migrate | Log "No lasting artifacts found — skipping Phase B" and proceed to cleanup |
| `execution-log.json` missing | BLOCK: "Cannot verify completion — docs/feature/{feature-id}/deliver/execution-log.json not found." Never treat an absent log as "all steps done". |
| `execution-log.json` unparseable | BLOCK: "docs/feature/{feature-id}/deliver/execution-log.json is not valid JSON: {reason}." Never treat an unreadable log as complete. |
| `execution-log.json` has zero events | BLOCK: "docs/feature/{feature-id}/deliver/execution-log.json records no phases — nothing to verify." An empty log satisfies "every step is DONE" vacuously; it must not. |
| Feature already finalized | BLOCK: "ALREADY FINALIZED: {feature-id} — see docs/evolution/{file}. Re-run with --force to re-migrate." |

## Examples

### Example 1: Standard finalization
```
/nw-finalize @nw-platform-architect "auth-upgrade"
```
Verifies all steps done. Creates evolution doc. Migrates `design/architecture-design.md` → `docs/architecture/auth-upgrade/`, ADRs → `docs/adrs/`, test-scenarios → `docs/scenarios/auth-upgrade/`. Shows remaining files, user approves, deletes session markers only — `docs/feature/auth-upgrade/` is retained. Commits.

### Example 2: Blocked by incomplete steps
```
/nw-finalize @nw-platform-architect "data-pipeline"
```
Pre-dispatch gate finds step 02-03 status IN_PROGRESS. Returns: "BLOCKED: 1 incomplete step - 02-03: IN_PROGRESS. Complete all steps before finalizing."

## Next Wave

**Handoff To**: Feature complete - no next wave
**Deliverables**: docs/evolution/YYYY-MM-DD-{feature-id}.md, migrated artifacts, retained feature workspace with session artifacts cleared

## Expected Outputs

```
docs/evolution/YYYY-MM-DD-{feature-id}.md
docs/architecture/{feature}/ (migrated design docs)
docs/adrs/ADR-*.md (migrated ADRs)
docs/scenarios/{feature}/ (migrated test scenarios)
docs/ux/{feature}/ (migrated UX journeys, if any)
Retained: docs/feature/{feature-id}/ (wave artifacts; session markers deleted)
```
