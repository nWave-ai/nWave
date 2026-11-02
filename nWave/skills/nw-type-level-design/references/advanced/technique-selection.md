# Advanced Haskell technique selection

Use this reference after the escalation gate. Prefer the first adequate row; techniques compose only when each protects a separate invariant.

| Problem shape | Adopt when | Accepted shape | Reject / keep simpler when |
| --- | --- | --- | --- |
| Equivalent representations | A regular shape removes repetition and callers benefit from combinators | `Grid a = Coord -> a`, with explicit domain conversions | Equal cardinality would hide meaningful field names, change instances, or obscure performance |
| Promoted states (`DataKinds`) | A small, stable set of phases or capabilities is central to the contract | `Connection 'Open` is required by `send` | A flag is local, transient, or derived from external runtime state |
| GADT | Pattern matching must refine a result type or carry equality evidence | `eval :: Expr a -> a`; `Add :: Expr Int -> Expr Int -> Expr Int` | A closed ordinary ADT plus one runtime validation is clearer; GADT deriving/inference dominates the API |
| Rank-N | A callback must work uniformly at every type, or a scope owner must choose a fresh token | `withPacked :: Packed -> (forall a. Cap a => a -> r) -> r` | Quantification only encodes a clever encoding; a named data type or ordinary callback states the intent |
| Existential | A value's concrete type should be hidden but selected capabilities survive | Pack `a` with `Show a`; eliminate through its capability | Clients later need arbitrary recovery of `a`; use a closed sum or typed lookup instead |
| Region / ST-style token | A resource/reference must be impossible to leak beyond a local owner | `runRegion :: (forall s. Region s a) -> a` | Resource lifetime depends on I/O, cancellation, or another dynamic system the token cannot control |
| Roles and `coerce` | A zero-cost newtype conversion is intended and preserves the invariant | `coerce` through a representation-safe wrapper | A key/order/class invariant distinguishes the parameter; preserve nominal separation |
| Associated or closed family | A stable type-level grammar computes a type, constraint, or protocol interface | One schema drives both an interpreter and its signature | The schema arrives at runtime, equations/overlap become the API, or a value-level AST gives better errors |
| First-class-family encoding | A family must be passed to reusable type-level map/fold/composition | Use one governed `Eval` convention or established FCF library | It only saves a few repeated equations; ceremony, compile time, and open instances outweigh reuse |
| Open sum/product | Typed extension is required across modules and closed alternatives cannot serve it | `inj`/`prj` or label lookup behind smart constructors | A plugin map or closed ADT suffices; never expose unchecked vector/index/cast alignment |
| Singletons / Sigma | A runtime tag truly determines the statically typed payload operation | Reify tag to `SomeSing`; eliminate with a total dictionary | Tags are known at compile time, all cases share one operation, or a closed ADT is enough |

## Mechanism-specific constraints

### Cardinality, isomorphism, and variance

Use cardinality to ask whether the information content matches: zero (`Void`), one (`()`), sum, product, and finite function. The calculation deliberately ignores divergence and therefore is not a full semantic proof for lazy Haskell. An isomorphism needs both directions and should preserve the domain story at its boundary.

Trace a parameter through function arrows before asking for `Functor`: result position is positive, argument position reverses polarity. Covariant, contravariant, and invariant interfaces need their corresponding laws; variance alone does not approve an API.

### DataKinds, GADTs, constraints, and families

Promote a small datatype only after naming its kind and the intended public indices. A GADT constructor states the evidence clients may obtain by matching; index only information that affects a safe operation. For heterogeneous type-level lists, recursive constraints should use an explicit base and step, but a normal record is usually clearer.

Associated families bind a class implementation to a computed type. Closed families are useful for a finite, ordered grammar. Both demand saturated applications. Treat first-class-family defunctionalization (`Exp`/`Eval`) as a library-level convention, not a casual local helper.

### Quantification, existentials, and regions

Read `forall` by ownership. In `forall a. a -> ...`, the caller picks `a`; in a rank-N argument `(forall a. ...)`, the callee of that argument picks `a`. An existential is a package whose producer selected `a`; its eliminator may use only the capabilities packed with it. A region token applies the same rule to lifetime: universal quantification makes the token fresh and unnameable outside the runner.

Do not reproduce teaching implementations based on `unsafePerformIO`. If an unsafe primitive is unavoidable, the exported module must hide it, name the invariant that makes it sound, and restrict all construction paths.

### Roles, open data, and dependent approximations

`newtype` has no runtime representation overhead, while `coerce` is permitted only when GHC proves representational safety. Treat roles as part of an abstraction boundary: phantom is weakest, representational follows representation, nominal prevents lifting a coercion. Strengthen to nominal when the parameter selects an invariant.

An open sum/product typically pairs a type-level list with runtime storage. Its correctness hinges on index/list and label/type alignment; keep storage and casts private. For singleton designs, make reification from dynamic input explicit (`SomeSing`) and ensure every eliminator has the required equality proof or total dictionary. Neither technique converts untrusted input into a compile-time fact without a runtime check.
