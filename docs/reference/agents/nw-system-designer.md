# nw-system-designer

Use for DESIGN wave infrastructure-level architecture. Designs distributed systems, scalability strategies, load balancing, caching, database sharding, message queues, back-of-envelope estimation, and trade-off analysis. Complements solution-architect (application-level) with infrastructure-level depth.

**Wave:** DESIGN
**Model:** sonnet
**Max turns:** 45
**Tools:** Read, Glob, Grep, Bash, Task, Skill, Write, SendMessage

## Commands

- [`/nw-design`](../commands/index.md)

## Preloaded skills

- [nw-code-analysis-port](../skills/nw-code-analysis-port.md) — KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact.
- [nw-cross-cutting-invariants](../skills/nw-cross-cutting-invariants.md) — Cross-cutting normative invariants — routing core for the software/model boundary doctrine, gate/construction principles and on-demand knowledge lenses. Cite clause ids; never re-declare.
- [nw-sd-case-studies](../skills/nw-sd-case-studies.md) — 25 real-world system design case studies condensed from Alex Xu's System Design Interview Vol 1 and 2 - requirements, architecture, deep dive insights, key takeaways
- [nw-sd-framework](../skills/nw-sd-framework.md) — 4-step system design framework with back-of-envelope estimation, scaling ladder, and common pitfalls
- [nw-sd-patterns](../skills/nw-sd-patterns.md) — Core distributed systems patterns - load balancing, caching, sharding, consistent hashing, message queues, rate limiting, CDN, Bloom filters, ID generation, replication, conflict resolution, CAP theorem
- [nw-sd-patterns-advanced](../skills/nw-sd-patterns-advanced.md) — Advanced distributed patterns - event sourcing, CQRS, saga, stream processing, append-only log, exactly-once delivery, sequencer, double-entry ledger, erasure coding, order book, watermarks
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
