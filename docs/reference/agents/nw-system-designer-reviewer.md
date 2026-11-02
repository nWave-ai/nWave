# nw-system-designer-reviewer

Use to review system design architecture outputs. Validates trade-off analysis, estimation accuracy, pattern applicability, SPOF detection, and scalability claims. Pairs with system-designer.

**Wave:** DESIGN
**Model:** sonnet
**Max turns:** 40
**Tools:** Read, Glob, Grep, Task, Bash, Skill, Write, SendMessage

## Preloaded skills

- [nw-code-analysis-port](../skills/nw-code-analysis-port.md) — KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact.
- [nw-sd-framework](../skills/nw-sd-framework.md) — 4-step system design framework with back-of-envelope estimation, scaling ladder, and common pitfalls
- [nw-sd-patterns](../skills/nw-sd-patterns.md) — Core distributed systems patterns - load balancing, caching, sharding, consistent hashing, message queues, rate limiting, CDN, Bloom filters, ID generation, replication, conflict resolution, CAP theorem
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
