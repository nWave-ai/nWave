---
name: nw-algebraic-design-protocol
description: The METHOD for finding a design — name observations and equality before constructors, then follow any contradiction to the type or observation that causes it. Use when a design decision is contested, a law has exceptions, a census or model keeps producing wrong answers, or a representation change must preserve meaning. Complements nw-fp-algebra-driven-design, which catalogues the structures; this says how to arrive at one and what to do when it breaks.
---

# Algebraic Design Protocol

`nw-fp-algebra-driven-design` catalogues structures; this finds a design and
traces a false law. Load both for a compositional core; load this alone for a
design that keeps giving wrong answers.

**nWave sequencing choice.** State observations/equality before an algebra;
this is project synthesis, not a universal ADD claim.

**Cross-layer authority (ADR-SSOT-002 §6a).** One language-agnostic procedure
for declared target-boundary layers: domain, application/ports, adapter/
integration, infrastructure/recovery. `targets[].boundary`/`contract-shape`
sets applicability without a persisted field. OO/FP catalogues are projections,
never competitors.

## 1. Observations and equality, before anything else

State what a user can meaningfully **observe**. Then define `x ≈ y` as agreement
under that observation set — never structural equality chosen because it was easy
to implement.

Inventory each observation, its result type, and **what it cannot distinguish**.
That last column is the one that pays: a Boolean result is usually too weak the
moment composition needs the remaining input or state.

If several observations repeat the same traversal, look for one more primitive
transition the others project from.

**Command-owned replay equality.** If a command authors only part of an
aggregate, compare that authored projection, not a fresh aggregate carrying
defaults for unrelated state. Replaying equal title/size after an independent
review change yields `Unchanged` and preserves that review; changing size still
counts as a change. Law: unrelated-state edits leave replay equality unchanged
and survive the replay. The ownership scope is part of the law—a producer that
owns the whole output still observes all of it. Exact projection/frame policy is
application synthesis from Sandy Maguire, *Algebra-Driven Design*, Reference
Material → Common Algebraic Components → Idempotency; Designing Algebras →
Tiles → Observations.

**Does the observation distinguish the plausible wrong implementation?** If not,
add the missing stimulus or observation, not merely more examples. Diagnostic
sets observe error equality; per-unit results/invocations observe availability;
protected-activity traces observe forbidden work. Generate a failed producer,
its dependent and an independently failing sibling—not only unrelated failures.
Expect the real producer/sibling errors and no dependent invocation with invented
input; a new public blocked-status type is not required just to observe skipping.
For a no-render-on-refusal claim, unchanged files cannot exclude discarded
rendering. Observe every activity the contract forbids: when it names ID
issuance, interning, rendering and writes, instrument each actual invocation
boundary, including discarded or failing calls, and assert zero for each on
refusal. A render-only spy cannot establish the other exclusions. For canonical
text, repeat actual retained text and observe identity.
These discriminators are application synthesis from Sandy Maguire,
*Algebra-Driven Design*, Designing Algebras → Tiles → Observations; Scavenger Hunt
→ Challenge Completion; Reference Material → Property-Based Testing →
Anti-pattern: Generating Non-Representative Terms.

## 2. Constructors one at a time, each with an equation

After adding a constructor, write at least one equation relating it to an
observation or an existing constructor. The web of equations IS the design.

A law with ignored arguments, many exceptions, or domain-specific flags signals a
**fused concept**. Split it before choosing a representation.

## 3. Follow a contradiction to the carrier — do not special-case it

This is the step that catches real defects, and the reason to load this skill
when something is already broken.

When a law fails, the cause is usually not the law. It is that the **carrier** —
the type you are observing through — cannot express the property. Order-insensitive
composition observed through an order-sensitive list is the textbook case.

Two honest resolutions: **replace the carrier**, or **retract the law**. Never
conceal the conflict with a special case, because a special case makes the model
agree with the data while still being wrong about the domain.

