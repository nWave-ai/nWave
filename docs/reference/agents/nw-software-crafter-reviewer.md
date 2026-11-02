# nw-software-crafter-reviewer

Independently reviews the whole candidate with captured native evidence.

**Wave:** Other
**Model:** claude-opus-5
**Max turns:** 40
**Tools:** Read, Bash, Write, SendMessage

## Preloaded skills

- [nw-certainty-by-construction](../skills/nw-certainty-by-construction.md) — Turn a stable layer claim (domain, application, adapter, or infrastructure) into a construction boundary so the invalid state cannot be built, and state honestly what remains unguarded. Use when a requirement says an invalid state or transition must not occur, when values need a canonical form, or when a rewrite/cache/optimisation must preserve meaning. Complements nw-fp-domain-modeling, which shows the encodings; this decides whether to encode, how strong the claim really is, and what obligation is left over.
- [nw-code-craftsmanship](../skills/nw-code-craftsmanship.md) — Universal OO/FP craftsmanship foundation — domain-language naming, small cohesive units, semantic DRY/SSOT, reuse-before-new, one owner per rule/config/fact, prefactoring before new behavior, ports/adapters for testability. Consult before writing or reviewing any unit of code, either paradigm.
- [nw-code-design-fp](../skills/nw-code-design-fp.md) — FP code-design SSOT — the WHAT-to-design catalog (algebra-driven design, domain modelling with types, railway/error-track isolation) shared by the solution architect (design-time) and the functional crafter (execution-time).
- [nw-code-design-oo](../skills/nw-code-design-oo.md) — OO code-design SSOT — the WHAT-to-design anti-smell catalog (Object Calisthenics, RPP smell taxonomy, effect isolation) shared by the solution architect (design-time) and the crafter (execution-time).
- [nw-sc-review-dimensions](../skills/nw-sc-review-dimensions.md) — Reviewer critique dimensions for peer review - implementation bias detection, test quality validation, completeness checks, and priority validation
- [nw-type-level-design](../skills/nw-type-level-design.md) — Design or review evidence-preserving APIs that model invalid states, state transitions, capabilities, and trusted construction proportionately to the target language.
- [nw-typesafe-system-one](../skills/nw-typesafe-system-one.md) — Use Jev System One for every supported, authorized semantic judgment when available: relevance selection, handoff preflight, evidence mapping, finding clustering, and confidence-gated escalation.
