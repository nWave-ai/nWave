# nw-solution-architect-reviewer

Reviews durable architecture decisions for evidence, reuse, boundaries, cross-layer algebra, residual stress behavior, test substrate, and absence of drift.

**Wave:** Other
**Model:** sonnet
**Max turns:** 40
**Tools:** Read, Glob, Grep, Bash, Write, SendMessage

## Preloaded skills

- [nw-algebraic-design-protocol](../skills/nw-algebraic-design-protocol.md) — Load when designing a representation, equality or laws, when a law has exceptions, or when a representation change must preserve meaning.
- [nw-certainty-by-construction](../skills/nw-certainty-by-construction.md) — Load when a state must be unrepresentable, evidence must carry instead of a boolean, or a representation change must preserve meaning - redirect plus the byte-preservation and structural-owner rules.
- [nw-code-analysis-port](../skills/nw-code-analysis-port.md) — KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact.
- [nw-code-craftsmanship](../skills/nw-code-craftsmanship.md) — Load when writing or changing production code in craft; per-unit rules, failure messages, security, recovery, performance, honest closing statement.
- [nw-product-value-slicing](../skills/nw-product-value-slicing.md) — Product-owner foundation for slicing value — elephant carpaccio thin vertical slices, one walking skeleton per feature (not per slice), feature identity from user/product authority, JTBD/domain language framing. Consult when decomposing a feature into independently observable increments.
- [nw-sar-critique-dimensions](../skills/nw-sar-critique-dimensions.md) — Architecture quality critique dimensions for peer review. Load when performing architecture document reviews.
- [nw-type-level-design](../skills/nw-type-level-design.md) — Load when an invalid state, call or transition must be impossible to build, or a validation must carry evidence to the next operation.
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
