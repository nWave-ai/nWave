# nw-ddd-architect-reviewer

Use for reviewing DDD domain models. Validates bounded context boundaries, aggregate design, context mapping, ES/CQRS recommendations, and ubiquitous language consistency.

**Wave:** DESIGN
**Model:** sonnet
**Max turns:** 40
**Tools:** Read, Glob, Grep, Task, Bash, Skill, Write, SendMessage

## Preloaded skills

- [nw-code-analysis-port](../skills/nw-code-analysis-port.md) — KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact.
- [nw-ddd-architect](../skills/nw-ddd-architect.md) — DDD architect design-time mandates — the Fixture-Fanout Enumeration Mandate for shared-substrate per-caller migration (enumerate production callers plus fixture sites plus atomic bundle scope, mechanically enforced) that both the ddd-architect and its reviewer load by name
- [nw-ddd-strategic](../skills/nw-ddd-strategic.md) — Strategic DDD — bounded context discovery, context mapping patterns, subdomain classification, ubiquitous language, and organizational alignment
- [nw-ddd-tactical](../skills/nw-ddd-tactical.md) — Tactical DDD — aggregate design rules, entities, value objects, domain events, repositories, domain services, and anti-pattern detection
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
