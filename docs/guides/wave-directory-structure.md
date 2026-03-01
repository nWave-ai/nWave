# Wave Directory Structure

How nWave organizes artifacts across the six-wave pipeline.

## The Rule

Every wave writes its output under a single, predictable path:

```
docs/feature/{feature-id}/{wave}/
```

Where `{feature-id}` is a kebab-case identifier derived from the feature description (see [Feature ID Derivation](#feature-id-derivation) below).

## Directory Layout

```
docs/feature/{feature-id}/
├── discover/                 # DISCOVER wave — evidence & validation
│   ├── problem-validation.md
│   ├── opportunity-tree.md
│   ├── solution-testing.md
│   ├── lean-canvas.md
│   └── interview-log.md
│
├── discuss/                  # DISCUSS wave — JTBD, journeys, requirements
│   ├── jtbd-job-stories.md
│   ├── jtbd-four-forces.md
│   ├── jtbd-opportunity-scores.md
│   ├── journey-{name}-visual.md
│   ├── journey-{name}.yaml
│   ├── journey-{name}.feature
│   ├── shared-artifacts-registry.md
│   ├── requirements.md
│   ├── user-stories.md
│   ├── acceptance-criteria.md
│   └── dor-checklist.md
│
├── design/                   # DESIGN wave — architecture, technology, components, data
│   ├── architecture-design.md (mandatory — C4 diagrams in Mermaid format)
│   ├── technology-stack.md
│   ├── component-boundaries.md
│   └── data-models.md
│
├── devops/                   # DEVOPS wave — infrastructure, CI/CD, observability, deployment
│   ├── platform-architecture.md
│   ├── ci-cd-pipeline.md
│   ├── observability-design.md
│   ├── monitoring-alerting.md
│   ├── infrastructure-integration.md (if existing infrastructure)
│   ├── branching-strategy.md
│   └── continuous-learning.md (if applicable)
│
├── distill/                  # DISTILL wave — acceptance test design (summary only)
│   ├── test-scenarios.md (summary of planned test coverage)
│   ├── walking-skeleton.md (minimal user journey for E2E wiring)
│   └── acceptance-review.md (peer review results & DoD validation)
│
└── deliver/                  # DELIVER wave — TDD execution
    ├── roadmap.json
    ├── execution-log.json
    ├── .develop-progress.json
    └── mutation/
        └── mutation-report.md (when mutation testing is enabled via rigor profile)
```

## Cross-Feature Artifacts

Acceptance test files and cross-feature documents live outside the per-feature tree:

| Location | Content | Why | Written By |
|----------|---------|-----|-----------|
| `tests/{test-type}/{feature-id}/acceptance/` | Acceptance test files (.feature, step definitions) | Actual executable tests, not documentation | acceptance-designer (DISTILL) |
| `CLAUDE.md` (project root) | Development paradigm (OOP or Functional), mutation testing strategy | Shared across all features in project | solution-architect (DESIGN), platform-architect (DEVOPS) |
| `docs/adrs/` | Architecture Decision Records | Cross-feature decisions affecting multiple features | solution-architect (DESIGN) |
| `docs/evolution/` | Post-completion archives | Centralized history of completed features | platform-architect (/nw:finalize) |

## Feature ID Derivation

When you run `/nw:new`, `/nw:deliver`, or any wave command, nWave derives a feature ID from your description:

1. Strip common prefixes: "implement", "add", "create", "build"
2. Remove English stop words: "a", "the", "to", "for", "with", "and", "in", "on", "of"
3. Convert to kebab-case (lowercase, hyphens)
4. Limit to 5 segments maximum

**Examples:**
- "Add rate limiting to the API gateway" → `rate-limiting-api-gateway`
- "OAuth2 upgrade" → `oauth2-upgrade`
- "Implement real-time notifications with WebSocket" → `real-time-notifications-websocket`

## Acceptance Test Directory Structure

Actual executable acceptance tests are NOT in `distill/`. They are organized by test type in the `tests/` directory:

```
tests/
├── acceptance/
│   └── {feature-id}/
│       └── {scenario-name}.feature     (Gherkin feature files)
│       ├── step_definitions.py         (Given/When/Then implementations)
│       ├── fixtures/
│       └── conftest.py                 (pytest configuration for this feature)
```

This separation is critical: `docs/feature/{feature-id}/distill/` contains design summaries and peer review records, while `tests/acceptance/{feature-id}/` contains the actual executable specifications. The acceptance-designer (DISTILL wave) designs the tests, but implementation goes to `tests/` where they become part of the executable test suite.

## Wave Detection

`/nw:continue` uses these rules to detect progress:

| Wave | Complete When |
|------|--------------|
| DISCOVER | `discover/problem-validation.md` AND `discover/lean-canvas.md` exist |
| DISCUSS | `discuss/requirements.md` AND `discuss/user-stories.md` exist |
| DESIGN | `design/architecture-design.md` exists |
| DEVOPS | `devops/platform-architecture.md` exists |
| DISTILL | `distill/test-scenarios.md` exists AND `tests/acceptance/{feature-id}/` has feature files |
| DELIVER | `deliver/execution-log.json` with all steps at COMMIT/PASS |

## Wave Summary Table

Quick reference for each wave's primary deliverable, location, and completion gate:

| Wave | Agent | Primary Deliverable | Location | Completion Gate |
|------|-------|---------------------|----------|-----------------|
| DISCOVER | product-discoverer | Problem validation + lean canvas | `docs/feature/{id}/discover/` | `problem-validation.md` + `lean-canvas.md` exist |
| DISCUSS | product-owner | User stories + requirements + journey artifacts | `docs/feature/{id}/discuss/` | `requirements.md` + `user-stories.md` + acceptance criteria |
| DESIGN | solution-architect | Architecture design with C4 diagrams + ADRs | `docs/feature/{id}/design/` + `docs/adrs/` | `architecture-design.md` exists with Mermaid C4 diagrams |
| DEVOPS | platform-architect | Platform architecture + CI/CD + observability + monitoring | `docs/feature/{id}/devops/` | `platform-architecture.md` + `ci-cd-pipeline.md` + `observability-design.md` exist |
| DISTILL | acceptance-designer | Acceptance test design + feature files in Gherkin | `docs/feature/{id}/distill/` + `tests/acceptance/{id}/` | `.feature` files exist with step definitions implemented |
| DELIVER | software-crafter | Working code + passing tests (unit + acceptance + integration) | `src/` + `tests/` | `deliver/execution-log.json` with all steps at COMMIT/PASS |
| FINALIZE | platform-architect | Feature completion archive + cleanup | `docs/evolution/YYYY-MM-DD-{id}.md` | Feature directory cleaned, evolution document committed |

## Handoff Chain

Each wave reads from the previous wave's directory:

```
DISCOVER → DISCUSS reads discover/ (problem + opportunity + viability)
DISCUSS  → DESIGN reads discuss/ (requirements + journey artifacts)
DESIGN   → DEVOPS reads design/ (architecture + technology stack + ADRs)
DEVOPS   → DISTILL reads devops/ + design/ (infrastructure design informs test environment)
DISTILL  → DELIVER reads distill/ + design/ (acceptance tests + architecture)
DELIVER  → reads deliver/ (roadmap + execution log for resumption)
```

After DELIVER completes and all tests pass, `/nw:finalize` archives a summary to `docs/evolution/`.

## Critical Distinctions

### DISTILL Wave Output vs Test Files
**DISTILL deliverables** (`docs/feature/{id}/distill/`): Design documents, peer review records, test scenario summaries. These are documentation of WHAT tests to write.

**Actual test code** (`tests/acceptance/{id}/`): Executable .feature files and step definitions. Written by acceptance-designer but stored in executable test suite location. These are the tests themselves.

This distinction matters: you can review DISTILL documentation before tests are executable, and the tests live alongside other test code for CI/CD integration.

### DESIGN Wave Output Structure
**solution-architect** produces: `docs/feature/{id}/design/architecture-design.md` (must include C4 diagrams in Mermaid), `technology-stack.md`, `component-boundaries.md`, `data-models.md`, plus ADRs in `docs/adrs/`. Also documents development paradigm (OOP or Functional) in project `CLAUDE.md`.

### DEVOPS Wave Output Structure
**platform-architect** produces: `docs/feature/{id}/devops/platform-architecture.md`, `ci-cd-pipeline.md`, `observability-design.md`, `monitoring-alerting.md`, `branching-strategy.md`, plus conditional files `infrastructure-integration.md` (if existing infra) and `continuous-learning.md` (if applicable). Also configures mutation testing strategy in project `CLAUDE.md` (Decision 9 of DEVOPS workflow).

Note: DESIGN produces software architecture and technology decisions. DEVOPS produces operational infrastructure, CI/CD pipelines, observability, and deployment strategy for that architecture.
