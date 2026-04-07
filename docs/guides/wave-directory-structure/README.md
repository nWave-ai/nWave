# Wave Directory Structure

How nWave organizes artifacts across the seven-wave methodology.

## Document Model: SSOT + Delta

nWave uses a two-tier document model:

**Product SSOT** (`docs/product/`) — what the system IS now. Updated by each wave. Never duplicated per feature.

```
docs/product/
  vision.md                 ← product vision (updated by DIVERGE)
  jobs.yaml                 ← validated JTBD jobs (updated by DIVERGE)
  journeys/
    {name}.yaml             ← current journey schema (updated by DISCUSS)
    {name}-visual.md        ← human-readable journey (updated by DISCUSS)
  architecture/
    brief.md                ← current architecture (updated by DESIGN)
    adr-*.md                ← permanent decisions
  kpi-contracts.yaml        ← measurement contracts (updated by DEVOPS)
```

**Feature Delta** (`docs/features/{id}/`) — what THIS feature changes. Max 6 files.

```
docs/features/{id}/
  feature-brief.md          ← generated summary for human review
  recommendation.md         ← chosen direction (from DIVERGE)
  user-stories.md           ← stories for this feature (from DISCUSS)
  wave-decisions.md         ← decisions made across all waves
  acceptance-tests.feature  ← executable specs (from DISTILL)
  roadmap.json              ← implementation plan (from DELIVER)
```

See [Understanding the SSOT Model](../understanding-ssot-model/) for the full explanation.

## New Features: SSOT + Delta Model

New features write output to two locations:

1. **SSOT updates** in `docs/product/` — the wave updates the living product documents
2. **Feature delta** in `docs/features/{id}/` — max 6 files describing what this feature changes

Waves do NOT create per-wave subdirectories. Each wave appends to feature-level files or updates the SSOT. The `wave-decisions.md` file is built incrementally — each wave adds its section.

### Which Wave Updates What

| Wave | Reads from SSOT | Produces delta | Updates SSOT |
|------|----------------|----------------|--------------|
| DISCOVER | `jobs.yaml` | (evidence brief, internal) | `jobs.yaml` |
| DIVERGE | `jobs.yaml`, `vision.md` | `recommendation.md` | `jobs.yaml` |
| DISCUSS | `journeys/{name}.yaml` | `user-stories.md` | `journeys/{name}.yaml` |
| DESIGN | `architecture/brief.md` | `wave-decisions.md` | `architecture/brief.md` + ADRs |
| DEVOPS | `kpi-contracts.yaml` | (infra spec, internal) | `kpi-contracts.yaml` |
| DISTILL | all 3 SSOT dimensions | `acceptance-tests.feature` | — |
| DELIVER | `acceptance-tests.feature` | code | code |

## Old Features: Per-Wave Directories (Archived)

Existing features created before the SSOT model use per-wave subdirectories under `docs/feature/{feature-id}/`. These are frozen archives — not updated, not migrated.

```
docs/feature/{feature-id}/          ← OLD MODEL (archived)
├── discover/
│   ├── problem-validation.md
│   └── lean-canvas.md
├── discuss/
│   ├── journey-{name}-visual.md
│   ├── journey-{name}.yaml
│   ├── user-stories.md
│   └── ...
├── design/
│   └── architecture-design.md
├── devops/
│   └── platform-architecture.md
├── distill/
│   └── test-scenarios.md
└── deliver/
    ├── roadmap.json
    └── execution-log.json
```

Agents check `docs/product/` first (SSOT). If it does not exist, they fall back to `docs/feature/{id}/` for the current feature (old model).

## Cross-Feature Artifacts

Acceptance test files and cross-feature documents live outside the per-feature tree:

| Location | Content | Written By |
|----------|---------|-----------|
| `tests/{test-type}/{feature-id}/acceptance/` | Executable test files (.feature, step definitions) | acceptance-designer (DISTILL) |
| `docs/product/architecture/adr-*.md` | Architecture Decision Records (SSOT) | solution-architect (DESIGN) |
| `docs/evolution/` | Post-completion archives | platform-architect (/nw-finalize) |
| `CLAUDE.md` (project root) | Development paradigm, mutation testing strategy | solution-architect, platform-architect |

