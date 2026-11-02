---
name: nw-certainty-by-construction
description: Turn a stable layer claim (domain, application, adapter, or infrastructure) into a construction boundary so the invalid state cannot be built, and state honestly what remains unguarded. Use when a requirement says an invalid state or transition must not occur, when values need a canonical form, or when a rewrite/cache/optimisation must preserve meaning. Complements nw-fp-domain-modeling, which shows the encodings; this decides whether to encode, how strong the claim really is, and what obligation is left over.
---

# Certainty by Construction

`nw-fp-domain-modeling` shows encodings; this decides whether a claim belongs
in construction, its honest strength and the obligation left outside.

Safety is exclusion only. Also establish **valid-state inhabitation**: at least
one intended value has an acyclic construction path from admitted input. Public
reachability (that path reaches a public observation) and liveness (eventual
progress under temporal assumptions) are separate claims; construction alone
does not establish either.

**Layer-neutral (ADR-SSOT-002 §6a).** A claim is encoded at whichever layer
it is stable, local and high-value — domain state/transition, application/
port outcome, adapter/integration failure translation, or infrastructure/
recovery policy. Which layers apply to a target derives from that target's
declared `boundary`/`contract-shape`, never a hand-picked "domain-only" scope.

## Work from the claim outward

1. **State the proposition precisely.** "A `ConfirmedBooking` has an approved
   payment." Name its owner and its semantic equality.
2. **Draw the trust boundary.** Which inputs and writers are untrusted, where
   effects and persistence enter, and **who can bypass the constructor**.
3. **Choose the strongest proportionate encoding.** A guarantee is only real if
   its constructors and eliminators make the prohibited state hard to express.
4. **State the residual obligation.** Record stable/local admitted, excluded
   and unknown states with risk owner; route triggered stressors to
   `nw-stress-analysis`; triage a removed-hypothesis counterexample before a
   missing-type claim. Do not convert external, temporal or cross-system rules
   into local type claims.
5. **Demonstrate both sides.** When implementing, add tests in the owned test
   paths that the invalid construction is refused with its reason and that a
   valid value is built through the public producer; a throwaway script is not
   that test; when no test path is owned, name the uncovered refusal in the
   diagnostic for the oracle owner. For a call the checker rejects, keep the
   receipt of a failing run of the repository's own checker or compiler on a
   separate probe.

Before refining, ask: is the invariant stable, local and high-value; can all
legitimate construction pass through this boundary; will the representation
survive the API, serialization and interop edges? If not, keep it **extrinsic** —
and carry it deliberately rather than pretending it is intrinsic.

For each intended public value, name admitted input, public constructor or
producer, consumer and public observation. A cycle is valid only with an
explicit bootstrap outside the cycle; otherwise its safety claim has no
inhabited valid value.

## Make propositions carry evidence

Treat `P(x)` as a type of evidence for `P(x)`.

- Prefer a validated constructor, opaque value object, non-empty wrapper or
  state-specific type over a primitive plus a convention.
- Make construction the only ordinary route in. A public raw constructor that
  recreates the invalid state cancels the guarantee.
- **Return the evidence, not a Boolean.** A decision's success branch carries a
  witness; its failure branch carries a reason. `true`/`false` throws away what
  the caller needs next.
- Keep operations total over their stated input types; where the language cannot
  make an alternative unrepresentable, put it in the **result type** instead.

**One structural owner.** When multiple boundary views express a declared closed
structural contract, derive the needed schema, shape parser or field-aware
traversal from one description rather than re-declaring alternatives in preflight.
Check raw allowed keys before normalizing declared slots: an unknown key remains
invalid even when its value is null or empty. Resolve a selector once and return
its witness to the consumer. On the declared structural input domain,
`schemaAccepts(x) iff shapeParse(x) succeeds`; reference existence and mutable
policy remain separate semantic obligations. Generic derivation: Sandy Maguire,
*Thinking with Types*, Generics → Using Generic Metadata; intrinsic construction:
*Certainty by Construction*, Decidability → Intrinsic vs Extrinsic Proofs.
Raw-key ordering and selector reuse are application synthesis.

