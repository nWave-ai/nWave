# nw-ddd-architect

Use for DESIGN wave domain modeling. Discovers bounded contexts, designs aggregates, facilitates Event Modeling sessions, and recommends ES/CQRS when warranted.

**Wave:** DESIGN
**Model:** sonnet
**Max turns:** 45
**Tools:** Read, Glob, Grep, Bash, Task, Skill, Write, SendMessage

## Commands

- [`/nw-design`](../commands/index.md)

## Preloaded skills

- [nw-code-analysis-port](../skills/nw-code-analysis-port.md) — KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact.
- [nw-cross-cutting-invariants](../skills/nw-cross-cutting-invariants.md) — Cross-cutting normative invariants — routing core for the software/model boundary doctrine, gate/construction principles and on-demand knowledge lenses. Cite clause ids; never re-declare.
- [nw-ddd-architect](../skills/nw-ddd-architect.md) — DDD architect design-time mandates — the Fixture-Fanout Enumeration Mandate for shared-substrate per-caller migration (enumerate production callers plus fixture sites plus atomic bundle scope, mechanically enforced) that both the ddd-architect and its reviewer load by name
- [nw-ddd-event-modeling](../skills/nw-ddd-event-modeling.md) — Event Modeling facilitation technique — brainstorm events, identify commands and views, define aggregate boundaries, write Given-When-Then specifications
- [nw-ddd-eventsourcing](../skills/nw-ddd-eventsourcing.md) — Event Sourcing and CQRS as DDD implementation patterns — when to use, aggregate event streams, projections, snapshots, sagas, upcasting, conflict resolution
- [nw-ddd-strategic](../skills/nw-ddd-strategic.md) — Strategic DDD — bounded context discovery, context mapping patterns, subdomain classification, ubiquitous language, and organizational alignment
- [nw-ddd-tactical](../skills/nw-ddd-tactical.md) — Tactical DDD — aggregate design rules, entities, value objects, domain events, repositories, domain services, and anti-pattern detection
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