## Feature ID Derivation

When you run `/nw-new`, `/nw-deliver`, or any wave command, nWave derives a feature ID from your description:

1. Strip common prefixes: "implement", "add", "create", "build"
2. Remove English stop words: "a", "the", "to", "for", "with", "and", "in", "on", "of"
3. Convert to kebab-case (lowercase, hyphens)
4. Limit to 5 segments maximum

**Examples:**
- "Add rate limiting to the API gateway" → `rate-limiting-api-gateway`
- "OAuth2 upgrade" → `oauth2-upgrade`

In the SSOT model, this ID is used as `docs/features/{id}/` for delta files.

## Acceptance Test Directory Structure

Executable acceptance tests live in `tests/`, not in documentation:

```
tests/
├── acceptance/
│   └── {feature-id}/
│       └── {scenario-name}.feature     (Gherkin feature files)
│       ├── step_definitions.py         (Given/When/Then implementations)
│       ├── fixtures/
│       └── conftest.py                 (pytest configuration for this feature)
```

The acceptance-designer (DISTILL wave) designs the tests and writes them directly to `tests/acceptance/{feature-id}/`.

## Wave Detection

`/nw-continue` uses these rules to detect progress:

### New model (SSOT)

| Wave | Complete When |
|------|--------------|
| DISCOVER | `docs/product/jobs.yaml` has a validated job for this feature |
| DIVERGE | `docs/features/{id}/recommendation.md` exists |
| DISCUSS | `docs/features/{id}/user-stories.md` exists |
| DESIGN | `docs/product/architecture/brief.md` updated for this feature |
| DEVOPS | `docs/product/kpi-contracts.yaml` has contracts for this feature |
| DISTILL | `docs/features/{id}/acceptance-tests.feature` exists AND `tests/acceptance/{id}/` has feature files |
| DELIVER | `docs/features/{id}/roadmap.json` with all steps at COMMIT/PASS |

### Old model (archived features)

| Wave | Complete When |
|------|--------------|
| DISCOVER | `discover/problem-validation.md` AND `discover/lean-canvas.md` exist |
| DISCUSS | `discuss/user-stories.md` exists |
| DESIGN | `design/architecture-design.md` exists |
| DEVOPS | `devops/platform-architecture.md` exists |
| DISTILL | `distill/test-scenarios.md` exists AND `tests/acceptance/{id}/` has feature files |
| DELIVER | `deliver/execution-log.json` with all steps at COMMIT/PASS |

## Wave Summary Table

| Wave | Agent | SSOT Update | Feature Delta | Completion Gate |
|------|-------|-------------|---------------|-----------------|
| DISCOVER | product-discoverer | `jobs.yaml` | — | Validated job exists |
| DIVERGE | nw-diverger | `jobs.yaml` | `recommendation.md` | Recommendation + peer review |
| DISCUSS | product-owner | `journeys/{name}.yaml` | `user-stories.md` | User stories + DoR passed |
| DESIGN | solution-architect | `architecture/brief.md` + ADRs | `wave-decisions.md` | Architecture with C4 diagrams |
| DEVOPS | platform-architect | `kpi-contracts.yaml` | — | KPI contracts defined |
| DISTILL | acceptance-designer | — | `acceptance-tests.feature` | Feature files + step definitions |
| DELIVER | software-crafter | code | `roadmap.json` | All steps COMMIT/PASS |
| FINALIZE | platform-architect | — | — | Evolution doc committed |

## Handoff Chain

Each wave reads SSOT first, then prior wave delta:

```
DISCOVER → DIVERGE reads jobs.yaml (validated problems + opportunities)
DIVERGE  → DISCUSS reads recommendation.md + jobs.yaml (selected direction + job)
DISCUSS  → DESIGN reads journeys/*.yaml + user-stories.md (experience + requirements)
DESIGN   → DEVOPS reads architecture/brief.md + kpi-contracts.yaml (components + measurement)
DEVOPS   → DISTILL reads all 3 SSOT dimensions (journeys + architecture + kpi-contracts)
DISTILL  → DELIVER reads acceptance-tests.feature + roadmap.json (specs + plan)
```

After DELIVER completes and all tests pass, `/nw-finalize` archives a summary to `docs/evolution/`.