**Semantic closure before construction activity.** When refusal forbids issuance,
interning, rendering or writes, finish selection and semantic decisions over a
pure description before invoking those activities. A ready plan has no remaining
semantic refusal; interpretation may still return declared environmental failure.
For an account-change batch, decide against evolving descriptive state, then
materialize only the accepted plan. Law: semantic refusal preserves prior state
**and has an empty protected-activity trace**. Scope that trace to the contract's
named activities, data and outcomes: a refusal-only promise does not forbid
interning discarded data on an accepted path, nor every interning call when only
a particular data subset is protected. A separate discard prohibition needs its
own stated scope. Purity or rollback alone cannot establish invocation exclusion.
This is application synthesis, not a theorem supplied by the books: Sandy
Maguire, *Algebra-Driven Design*, Deriving Implementations → Tile Implementation
→ The Initial Encoding; *Thinking with Types*, Indexed Monads → Definition and
Necessary Machinery; *Certainty by Construction*, Decidability → Intrinsic vs
Extrinsic Proofs. This boundary is warranted by that prohibition, not by every
ordinary parser or pure function.

## Prefer canonical meaning

Decide first whether semantically equal values should have ONE representation. If
yes, design the canonical form into the constructors and the later normalization
and equality burden disappears.

If several representations are intentionally valid, specify all four: the
denotation map, the equivalence relation, the normalization, and the
**preservation claim** — that normalization has the same denotation as its input.
Never hide a lossy conversion behind the word "normalization".

**Semantic comparison versus retained bytes.** When a format admits LF and CRLF
as the same layout but promises byte preservation, normalize the comparison view,
not the retained source. Law: no semantic change returns the original bytes;
a status-only update changes only its designated region, preserving all other
bytes. Exercise both admitted line endings and byte-distinct surrounding text.
A new export explicitly specified as canonical LF needs no original-byte buffer.
Exact newline and update policies are application synthesis from Sandy Maguire,
*Algebra-Driven Design*, Designing Algebras → Tiles → Observations;
*Certainty by Construction*, An Exploration of Numbers → Unique Integer
Representations; Appendix: Ring Solving → Semantics.

## Preserve meaning before optimising

| Change | The argument you owe |
|---|---|
| Same information, different representation | Isomorphism: both round trips preserve the intended equality |
| Mapping computations across an operation | Homomorphism: identity and composition preserved |
| Rewrite, cache, memoize, compile | A relation to the specification, plus that every operation preserves it |

An equivalence argument establishes meaning. It says nothing about speed, memory
or availability — those are separate claims and must be measured separately.

## Calibrate the claim to the language — say what you actually have

Choose the row by the checker the repository actually runs in its verification
command, not by the language's reputation.

| Environment | Honest claim |
|---|---|
| Proof assistant | The property follows from checked definitions and admitted axioms |
| Strong static language | Invalid states blocked on typed paths; casts, reflection, deserialization and foreign writers remain boundaries |
| Gradual typing with the checker in verification (e.g. Python + mypy, TypeScript) | The checker rejects modeled invalid calls on annotated paths, so the guarded operation takes the evidence type; `Any`, casts, untyped callers and deserialization still need the runtime boundary |
| Mainstream OO/FP | Construction is centralised and misuse reduced; the compiler does **not** prove the predicate |
| Dynamic, or no checker in verification | Checked at controlled runtime boundaries, and every writer must preserve it |

Do not call all type safety "proof", and do not simulate proof strength with
nominal wrappers: a wrapper, annotation or nominal type the runtime can build
around the same invalid value is not a proof. Name the bypass routes and keep
their checks visible.

## What construction never establishes

Stakeholder intent, authorization, time-dependent policy, cross-aggregate
consistency under concurrency, external API behaviour, persistence integrity
after a bypass, cryptographic soundness, availability. Validate those at their
owning boundary and say so.

A false proposition is not a missing implementation detail. Revisit the
statement or the representation.

## Cross-cutting invariants

Load `nw-cross-cutting-invariants` alongside this — especially
`gate:self-explaining-what-why-how`: a constructor that refuses must say WHAT was
invalid, WHY it cannot be built, and HOW to build a valid one.
