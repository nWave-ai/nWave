# What's New in nWave v3.5

## DIVERGE Wave

A new optional wave between DISCOVER and DISCUSS. Run `/nw-diverge` to explore multiple design directions before converging on one.

**What it does**: JTBD analysis, competitive research, structured brainstorming (SCAMPER + HMW), and taste evaluation (DVF + Apple/Jobs design principles). Produces a scored recommendation with dissenting case.

**When to use**: New products, pivots, or any time multiple approaches are viable and you haven't chosen one yet.

**When to skip**: Bugfixes, refactoring, or features with a clear direction.

See the [DIVERGE Wave Guide](../diverge-wave-guide/) for details.

## DESIGN Wave: 3 Specialist Architects

`/nw-design` now routes to the right architect based on what you're designing:

| Scope | Architect | Focus |
|-------|-----------|-------|
| System / infrastructure | nw-system-designer (Titan) | Scalability, distributed patterns, trade-offs |
| Domain / bounded contexts | nw-ddd-architect (Hera) | DDD, Event Modeling, ES/CQRS |
| Application / components | nw-solution-architect | Hexagonal architecture, tech stack, C4 |

All three support two interaction modes: **Guide me** (interactive questions) or **Propose** (autonomous analysis + options).

## SSOT Document Model

Features no longer produce ~26 documents in per-wave subdirectories. Instead:

- **Product SSOT** (`docs/product/`) holds living documents that represent the current state of the product: vision, validated jobs, journeys, architecture, KPI contracts
- **Feature Delta** (`docs/features/{id}/`) holds max 6 files describing what this feature changes

Each wave reads the SSOT, produces its delta, and updates the SSOT. Documents are never duplicated across features.

See [Understanding the SSOT Model](../understanding-ssot-model/) for the full explanation, or [Migrating to the SSOT Model](../migrating-to-ssot-model/) for the step-by-step upgrade guide.

## Document Rationalization

4 documents eliminated (never produced):
- `acceptance-criteria.md` — superseded by executable `acceptance-tests.feature` in DISTILL
- `requirements.md` — merged into `user-stories.md` as `## System Constraints`
- `prioritization.md` — merged into `story-map.md` as `## Priority Rationale`
- `journey.feature` — Gherkin embedded in `journey.yaml`, extracted by DISTILL

## DISTILL as Conjunction Point

DISTILL now reads all three SSOT dimensions:
- **Journeys** — behavioral scenarios + failure modes
- **Architecture** — driving ports for `@driving_port` tagged scenarios
- **KPI contracts** — observability for `@kpi` tagged scenarios (soft gate)

Scope is bounded by the feature delta — DISTILL tests what this feature changes, not the entire SSOT.

## Wave Routing

Waves are a graph, not a pipeline. Work enters at different points:

| Work type | Entry point |
|-----------|------------|
| New product | DISCOVER |
| Brownfield feature | DIVERGE |
| Feature on known journey | DISCUSS |
| Technical story / refactoring | DESIGN |
| Bug fix (cause known) | DISTILL |
| Infrastructure | DEVOPS |

DISTILL → DELIVER is always the terminal pair. See [Wave Routing Guide](../wave-routing-and-entry-points/).
