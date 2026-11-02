# Advanced Haskell Type-Level Design

Use this reference only for a GHC target. Decide whether an advanced technique
earns its complexity, then design the smallest ergonomic boundary.

## Haskell trigger and decision gate

Consider it when a Haskell API has a type-dependent result, an existential
payload, a resource that must not escape its scope, a schema computed from
types, a representation-preserving conversion, or a runtime tag that selects a
typed payload. Also consider a proposed GADT, `DataKinds`, rank-N type, type
family, `coerce`, open row, or singleton design.

Admit the design only when a concrete rejected call is valuable at compile time;
the relevant states/schema are finite and stable; a realistic accepted call is
at least as legible as the value-level alternative; the public GHC/package
range and extensions are known; and the technique has a narrow boundary with
predictable diagnostics. Keep unsafe constructors, casts, and family machinery
inside the smallest module boundary.

## Escalation gate

| Need | Smallest likely tool |
| --- | --- |
| Match refines the result type; ill-typed syntax must not exist | GADT, possibly `DataKinds` |
| API consumes an unknown type uniformly | existential with rank-N eliminator |
| Reference/capability must not escape a bracketed scope | rank-N region token |
| Type-level state transition is the product contract | `DataKinds` index; indexed interface only if a simple phase type cannot express it |
| Schema computes an interface or constraint | associated/closed family; FCF only for genuine higher-order reuse |
| Runtime tag selects a statically distinct payload operation | singleton/Sigma after a closed ADT is insufficient |
| Representation is identical but abstraction must survive | `newtype`, `Coercible`, deliberate role |
| Extensible typed row is truly required | mature library first; otherwise tightly encapsulated open sum/product |

Stop and use the simpler form when the check is local, states are volatile or
user-defined, the payload is inherently dynamic, the rejected call is
contrived, or annotations make ordinary use worse. `unsafeCoerce`,
`unsafePerformIO`, overlapping instances, and an open `Eval` universe need an
explicit exceptional justification; never use them as defaults.

## Call-site contract

Write accepted and rejected call-sites before implementation:

```haskell
-- Accepted: evaluation exposes exactly the index promised by the expression.
eval (Add (LitInt 2) (LitInt 3)) :: Int

-- Rejected: a boolean cannot be supplied to integer addition.
eval (Add (LitBool True) (LitInt 3))
```

```haskell
-- Accepted: the reference is consumed inside its universally quantified region.
runRegion $ \ref -> readRef ref

-- Rejected: `Ref s a` cannot be returned because `s` is local to runRegion.
runRegion $ \ref -> pure ref
```

Explain the chosen quantifier: the caller chooses `a` for `forall a`; an
existential hides an `a` chosen by the implementation. If clients need
pervasive `Proxy`, elaborate kind annotations, or internal `Eval` symbols,
provide a named eliminator, smart constructor, or value-level facade instead.

## Required notes

- Finite sums add inhabitants and products multiply them. An isomorphism
  preserves information, not domain meaning, instances, strictness,
  performance, or names.
- GADT pattern matches introduce equality evidence. Existentials retain only
  operations supplied by their dictionary or eliminator. Rank-N scopes decide
  who chooses a type.
- Type families are saturated and not first-class functions. Treat
  defunctionalized `Exp`/`Eval` as a library convention, not a casual helper.
- `Coercible` is representational equality, not semantic equivalence. Roles may
  strengthen inferred roles but cannot weaken them. Keep cast alignment
  invariants private and auditable.
- Public diagnostics name the operation, requirement, supplied state, and
  remedy. `TypeError` cannot rescue an opaque API.

Read [technique selection](technique-selection.md) when choosing a mechanism,
and [ergonomics and compatibility](ergonomics-and-compatibility.md) before
exposing a compiler- or package-dependent API.
