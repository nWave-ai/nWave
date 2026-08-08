---
name: nw-finalize
description: "Archives a completed feature to docs/evolution/, migrates lasting artifacts to permanent directories, preserves the feature workspace, and cleans session artifacts. Use after all implementation steps pass and mutation testing completes."
user-invocable: false
argument-hint: '[agent] [feature-id] - Example: @platform-architect "auth-upgrade"'
---

# NW-FINALIZE: Feature Completion and Archive

**Wave**: CROSS_WAVE
**Agent**: @nw-platform-architect (default) or specified agent

## Overview

Finalize a completed feature: verify all steps done|create evolution document|migrate lasting artifacts to permanent directories|preserve the feature workspace|clean session artifacts. Agent gathers project data|analyzes execution history|writes summaries|migrates|preserves the source history.

`docs/feature/{feature-id}/` is the **feature workspace** — it is populated during active nWave waves (DISCUSS through DELIVER). At finalize, artifacts with lasting value are **copied** to permanent directories. WHEN finalize completes, the system SHALL retain `docs/feature/{feature-id}/`. Only session markers and resume state are deleted. See Phase C step 3 for why retention is required.

## Usage

```
/nw-finalize @{agent} "{feature-id}"
```

## Context Files Required

The completion-evidence files are `docs/feature/{feature-id}/deliver/roadmap.json` (the original project plan) and `docs/feature/{feature-id}/deliver/execution-log.json` (step execution history).

## Pre-Dispatch Gate: All Work Complete

Before dispatching, verify all work is done — prevents archiving incomplete features.

1. **Parse execution log** — Read `docs/feature/{feature-id}/deliver/execution-log.json`. Gate: file readable.
2. **Verify completeness** — Check every step has status `DONE`. Gate: all steps DONE.
3. **Block or proceed** — If any step is not DONE, list incomplete steps with current status and halt. If all DONE, proceed to dispatch. Gate: zero incomplete steps before dispatch.

## Phases

### Phase A — Evolution Document

0. **Refuse a second finalize** — **IF** `docs/evolution/*-{feature-id}.md` already exists, the system SHALL stop with "ALREADY FINALIZED: {feature-id} — see docs/evolution/{file}. Re-run with --force to re-migrate." and SHALL NOT write a second evolution doc or re-copy any artifact. Gate: no existing evolution doc, or `--force` given.

   Preserving the workspace makes `/nw-finalize` re-runnable, so this check is what stops a second run from writing a conflicting post-mortem and overwriting permanent copies that were edited since the first run. When the workspace was deleted, "project directory not found" happened to provide this; it no longer does.

1. **Gather source data** — Read `execution-log.json` + `roadmap.json` (the step log and plan), and all `*/wave-decisions.md` files. Gate: source files read.
2. **Extract key decisions** — Pull decisions, issues, and lessons from wave-decisions files. Gate: decisions list assembled.
3. **Write evolution doc** — Create `docs/evolution/YYYY-MM-DD-{feature-id}.md` with: feature summary, business context, key decisions, work completed (from `execution-log.json`), lessons learned, issues encountered, links to migrated permanent artifacts. Gate: file written.

### Phase B — Migrate Lasting Artifacts

1. **Scan workspace** — List all files under `docs/feature/{feature-id}/`. Gate: file list produced.
2. **Match against destination map** — For each file, apply the destination map below. Gate: migration plan assembled.
3. **Create destination directories** — Create any missing permanent directories. Gate: directories exist.
4. **Copy files** — Copy each matched file to its permanent destination. Gate: all copies verified.
5. **Log skipped files** — Note any files from the discard list (not migrated). Gate: discard list documented.

#### Destination Map

| Source (feature workspace) | Destination (permanent) | Condition |
|---|---|---|
| `design/architecture-design.md` | `docs/architecture/{feature}/` | If exists |
| `design/component-boundaries.md` | `docs/architecture/{feature}/` | If exists |
| `design/technology-stack.md` | `docs/architecture/{feature}/` | If exists |
| `design/data-models.md` | `docs/architecture/{feature}/` | If exists |
| `design/adrs/ADR-*.md` | `docs/adrs/` | Flat namespace, cross-feature |
| `distill/walking-skeleton.md` | `docs/scenarios/{feature}/` | Walking skeleton specification |
| `discuss/journey-*.yaml` | `docs/ux/{feature}/` | If UX journeys exist |
| `discuss/journey-*-visual.md` | `docs/ux/{feature}/` | If UX visuals exist |

Research docs (`docs/research/`) are already in a permanent location — no migration needed.

#### What NOT to Migrate (stays in the workspace)

These are process scaffolding: they have no readership outside the feature, so
they are NOT copied to the permanent directories. They are NOT deleted either —
they remain in `docs/feature/{feature-id}/` as the feature's history.

**"Not migrated" means "not copied". It never means "deleted".** The only files
finalize removes are the session artifacts named in Phase C step 4.

