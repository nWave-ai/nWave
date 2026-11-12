---
name: nw-algebraic-design-protocol
description: Load when designing a representation, equality or laws, when a law has exceptions, or when a representation change must preserve meaning.
---

# Observations, equality, laws

## Decide before writing

1. List what a user can observe: each observation, its result type, and what it cannot distinguish. Do this before any constructor.
2. Define equality `x ≈ y` as agreement under those observations, not structural equality of the representation. For a command that authors only part of an aggregate, compare that part only.
3. Check that the observations tell the plausible wrong implementation apart from the right one; if not, add the missing observation or stimulus, not more examples.
4. Keep persistence, tree shape, cache and optimisation out of the public operations and observations. Put canonical reductions in smart constructors.
5. Build a deliberately obvious reference encoding first.

## Write

1. After each constructor, write at least one law relating it to an observation or to another constructor, and a test for it.
2. Test each law with generated inputs (or a table for a finite domain) through the public surface, such that a plausible wrong implementation fails it. State generator reach and size bounds.
3. A law with ignored arguments, many exceptions or flags means two fused concepts; split them before choosing a representation.
4. When a law fails, the carrier usually cannot express it (order-insensitive composition over an ordered list). Replace the carrier or retract the law. Never add a special case or guard over an unchanged representation to pass the input while the law stays false.
5. Before adopting a replacement carrier, run the stated laws against the reference encoding over generated inputs that include the refuting case; confirm every consumed observation survives (an unordered carrier must still give the deterministic order a consumer needs).
6. Keep a counterexample that expresses required behaviour as a regression test, with its refuting input. Record a tempting but false law as refuted, not deleted.
7. When a counterexample survives a repair, restate the family law and enumerate its interpreters before patching another instance.
8. When changing a representation, state old and new observation sets and the equivalence claim first. Then test encode-then-decode and decode-then-encode at the declared equality against the independent reference, including the input that refuted the old one. For a mapping over an operation, test identity and composition preservation.
9. Name the runtime operation and observation for each model operation. If concrete activity (an attempted payment, an issued id) is invisible to the model, extend the observation or narrow the claim; a model proof alone is not a runtime guarantee, so say what the model does not cover.
10. Passing generated checks is evidence, not proof; say which you have.

## Self-check before recording the step

1. Observations are listed and equality is defined by them.
2. Every constructor appears in a law tested against an observation.
3. Each law test fails on a plausible wrong implementation.
4. No special case hides a false law; the carrier was replaced or the law retracted.
5. Representation changes have round-trip tests against an independent reference.
6. No persistence, tree shape or cache leaks into the public algebra.
7. Observations nobody consumes are removed.
