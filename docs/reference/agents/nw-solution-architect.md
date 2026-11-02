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

- [nw-algebraic-design-protocol](../skills/nw-algebraic-design-protocol.md) — The METHOD for finding a design — name observations and equality before constructors, then follow any contradiction to the type or observation that causes it. Use when a design decision is contested, a law has exceptions, a census or model keeps producing wrong answers, or a representation change must preserve meaning. Complements nw-fp-algebra-driven-design, which catalogues the structures; this says how to arrive at one and what to do when it breaks.
- [nw-certainty-by-construction](../skills/nw-certainty-by-construction.md) — Turn a stable layer claim (domain, application, adapter, or infrastructure) into a construction boundary so the invalid state cannot be built, and state honestly what remains unguarded. Use when a requirement says an invalid state or transition must not occur, when values need a canonical form, or when a rewrite/cache/optimisation must preserve meaning. Complements nw-fp-domain-modeling, which shows the encodings; this decides whether to encode, how strong the claim really is, and what obligation is left over.
- [nw-code-analysis-port](../skills/nw-code-analysis-port.md) — KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact.
- [nw-code-craftsmanship](../skills/nw-code-craftsmanship.md) — Universal OO/FP craftsmanship foundation — domain-language naming, small cohesive units, semantic DRY/SSOT, reuse-before-new, one owner per rule/config/fact, prefactoring before new behavior, ports/adapters for testability. Consult before writing or reviewing any unit of code, either paradigm.
- [nw-cross-cutting-invariants](../skills/nw-cross-cutting-invariants.md) — Cross-cutting normative invariants — routing core for the software/model boundary doctrine, gate/construction principles and on-demand knowledge lenses. Cite clause ids; never re-declare.
- [nw-design](../skills/nw-design.md) — Establishes durable architecture, reuse, boundaries, cross-layer algebra, residual stress behavior, paradigm, and prefactoring decisions for deterministic minimal handover construction.
- [nw-human-collaboration](../skills/nw-human-collaboration.md) — Collaborate with the human to refine product, architecture and operational decisions before implementation; preserve explicit delegation preferences.
- [nw-product-value-slicing](../skills/nw-product-value-slicing.md) — Product-owner foundation for slicing value — elephant carpaccio thin vertical slices, one walking skeleton per feature (not per slice), feature identity from user/product authority, JTBD/domain language framing. Consult when decomposing a feature into independently observable increments.
- [nw-property-based-testing](../skills/nw-property-based-testing.md) — Property-based testing strategies (PBT — ACTIVE, authored by the acceptance-designer during DISTILL), shrinking, PBT+TDD integration.
- [nw-test-design-mandates-composition-contract](../skills/nw-test-design-mandates-composition-contract.md) — Composition-root authoring-contract mandates for acceptance tests — SSOT + Zero Duplication via Types + Services + DSL, Driving-Port-Only Boundary (Farley four-layer protocol-driver contract, fixture-theater/tautological-test anti-pattern), Contract Shape Classification (@in-memory/@real-io tag-vs-composition), and Dormant-Seam Reconciliation (AT drives the DESIGN-declared seam, not the new component). Consult while composing the AT's driving surface, structuring step/type/service code, and tagging the contract shape. Canonical definitions; SSOT for these mandates.
- [nw-type-level-design](../skills/nw-type-level-design.md) — Design or review evidence-preserving APIs that model invalid states, state transitions, capabilities, and trusted construction proportionately to the target language.
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