A replacement carrier is a claim until checked. Before proposing it, run the
stated laws against an obvious reference encoding of the new carrier, over
generated public inputs that include the refuting case, and keep that receipt
beside the counterexample. Check that each consumed observation survives: an
order-free carrier must still yield a deterministic order to every consumed
ordered-listing observation.

**A counterexample survived an earlier repair?** Restate the family law and
enumerate its interpreters before patching another instance. For schema/decoder
drift, include declared field kinds and unknown null/empty keys, then repair the
shared shape owner. Keep old and new witnesses; the family property must reject
the prior wrong interpretation. Application of Sandy Maguire, *Algebra-Driven
Design*, Designing Algebras → Scavenger Hunt → A Unified Observation; Reference
Material → Property-Based Testing → Anti-pattern: Not Generating All Constructors.

> **Worked anchor (nWave, 2026-08-06).** A census asked "is this MODULE live?"
> when liveness was a property of the VERB the module dispatched. The three verbs
> disagreed, so the answer came back for whichever one dominated the text.
> Measuring per-module was the wrong carrier, and no amount of scanning more
> surfaces would have fixed it — the fix was to change what the unit was. The
> unit comes from the SEMANTICS, not from the file system.

## 4. Keep the representation out of the public algebra

Persistence, tree shape, cache and optimisation are not part of the design.
Build a deliberately obvious reference encoding first; enforce canonical
reductions through smart constructors.

Generate values through the **public surface**, and state reachability and size
bounds explicitly. Generated counterexamples are candidate findings until a human
reviews them: an impossible minimal case is evidence to audit the generator
before blaming the implementation.

For every intended public value, trace admitted input through a public
constructor/producer and consumer to a public observation. The construction
graph must be acyclic from an admitted input, or name an explicit bootstrap;
a cycle with no seed proves neither inhabitation nor reachability.

## 5. Optimise by denotation, and prove the claim observationally

Seek a homomorphic denotation the other observations derive from. State the old
and new observation sets and the equivalence claim **before** changing the
representation, and protect it with generated terms on both sides.

For a changed representation, check both encode/decode round trips at the
declared observational equality. For a mapping over an operation, check
identity and composition preservation. Execute against an independent reference
encoding over generated public inputs, including the input that refuted the old
carrier; retain each law's actual run and counterexample evidence rather than
assigning one aggregate result to laws it did not exercise.

Passing generated checks is evidence, not proof. Say which.

**Model-to-runtime ceiling.** Name the concrete operation and observation for
each model operation. An unchanged account balance does not exclude a payment
attempt. If concrete activity is invisible to the model, extend the observation
or narrow the guarantee; relate accepted and refused traces, including a later
batch failure, through the refinement map. Trace refinement is application
synthesis from Sandy Maguire, *Certainty by Construction*, Appendix: Ring Solving
→ Semantics; *Algebra-Driven Design*, Deriving Implementations → Tile
Implementation → Generating Tests. A model proof alone is not that runtime link.

## Stop conditions

The design is ready when every public constructor participates in a law or an
observation, equality has a stated scope, and tempting-but-false laws are
**recorded rather than deleted** — a future reader who rediscovers one needs to
know it was already refuted.

Escalate rather than paper over an unresolved observation, an incompatible
carrier, or a nondeterministic boundary whose effect model has not been stated.

## Scope boundary

Candidate algebra/preservation only: `BROAD_INPUT_DOMAIN` needs broad generated
domain plus independent observation/falsifier; finite exhaustive/no law is
`NOT_APPLICABLE`. It selects no topology, aggregate, deployment or runtime wiring.

## Cross-cutting invariants

If not already loaded, read `nw-cross-cutting-invariants` for
`gate:design-principles-gdp-1-9`. For a produced datum or observation, consult
`data:consumer-known-before-produced` in its actual home,
`nw-cross-cutting-input-data-contracts`; read that lens if not already loaded.
An observation nobody consumes is a field, not an observation.
