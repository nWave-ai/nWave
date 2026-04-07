---
name: nw-buddy-project-reading
description: How to read a project's nWave state — detect document model, determine wave progress, find feature artifacts. For the buddy agent to give contextual advice.
user-invocable: false
disable-model-invocation: true
---

# Project State Reading

## Step 1: Detect Document Model

```
Glob for docs/product/ -> SSOT model active
Glob for docs/features/ -> new delta files present
Glob for docs/feature/ -> old model features present
Neither exists -> greenfield project (no waves run yet)
```

## Step 2: List Features

**SSOT model**: `ls docs/features/` -> each directory is a feature ID.
**Old model**: `ls docs/feature/` -> each directory is a feature ID.
**Both models**: features can coexist.

## Step 3: Determine Wave Progress Per Feature

### SSOT Model Detection

| Wave | Complete When |
|------|--------------|
| DISCOVER | `docs/product/jobs.yaml` has a validated job for this feature |
| DIVERGE | `docs/features/{id}/recommendation.md` exists |
| DISCUSS | `docs/features/{id}/user-stories.md` exists |
| DESIGN | `docs/product/architecture/brief.md` updated for this feature (check changelog) |
| DEVOPS | `docs/product/kpi-contracts.yaml` has contracts for this feature |
| DISTILL | `docs/features/{id}/acceptance-tests.feature` exists AND `tests/acceptance/{id}/` has feature files |
| DELIVER | `docs/features/{id}/roadmap.json` with all steps at COMMIT/PASS |

### Old Model Detection

| Wave | Complete When |
|------|--------------|
| DISCOVER | `docs/feature/{id}/discover/problem-validation.md` exists |
| DIVERGE | `docs/feature/{id}/diverge/recommendation.md` exists |
| DISCUSS | `docs/feature/{id}/discuss/user-stories.md` exists |
| DESIGN | `docs/feature/{id}/design/architecture-design.md` exists |
| DEVOPS | `docs/feature/{id}/devops/platform-architecture.md` exists |
| DISTILL | `docs/feature/{id}/distill/test-scenarios.md` exists |
| DELIVER | `docs/feature/{id}/deliver/execution-log.json` with all steps at COMMIT/PASS |

## Step 4: Build Progress Dashboard

For each feature, build a wave completion table:

```
Feature: {id}
Model: SSOT | Old | Mixed

| Wave     | Status     | Evidence |
|----------|------------|----------|
| DISCOVER | complete   | jobs.yaml has validated job JOB-003 |
| DIVERGE  | complete   | recommendation.md exists |
| DISCUSS  | complete   | user-stories.md exists |
| DESIGN   | incomplete | architecture/brief.md has no entry for this feature |
| DEVOPS   | skipped    | (check if skip conditions met) |
| DISTILL  | not started| |
| DELIVER  | not started| |

Next wave: DESIGN
Recommended command: /nw-design {id}
```

## Step 5: Recommend Next Action

Based on progress:
1. Find first incomplete wave (not skipped)
2. Check if skip conditions are met for that wave
3. If skip conditions met, move to next wave
4. Recommend the command for the first required incomplete wave
5. Provide rationale based on what's missing

## Reading SSOT Files

When the user asks about product state:

- **Jobs**: Read `docs/product/jobs.yaml` -> list validated jobs, opportunity scores
- **Journeys**: Glob `docs/product/journeys/*.yaml` -> list current journeys
- **Architecture**: Read `docs/product/architecture/brief.md` -> current components, driving ports
- **ADRs**: Glob `docs/product/architecture/adr-*.md` -> list architectural decisions
- **KPIs**: Read `docs/product/kpi-contracts.yaml` -> active measurement contracts
- **Vision**: Read `docs/product/vision.md` -> product mission and principles

## Troubleshooting Missing Prerequisites

When a wave fails due to missing prerequisites:

| Error Signal | Missing Prerequisite | Fix |
|-------------|---------------------|-----|
| DISTILL says "architecture missing" | `docs/product/architecture/brief.md` | Run `/nw-design {id}` first |
| DISTILL says "no user stories" | `docs/features/{id}/user-stories.md` | Run `/nw-discuss {id}` first |
| DELIVER says "no acceptance tests" | `docs/features/{id}/acceptance-tests.feature` | Run `/nw-distill {id}` first |
| DISCUSS says "no recommendation" | `docs/features/{id}/recommendation.md` | Run `/nw-diverge {id}` first (if multiple approaches) |
| Agent reads stale journey | Journey changelog date > 6 months | Re-run `/nw-discuss {id}` to refresh |

> For authoritative detection rules and directory structure, read `docs/guides/wave-directory-structure/README.md`.
