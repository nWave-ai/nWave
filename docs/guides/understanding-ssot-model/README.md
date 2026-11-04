# Understanding nWave's SSOT Model

Why nWave's documentation structure changed, and what v4 records today.

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

Over 10 features, you'd have 10 versions of the architecture, 10 versions of
the user journey, 10 versions of the system's KPIs — but no single current
one. Every agent re-read everything, every feature.

**Root cause**: Documents were produced to show waves *completed work*, not to
*serve downstream consumers*.

---

## The Solution: Durable SSOT, No Per-Feature Copies

Product truth moved to durable files under `docs/product/`, updated in place:

```
docs/product/
  vision.md                    Product vision + validated problems
  jobs.yaml                    All validated jobs + opportunity scores
  journeys/
  architecture/
  kpi-contracts.yaml           Active measurement contracts
```

This part of the model is current. `/nw-discover` bootstraps `vision.md` and
`jobs.yaml` (and `kpi-contracts.yaml` for a quantified baseline); `/nw-diverge`
updates `jobs.yaml` with the validated job and a changelog entry.

## What Replaced the Delta Directory

The 3.x answer for per-feature records was a delta directory,
`docs/features/{id}/`, with at most six files per feature:
`feature-brief.md`, `recommendation.md`, `user-stories.md`,
`wave-decisions.md`, `acceptance-tests.feature` and `roadmap.json`.

v4 replaced it with one **feature directory**: `docs/feature/{id}/`, holding
the nwdes handoff (`handoff.json`), the briefs rendered from it
(`brief.md`, `architecture.md`, `acceptance.md`, with HTML versions) and the
run records under `runs/`. `roadmap.json`, `execution-log.json` and
`wave-decisions.md` are retired; no current wave writes a per-wave ledger, and
nothing converts the old files ([Migrate from nWave 3.x](../migrating-from-3x.md)).

---

## Why This Matters for You

- You maintain the SSOT files as living products (like code); every reader
  finds one current version.
- Each delivery feature has one canonical record, the handoff, and the human
  reading surface is rendered from it — nothing to keep in sync by hand.
- Merge conflicts happen at git merge time, with clear history of who changed
  what.

See [Understanding delivery artifacts](../understanding-delivery-artifacts/)
for what a v4 delivery produces, and [Wave Directory
Structure](../wave-directory-structure/) for where everything lives.
