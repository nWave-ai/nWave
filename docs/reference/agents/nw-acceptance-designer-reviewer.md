# nw-acceptance-designer-reviewer

Independently approves or finds defects in the consolidated public oracle.

**Wave:** Other
**Model:** claude-opus-5
**Max turns:** 40
**Tools:** Read, Bash, Write, SendMessage

## Preloaded skills

- [nw-ad-critique-dimensions](../skills/nw-ad-critique-dimensions.md) — Review dimensions for acceptance test quality - happy path bias, GWT compliance, business language purity, coverage completeness, walking skeleton user-centricity, priority validation, observable behavior assertions, traceability coverage, and walking skeleton boundary proof
- [nw-at-completeness-check](../skills/nw-at-completeness-check.md) — Verify that one minimal oracle falsifies every declared delivery obligation without checklist ceremony or duplicate tests.
- [nw-code-analysis-port](../skills/nw-code-analysis-port.md) — KNOWLEDGE — resolve code facts (who-calls-X / where-defined-or-read / call-graph / change-scope / file-atoms) through the vendor-neutral CLI `code-fact`, degrading LOUD through bundled adapters (AST, TextSearch). Trigger: any time an agent designs, writes, analyzes, or reviews code or tests and needs a structural code fact.
- [nw-product-value-slicing](../skills/nw-product-value-slicing.md) — Product-owner foundation for slicing value — elephant carpaccio thin vertical slices, one walking skeleton per feature (not per slice), feature identity from user/product authority, JTBD/domain language framing. Consult when decomposing a feature into independently observable increments.
- [nw-property-based-testing](../skills/nw-property-based-testing.md) — Load when a design law holds over a broad input, state or sequence domain and needs a generated property test.
- [nw-test-design-mandates](../skills/nw-test-design-mandates.md) — Load before writing, reviewing or timing any test - oracle, scenarios, assertions, fakes, names, budgets, walking skeleton.
- [nw-test-design-mandates-composition-contract](../skills/nw-test-design-mandates-composition-contract.md) — Stub - every test rule lives in nw-test-design-mandates; nothing to load here.
- [nw-test-design-mandates-scenario-design](../skills/nw-test-design-mandates-scenario-design.md) — Scenario-design mandates for acceptance tests — Hexagonal Boundary Enforcement (drive through driving ports, never internals), Business Language Abstraction (three abstraction layers), User Journey Completeness, Pure Function Extraction Before Fixtures, Algebraic Analysis Before the Scenario (name the law, find its narrowest surface, declare every gated input, prove the scenario can fail), the 3 Pillars style backbone, and Walking Skeleton Strategy. Consult while shaping or judging a scenario's boundary, language, journey completeness, and fixture strategy. Canonical definitions; SSOT for these mandates.
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
