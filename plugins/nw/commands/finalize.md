---
description: "Archives a completed feature to docs/evolution/, migrates lasting artifacts to permanent directories, and cleans up the temporary workspace. Use after all implementation steps pass and mutation testing completes."
disable-model-invocation: true
argument-hint: '[agent] [feature-id] - Example: @platform-architect "auth-upgrade"'
---

# NW-FINALIZE: Feature Completion and Archive

**Wave**: CROSS_WAVE
**Agent**: @nw-platform-architect (default) or specified agent

## Overview

Finalize a completed feature: verify all steps done|create evolution document|migrate lasting artifacts to permanent directories|clean up temporary workspace. Agent gathers project data|analyzes execution history|writes summaries|migrates|cleans up.

`docs/feature/{feature-id}/` is a **temporary workspace** — it exists during active nWave waves (DISCUSS through DELIVER). At finalize, artifacts with lasting value migrate to permanent directories; the rest is discarded.

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

Create `docs/evolution/YYYY-MM-DD-{feature-id}.md` with:
- Feature summary, business context, key decisions
- Steps completed (from execution-log.json)
- Key wave decisions (extracted from `*/wave-decisions.md` files)
- Lessons learned, issues encountered
- Links to migrated permanent artifacts

### Phase B — Migrate Lasting Artifacts

Scan `docs/feature/{feature-id}/` and migrate artifacts with lasting value to permanent directories. Create destination directories as needed.

#### Destination Map

| Source (temporary workspace) | Destination (permanent) | Condition |
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

#### What NOT to Migrate (Discard)

These are process scaffolding — valuable during delivery, disposable after:

| File pattern | Why discard |
|---|---|
| `deliver/execution-log.json` | Audit trail captured in evolution doc |
| `deliver/roadmap.json` | Step plan — superseded by evolution doc + git history |
| `deliver/.develop-progress.json` | Resume state — temporary |
| `design/review-*.md` | Review findings captured in evolution doc |
| `distill/acceptance-review.md` | Test review — tests themselves remain in `tests/` |
| `discuss/dor-validation.md` | Process gate, not lasting value |
| `discuss/shared-artifacts-registry.md` | Process scaffolding (if exists) |
| `*/wave-decisions.md` | Key decisions extracted into evolution doc |

### Phase C — Cleanup Workspace

1. List all remaining files in `docs/feature/{feature-id}/` after migration
2. Show the list to the user for approval
3. On approval: `rm -rf docs/feature/{feature-id}/`
4. If `docs/feature/` directory is now empty: remove it too

**NEVER delete without user approval.** Show exactly what will be removed.

### Phase D — Post-Cleanup Verification

1. Verify all migrated files exist in their destinations
2. Update architecture doc statuses from "FUTURE DESIGN" to "IMPLEMENTED"
3. Optionally invoke /nw-document for reference docs (skip with --skip-docs)
4. Commit in logical groups:
   - Commit 1: evolution doc + migrated artifacts
   - Commit 2: workspace cleanup (removal)

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
- [ ] User approved cleanup before workspace removal
- [ ] Workspace directory removed: docs/feature/{feature-id}/
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

## Examples

### Example 1: Standard finalization
```
/nw-finalize @nw-platform-architect "auth-upgrade"
```
Verifies all steps done. Creates evolution doc. Migrates `design/architecture-design.md` → `docs/architecture/auth-upgrade/`, ADRs → `docs/adrs/`, test-scenarios → `docs/scenarios/auth-upgrade/`. Shows remaining files, user approves, removes workspace. Commits.

### Example 2: Blocked by incomplete steps
```
/nw-finalize @nw-platform-architect "data-pipeline"
```
Pre-dispatch gate finds step 02-03 status IN_PROGRESS. Returns: "BLOCKED: 1 incomplete step - 02-03: IN_PROGRESS. Complete all steps before finalizing."

## Next Wave

**Handoff To**: Feature complete - no next wave
**Deliverables**: docs/evolution/YYYY-MM-DD-{feature-id}.md, migrated artifacts, cleaned workspace

## Expected Outputs

```
docs/evolution/YYYY-MM-DD-{feature-id}.md
docs/architecture/{feature}/ (migrated design docs)
docs/adrs/ADR-*.md (migrated ADRs)
docs/scenarios/{feature}/ (migrated test scenarios)
docs/ux/{feature}/ (migrated UX journeys, if any)
Removed: docs/feature/{feature-id}/
```
