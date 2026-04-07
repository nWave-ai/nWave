# Understanding nWave's SSOT Model

Why did nWave's documentation structure change? This guide explains the new model and how to navigate it.

---

## The Problem with 26 Documents Per Feature

Previously, every feature produced ~26 documents across 7 wave directories:

- DISCOVER: 4 documents
- DIVERGE: 5 documents
- DISCUSS: 12 documents
- DESIGN: 4 documents
- DEVOPS: 2 documents
- DISTILL: 1 document
- DELIVER: 1 document

Over 10 features, you'd have 10 versions of the architecture, 10 versions of the user journey, 10 versions of the system's KPIs — but no single current one. Every agent re-read everything, every feature.

**Root cause**: Documents were produced to show waves *completed work*, not to *serve downstream consumers*.

---

## The Solution: SSOT + Delta

Two categories of documents, with different lifespans:

### SSOT: Single Source of Truth (Product-level)

Lives in `docs/product/`. Grows over time, never duplicates.

```
docs/product/
  vision.md                    Product vision + validated problems
  jobs.yaml                    All validated jobs + opportunity scores
  journeys/
    onboarding.yaml            Current onboarding user experience
    onboarding-visual.md       Human-readable journey narrative
    {other-journeys}.yaml      ...
  architecture/
    brief.md                   Current component boundaries
    adr-001.md                 Architectural decision records
    adr-002.md                 (permanent decisions, never deleted)
  kpi-contracts.yaml           Active measurement contracts
```

**Updated by**: Each wave that produces insights (DIVERGE updates jobs, DISCUSS updates journeys, DESIGN updates architecture, DEVOPS updates KPIs).

**Read by**: Every downstream agent, at wave start.

### Delta: Feature-Specific (Feature-level)

Lives in `docs/features/{id}/`. Max 6 files per feature, describing *what this feature changes*.

```
docs/features/feat-001/
  feature-brief.md             Generated summary (for humans)
  recommendation.md            Chosen direction (from DIVERGE)
  user-stories.md              Stories for this feature (from DISCUSS)
  wave-decisions.md            Decisions made across all waves
  acceptance-tests.feature     Executable specs (from DISTILL)
  roadmap.json                 Implementation plan (from DELIVER)
```

**Written during**: Feature work (one wave at a time).

**Read by**: Later waves in the same feature, plus the implementation team.

---

## The Feature Brief: Your Human Layer

The SSOT files (YAML) serve agents. The delta files (acceptance tests, roadmap) serve the delivery pipeline.

The **feature-brief.md** is the *only* file designed for humans to read and approve.

### What it answers:

- **What are we building?** (from recommendation.md)
- **Why are we building it?** (from recommendation.md + jobs.yaml)
- **What will the user experience?** (from journeys/*.yaml)
- **What are we testing?** (from user-stories.md)
- **How will we know it worked?** (from kpi-contracts.yaml)
- **What trade-offs did we accept?** (from architecture/brief.md)

### When it appears:

Once, after DISTILL completes (when all waves have run and all decisions are made). It's a snapshot, not a living document.

If waves re-run, the brief is regenerated.

---

## Which Wave Updates What

| Wave | Reads SSOT | Produces Delta | Updates SSOT |
|------|-----------|----------------|--------------|
| DISCOVER | `jobs.yaml` | (evidence brief) | `jobs.yaml` + new validated job |
| DIVERGE | `jobs.yaml`, `vision.md` | `recommendation.md` | `jobs.yaml` (adds/updates job) |
| DISCUSS | `journeys/` | `user-stories.md` | `journeys/` (extends current journey) |
| DESIGN | `architecture/brief.md` | `wave-decisions.md` | `architecture/brief.md` + ADRs |
| DEVOPS | `kpi-contracts.yaml` | (infra spec) | `kpi-contracts.yaml` + contracts |
| DISTILL | All of above | `acceptance-tests.feature` | (none — tests are read-only) |
| DELIVER | `acceptance-tests.feature` | code | (code is the SSOT for implementation) |

---

## Directory Structure

### Old Model (still supported, read-only)

```
docs/feature/{id}/
  discover/
  diverge/
  discuss/
  design/
  devops/
  distill/
  deliver/
```

Used by features completed before the SSOT model. Not migrated, not deleted. Agents read this as fallback only if `docs/product/` doesn't exist.

### New Model (SSOT + Delta)

```
docs/product/            ← Single source of truth
  vision.md
  jobs.yaml
  journeys/
  architecture/
  kpi-contracts.yaml

docs/features/{id}/      ← Feature-specific deltas (max 6 files)
  feature-brief.md
  recommendation.md
  user-stories.md
  wave-decisions.md
  acceptance-tests.feature
  roadmap.json
```

---

## Schema Versioning

SSOT YAML files include:

```yaml
schema_version: 1

# ... content ...

changelog:
  - date: 2026-04-05
    feature: feat-001
    change: "Added 2FA support to onboarding journey"
  - date: 2026-04-01
    feature: feat-002
    change: "Updated authentication architecture"
```

**Why**: When schemas evolve (e.g., adding a new field to journeys), old YAML files continue to work. New fields default to empty/unset. No forced migration.

---

## Backward Compatibility

**Old features are frozen.** New features use the SSOT model.

### Fallback rules:

1. Agents check `docs/product/` first (SSOT)
2. If `docs/product/` doesn't exist, agents fall back to `docs/feature/{id}/` (old model) for that feature only
3. Once `docs/product/` exists, agents *never* read old feature directories for SSOT information
4. Old features can still be referenced for historical context (ADR history, past decisions) but are not authoritative

### First feature with SSOT:

When you run the first feature using the SSOT model, `docs/product/` is created from scratch. Old feature documents are *not* imported. The SSOT starts clean and grows with each new feature.

---

## Document Count: Before and After

| Wave | Old Count | New Count | Savings |
|------|-----------|-----------|---------|
| DISCOVER | 4 | → SSOT | −3 |
| DIVERGE | 5 | → SSOT | −3 |
| DISCUSS | 12 | → SSOT | −10 |
| DESIGN | 4 | → SSOT | −2 |
| DEVOPS | 2 | → SSOT | −1 |
| DISTILL | 1 | 1 | 0 |
| DELIVER | 1 | 1 | 0 |
| **Per feature** | ~26 | ~6 | **−20** |

The SSOT documents are written once and updated. Delta files serve only the current feature. Result: agents read ~77% fewer documents, token waste drops, and the single source of truth is always current.

---

## Why This Matters for You

### Before:
- You had to keep 26 documents in sync across teams
- Agents re-read everything on every feature
- No way to know which version of "architecture" was current
- Merge conflicts on the same file from different features

### After:
- You maintain SSOT files as living products (like code)
- Each feature records *what it changed* in deltas
- Agents read current state from one place
- Merge conflicts happen at git merge time, with clear history of *who changed what*

The feature-brief gives humans a single place to review and approve before implementation starts.
