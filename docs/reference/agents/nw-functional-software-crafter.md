# nw-functional-software-crafter

Implements the functional change for one ready ordered batch.

**Wave:** Other
**Model:** claude-opus-5
**Max turns:** 40
**Tools:** Read, Write, Edit, Bash, SendMessage

## Preloaded skills

- [nw-certainty-by-construction](../skills/nw-certainty-by-construction.md) — Load when a state must be unrepresentable, evidence must carry instead of a boolean, or a representation change must preserve meaning - redirect plus the byte-preservation and structural-owner rules.
- [nw-code-craftsmanship](../skills/nw-code-craftsmanship.md) — Load when writing or changing production code in craft; per-unit rules, failure messages, security, recovery, performance, honest closing statement.
- [nw-code-design-fp](../skills/nw-code-design-fp.md) — FP code-design SSOT — the WHAT-to-design catalog (algebra-driven design, domain modelling with types, railway/error-track isolation) shared by the solution architect (design-time) and the functional crafter (execution-time).
- [nw-fp-principles](../skills/nw-fp-principles.md) — Core functional programming thinking patterns and type system foundations, language-agnostic
- [nw-type-level-design](../skills/nw-type-level-design.md) — Load when an invalid state, call or transition must be impossible to build, or a validation must carry evidence to the next operation.
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
