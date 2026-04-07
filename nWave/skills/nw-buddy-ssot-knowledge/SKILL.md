---
name: nw-buddy-ssot-knowledge
description: How the SSOT + Delta document model works — file locations, what each file contains, backward compatibility, migration. For the buddy agent to explain and navigate the document model.
user-invocable: false
disable-model-invocation: true
---

# SSOT + Delta Document Model

## Two-Tier Model

**SSOT** (Single Source of Truth) in `docs/product/` — what the system IS now. Updated by each wave. Never duplicated per feature.

**Delta** in `docs/features/{id}/` — what THIS feature changes. Max 6 files per feature.

## SSOT Directory Structure

```
docs/product/
  vision.md                    Product vision + validated problems
  jobs.yaml                    All validated JTBD jobs + opportunity scores
  journeys/
    {name}.yaml                Current journey schema (updated by DISCUSS)
    {name}-visual.md           Human-readable journey narrative
  architecture/
    brief.md                   Current component boundaries (updated by DESIGN)
    adr-*.md                   Architectural decision records (permanent)
  kpi-contracts.yaml           Active measurement contracts (updated by DEVOPS)
```

## Feature Delta Structure

```
docs/features/{id}/
  feature-brief.md             Generated summary for human review (after DISTILL)
  recommendation.md            Chosen direction (from DIVERGE)
  user-stories.md              Stories for this feature (from DISCUSS)
  wave-decisions.md            Decisions made across all waves (incremental)
  acceptance-tests.feature     Executable specs (from DISTILL)
  roadmap.json                 Implementation plan (from DELIVER)
```

## Which Wave Updates What

| Wave | Reads SSOT | Produces Delta | Updates SSOT |
|------|-----------|----------------|--------------|
| DISCOVER | `jobs.yaml` | (evidence brief) | `jobs.yaml` + new validated job |
| DIVERGE | `jobs.yaml`, `vision.md` | `recommendation.md`, `job-analysis.md` | `jobs.yaml` |
| DISCUSS | `journeys/`, `jobs.yaml`, `vision.md` | `user-stories.md`, `story-map.md`, `outcome-kpis.md` | `journeys/` (extends journey), `jobs.yaml` (if new job from DIVERGE) |
| DESIGN | `architecture/brief.md`, `journeys/` | `wave-decisions.md` | `architecture/brief.md` + ADRs + `c4-diagrams.md` |
| DEVOPS | `architecture/brief.md`, `kpi-contracts.yaml` | (infra spec) | `kpi-contracts.yaml` |
| DISTILL | all above | `acceptance-tests.feature` | (none) |
| DELIVER | `acceptance-tests.feature` | code | (code is the SSOT) |

## Old Model (Backward Compatibility)

Features created before SSOT use per-wave subdirectories:

```
docs/feature/{id}/          <- OLD MODEL (note: "feature" singular)
  discover/
  diverge/
  discuss/
  design/
  devops/
  distill/
  deliver/
```

**Migration gate** (CRITICAL): If `docs/product/` does not exist but `docs/feature/` has existing features, the project MUST migrate before running new waves. All wave skills enforce this gate. Direct the user to the migration guide: `docs/guides/migrating-to-ssot-model/README.md`.

**Key difference**: `docs/feature/` (singular, old) vs `docs/features/` (plural, new delta).

## Migration Path

Follow the step-by-step guide: `docs/guides/migrating-to-ssot-model/README.md`

Summary of the 7 steps:

1. Create `docs/product/` directory structure
2. Extract validated jobs into `jobs.yaml`
3. Consolidate journeys from features into `journeys/`
4. Create architecture brief from design artifacts
5. Extract KPI contracts
6. Create vision.md (one-time, ~50 lines)
7. Verify YAML syntax, commit

No forced migration. Old and new coexist. New features use SSOT automatically.

## Schema Versioning

SSOT YAML files include `schema_version: 1` and a `changelog:` section tracking which feature changed what, when. This enables conflict resolution at git merge time.

## Document Count Comparison

Old model: ~26 documents per feature. New model: ~6 delta files per feature + shared SSOT. Result: 77% fewer documents, single source of truth always current.

## How to Check Document Model

To determine which model a project uses:

1. Check if `docs/product/` exists -> SSOT model active
2. Check if `docs/features/` exists -> new delta files present
3. Check if `docs/feature/` exists -> old model features present
4. Both can coexist in the same project

> For the full authoritative SSOT model reference, read `docs/guides/understanding-ssot-model/README.md`.
> For the migration guide, read `docs/guides/migrating-to-ssot-model/README.md`.