| File pattern | Why it is not copied |
|---|---|
| `deliver/execution-log.json` | Audit trail — summarized in the evolution doc; the log itself stays, `des-verify-integrity` and `/nw-continue` read it |
| `deliver/roadmap.json` | Step plan — superseded by the evolution doc + git history for outside readers |
| `design/review-*.md` | Review findings summarized in the evolution doc |
| `discuss/dor-checklist.md` | Process gate, no lasting audience |
| `discuss/shared-artifacts-registry.md` | Process scaffolding |
| `discuss/prioritization.md` | Superseded by roadmap execution |
| `*/wave-decisions.md` | Key decisions extracted into evolution doc |

### Phase C — Remove Session Artifacts

1. **List the removal candidates** — List ONLY the files this phase would remove, by exact path:
   - `docs/feature/{feature-id}/deliver/.develop-progress.json`
   - `.nwave/des/deliver-session.json` (outside the feature workspace — list it explicitly, it is easy to miss)

   This list is the deletion set. It is NOT an inventory of the workspace: everything else under `docs/feature/{feature-id}/` stays. Gate: list produced, containing only the paths above that actually exist.
2. **Present for approval** — Show that exact list and request approval. The user approves the set that will be deleted, and nothing wider. Gate: user explicitly approves.
3. **Preserve workspace** — `docs/feature/{feature-id}/` is NOT deleted. The wave matrix derives status from this directory. Removing it would make finalized features disappear from the matrix. The evolution doc in `docs/evolution/` is the summary; the feature directory is the history. Gate: directory preserved.
4. **Remove the approved set only** — Delete exactly the paths approved in step 2. Do NOT remove wave artifacts (`discuss/`, `design/`, `distill/`, `deliver/`), and do NOT delete anything matched by a pattern rather than named in the list. **IF** a file appears to be temporary but was not in the approved list, the system SHALL leave it. Gate: approved paths removed, wave artifacts intact.

**NEVER delete without user approval.** Show exactly what will be removed.

### Phase D — Post-Finalize Verification

1. **Verify migrated files** — Confirm every file copied in Phase B exists at its destination. Gate: all destinations present.
2. **Update architecture doc statuses** — Change any "FUTURE DESIGN" labels to "IMPLEMENTED" in migrated architecture docs. Gate: no stale FUTURE DESIGN labels.
3. **Optionally generate reference docs** — Invoke /nw-document unless `--skip-docs` flag provided. Gate: docs generated or skipped.
4. **Commit evolution doc and artifacts** — Commit 1: evolution doc + migrated artifacts. Gate: commit created.
5. **Commit session-artifact cleanup** — Commit 2: removal of session markers and resume state only; `docs/feature/{feature-id}/` and its wave artifacts stay tracked. Gate: commit created and pushed.

## Agent Invocation

@{agent}

Finalize: {feature-id}

**Key constraints:**

1. Follow the 4-phase process (A → B → C → D) in order.
2. Create evolution document BEFORE migration (needs source files).
3. Migrate BEFORE cleanup (preserves artifacts).
4. Show cleanup list and wait for user approval before removing anything.
5. Commit and push after approval.

## Success Criteria

- [ ] All steps verified DONE before dispatch
- [ ] Evolution document created in docs/evolution/
- [ ] Architecture docs migrated to docs/architecture/{feature}/
- [ ] ADRs migrated to docs/adrs/ (if any)
- [ ] Scenario docs migrated to docs/scenarios/{feature}/ (if any)
- [ ] UX journeys migrated to docs/ux/{feature}/ (if any)
- [ ] User approved the session-artifact cleanup list
- [ ] Workspace directory retained: docs/feature/{feature-id}/ (wave artifacts intact)
- [ ] Session artifacts removed: .nwave/des/deliver-session.json, .develop-progress.json, temp files
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
Verifies all steps done. Creates evolution doc. Migrates `design/architecture-design.md` → `docs/architecture/auth-upgrade/`, ADRs → `docs/adrs/`, test-scenarios → `docs/scenarios/auth-upgrade/`. Shows remaining files, user approves, removes session markers only — `docs/feature/auth-upgrade/` is retained. Commits.

### Example 2: Blocked by incomplete steps
```
/nw-finalize @nw-platform-architect "data-pipeline"
```
Pre-dispatch gate finds step 02-03 status IN_PROGRESS. Returns: "BLOCKED: 1 incomplete step - 02-03: IN_PROGRESS. Complete all steps before finalizing."

## Next Wave

**Handoff To**: Feature complete - no next wave
**Deliverables**: docs/evolution/YYYY-MM-DD-{feature-id}.md, migrated artifacts, retained feature workspace with session artifacts cleaned

## Expected Outputs

```
docs/evolution/YYYY-MM-DD-{feature-id}.md
docs/architecture/{feature}/ (migrated design docs)
docs/adrs/ADR-*.md (migrated ADRs)
docs/scenarios/{feature}/ (migrated test scenarios)
docs/ux/{feature}/ (migrated UX journeys, if any)
Retained: docs/feature/{feature-id}/ (wave artifacts; session markers removed)
```
