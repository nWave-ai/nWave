# nw-solution-architect

Use for application architecture decisions, boundaries, reuse and evidence-backed design.

**Wave:** Other
**Model:** claude-opus-5
**Max turns:** 40
**Tools:** Read, Write, Glob, Grep, Bash, SendMessage

## Commands

- [`/nw-design`](../commands/index.md)
- [`/nw-diagram`](../commands/index.md)

## Preloaded skills

- [nw-algebraic-design-protocol](../skills/nw-algebraic-design-protocol.md) — Load when designing a representation, equality or laws, when a law has exceptions, or when a representation change must preserve meaning.
- [nw-certainty-by-construction](../skills/nw-certainty-by-construction.md) — Load when a state must be unrepresentable, evidence must carry instead of a boolean, or a representation change must preserve meaning - redirect plus the byte-preservation and structural-owner rules.
- [nw-code-analysis-port](../skills/nw-code-analysis-port.md) — KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact.
- [nw-code-craftsmanship](../skills/nw-code-craftsmanship.md) — Load when writing or changing production code in craft; per-unit rules, failure messages, security, recovery, performance, honest closing statement.
- [nw-cross-cutting-invariants](../skills/nw-cross-cutting-invariants.md) — Cross-cutting normative invariants — routing core for the software/model boundary doctrine, gate/construction principles and on-demand knowledge lenses. Cite clause ids; never re-declare.
- [nw-design](../skills/nw-design.md) — Establishes durable architecture, reuse, boundaries, cross-layer algebra, residual stress behavior, paradigm, and prefactoring decisions for deterministic minimal handover construction.
- [nw-human-collaboration](../skills/nw-human-collaboration.md) — Collaborate with the human to refine product, architecture and operational decisions before implementation; preserve explicit delegation preferences.
- [nw-product-value-slicing](../skills/nw-product-value-slicing.md) — Product-owner foundation for slicing value — elephant carpaccio thin vertical slices, one walking skeleton per feature (not per slice), feature identity from user/product authority, JTBD/domain language framing. Consult when decomposing a feature into independently observable increments.
- [nw-property-based-testing](../skills/nw-property-based-testing.md) — Load when a design law holds over a broad input, state or sequence domain and needs a generated property test.
- [nw-test-design-mandates-composition-contract](../skills/nw-test-design-mandates-composition-contract.md) — Stub - every test rule lives in nw-test-design-mandates; nothing to load here.
- [nw-type-level-design](../skills/nw-type-level-design.md) — Load when an invalid state, call or transition must be impossible to build, or a validation must carry evidence to the next operation.
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
