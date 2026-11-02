# nw-acceptance-designer

Authors the public executable oracle when required.

**Wave:** Other
**Model:** claude-opus-5
**Max turns:** 40
**Tools:** Read, Write, Edit, Bash, SendMessage

## Commands

- [`/nw-distill`](../commands/index.md)

## Preloaded skills

- [nw-at-completeness-check](../skills/nw-at-completeness-check.md) — Verify that one minimal oracle falsifies every declared delivery obligation without checklist ceremony or duplicate tests.
- [nw-bdd-methodology](../skills/nw-bdd-methodology.md) — BDD patterns for acceptance test design - Given-When-Then as a language-neutral specification style, scenario writing rules, realization in the project's incumbent native scenario syntax (Python pytest-bdd binding labelled), anti-patterns, and living documentation
- [nw-code-analysis-port](../skills/nw-code-analysis-port.md) — KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact.
- [nw-distill-prior-wave-reading](../skills/nw-distill-prior-wave-reading.md) — Reads and reconciles durable product, architecture, and platform authorities before DISTILL compiles an executable oracle.
- [nw-product-value-slicing](../skills/nw-product-value-slicing.md) — Product-owner foundation for slicing value — elephant carpaccio thin vertical slices, one walking skeleton per feature (not per slice), feature identity from user/product authority, JTBD/domain language framing. Consult when decomposing a feature into independently observable increments.
- [nw-property-based-testing](../skills/nw-property-based-testing.md) — Property-based testing strategies (PBT — ACTIVE, authored by the acceptance-designer during DISTILL), shrinking, PBT+TDD integration.
- [nw-tdd-methodology-paradigm](../skills/nw-tdd-methodology-paradigm.md) — Native contract-driven unit and acceptance testing: generative broad laws, finite examples, public-state preservation and real-boundary evidence.
- [nw-tdd-methodology-pbt-deep](../skills/nw-tdd-methodology-pbt-deep.md) — Deep property-based-testing mechanics (Hebert) - stateful PBT command-precondition anti-patterns (A13/P6), the four property-finding strategies, the two shrinking mechanisms, and targeted/search-based PBT with its hard limitations
- [nw-tdd-methodology-port-to-port](../skills/nw-tdd-methodology-port-to-port.md) — What a test asserts on and where it enters - port-to-port discipline at all test levels, the layer-specific Universe, refactoring-resilience, and the hexagonal per-layer testing strategy
- [nw-tdd-methodology-test-doubles](../skills/nw-tdd-methodology-test-doubles.md) — Choosing and building a test double - Meszaros taxonomy, classical-vs-mockist verification, the mock-only-at-port-boundaries policy, and the contract that every InMemory double must validate inputs like the real adapter
- [nw-test-design-mandates](../skills/nw-test-design-mandates.md) — Design mandates for acceptance tests - hexagonal boundary, business language abstraction, user journey completeness, pure function extraction, 3 Pillars (domain language / chained narrative / production composition), and the layered ATD discipline (Universe-bound assertion, layer-dependent PBT mode, two-tier acceptance, example-based sad paths). Lean recomposing core - routes to three narrow mandate modules.
- [nw-test-design-mandates-composition-contract](../skills/nw-test-design-mandates-composition-contract.md) — Composition-root authoring-contract mandates for acceptance tests — SSOT + Zero Duplication via Types + Services + DSL, Driving-Port-Only Boundary (Farley four-layer protocol-driver contract, fixture-theater/tautological-test anti-pattern), Contract Shape Classification (@in-memory/@real-io tag-vs-composition), and Dormant-Seam Reconciliation (AT drives the DESIGN-declared seam, not the new component). Consult while composing the AT's driving surface, structuring step/type/service code, and tagging the contract shape. Canonical definitions; SSOT for these mandates.
- [nw-test-design-mandates-scenario-design](../skills/nw-test-design-mandates-scenario-design.md) — Scenario-design mandates for acceptance tests — Hexagonal Boundary Enforcement (drive through driving ports, never internals), Business Language Abstraction (three abstraction layers), User Journey Completeness, Pure Function Extraction Before Fixtures, Algebraic Analysis Before the Scenario (name the law, find its narrowest surface, declare every gated input, prove the scenario can fail), the 3 Pillars style backbone, and Walking Skeleton Strategy. Consult while shaping or judging a scenario's boundary, language, journey completeness, and fixture strategy. Canonical definitions; SSOT for these mandates.
- [nw-test-organization-conventions](../skills/nw-test-organization-conventions.md) — Test directory structure patterns by architecture style, language conventions, naming rules, and fixture placement. Decision tree for selecting test organization strategy.
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
