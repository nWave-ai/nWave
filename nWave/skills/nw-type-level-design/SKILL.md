---
name: nw-type-level-design
description: Load when an invalid state, call or transition must be impossible to build, or a validation must carry evidence to the next operation.
user-invocable: false
disable-model-invocation: true
---

# Invalid states unrepresentable

## Decide before writing

1. State the rule in one sentence: which state is excluded, who could build it, what harm follows. Name the admitted input, constructor, consumer and public observation.
2. Encode only stable, local rules. Volatile policy, time, I/O, concurrency and untrusted input stay checked at their owning boundary.
3. Use the least powerful encoding: a named sum for alternatives, a record for required parts, an opaque value with a smart constructor, a result carrying reason and value. Use a state-indexed API only for few, stable states central to the contract.
4. Replace each flag, pair of optionals, or must-be-non-empty collection with distinct types, a choice type or a non-empty type.
5. Give every intended value a construction path from admitted input to a public observation. A construction cycle needs a named bootstrap.
6. Where several semantically equal values exist, prefer one canonical representation built into the constructor. If several stay valid, state the equality and that normalization preserves it.

## Write

1. Enforce the rule in the constructor or type, not at each use site.
2. Expose no public raw constructor, setter or deserializer that builds what the smart constructor refuses; deserializers call the smart constructor.
3. A decision returns its evidence: success carries the witness, failure carries the reason. No bare boolean or flag where the caller needs either. Remove a boolean validator left beside the evidence path.
4. An operation that accepts only validated input takes the validator's evidence type as its parameter and does not re-validate inside.
5. Return evidence at the smallest unit the consumer needs; independent failures stay separate until final assembly.
6. Decide every semantic refusal on a pure description before any issuance, write or render; a refusal leaves prior state intact and runs none of those activities.
7. Tests: one observes the refusal with its reason through the public surface the design declares; one builds a valid value through the public producer. Add them in the owned test paths when the oracle does not cover them; a throwaway script is not a test.

## State the claim honestly

- Claim the strength the repository's own checker gives: proof assistant = follows from checked definitions; strong static types = blocked on typed paths; gradual typing with the checker in verification = rejected on annotated paths; mainstream OO/FP = construction centralised, predicate not proved; no checker = checked at runtime boundaries.
- A wrapper the runtime can build around an invalid value is not a guarantee.
- Name each bypass the change leaves open (deserialization, casts, `Any`, reflection, outside writers, foreign code) and keep its runtime check.
- Construction never establishes intent, authorization, time-dependent policy, cross-aggregate consistency, external API behaviour, availability. Do not claim them.
- Safety (excludes the state), inhabitation (a valid value exists), reachability and liveness are separate claims; claim only what a test or checker shows.
- A refuted rule is a representation problem: change the type, do not add a guard over it.

## Self-check before recording the step

1. Each stable local rule is enforced in a constructor or type.
2. No public path builds what the smart constructor refuses.
3. No boolean result where a witness or reason is needed.
4. Validated-only operations take the evidence type and do not re-check.
5. No flag, optional pair or empty-able collection remains for a must-hold rule.
6. Each constructor has a refusal test with reason and a valid-build test.
7. Each valid type can be built from admitted input and observed publicly.
8. The closing statement claims no more than the checker shows and lists open bypasses.

## Advanced Haskell/GHC

For GHC-targeted GADTs, DataKinds, type families, roles or singletons, read [advanced Haskell design](references/advanced/haskell-type-level-design.md), then [technique selection](references/advanced/technique-selection.md) and [ergonomics and compatibility](references/advanced/ergonomics-and-compatibility.md), only when the target and its compiler range make them a concrete option.
