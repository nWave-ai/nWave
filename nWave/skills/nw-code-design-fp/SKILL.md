---
name: nw-code-design-fp
description: FP code-design SSOT — the WHAT-to-design catalog (algebra-driven design, domain modelling with types, railway/error-track isolation) shared by the solution architect (design-time) and the functional crafter (execution-time).
---

# FP Code Design

Design-time catalog for functional work. The architect loads this to design the
domain algebra, the type-level model, and the error/effect tracks BEFORE DISTILL
authors ATs; the functional crafter loads the same SSOT for execution. This is
the WHAT-to-design subset — execution mechanics (naive/discover/freeze testing,
ORM/persistence mapping, language idioms) stay in `nw-fp-algebra-driven-design`,
`nw-fp-domain-modeling`, and the language skills below.

### FP language skills — resolve by target language, never by default

| Language skill | Languages | PBT sibling (when one exists) |
|---|---|---|
| `nw-fp-clojure` | Clojure | — |
| `nw-fp-erlang-elixir` | Erlang, Elixir | `nw-pbt-erlang-elixir` |
| `nw-fp-fsharp` | F# | `nw-pbt-dotnet` |
| `nw-fp-haskell` | Haskell | `nw-pbt-haskell` |
| `nw-fp-kotlin` | Kotlin | `nw-pbt-jvm` |
| `nw-fp-rust` | Rust | `nw-pbt-rust` |
| `nw-fp-scala` | Scala | `nw-pbt-jvm` |
| `nw-fp-typescript` | TypeScript, JavaScript | `nw-pbt-typescript` |

Same shape as the Polyglot Adapter Matrix `nw-test-design-mandates-layered-mechanics`
already uses for PBT bindings — one row per target language, resolved from the
contract's own target evidence, never guessed. A language NOT in this table has
no dedicated FP-idiom skill: load this catalog and `nw-fp-domain-modeling` alone
(both are language-agnostic) rather than silently substituting a listed
language's skill — the wrong language's idioms are worse than none.

## Functional Core

Inside domain and application code:

- **Pure core, effects at the edge** — domain functions take values and return
  values; I/O, time, randomness and persistence stay in a thin shell that calls
  the core. No mutation and no shared state in the core.
- **Total functions** — every domain outcome is a case of the return type
  (see Railway, rule 5); no exception or null for a domain outcome.
- **Composition** — small single-purpose functions composed through pipelines
  and the railway; dependencies as leading parameters (see Dependencies).
- **Laws** — when the design declares an algebra, preserve each law; use
  `nw-fp-algebra-driven-design` to implement it, never to invent a new one.

**Refactoring order within each delta, verified once with it** — first readability (names, dead code,
magic values), then complexity and duplication, then move each decision into
the type or function that owns its data, then replace primitives and flags with
domain types and choice types, then replace conditionals on data with pattern
matching over a sum type, then extract the effects to the shell. Behaviour and
declared laws stay unchanged.

## Algebra-Driven Design

Discover the API before implementing by specifying the rules (equations)
operations must satisfy. Rules generate property tests, reveal missing features,
and catch contradictions at design time (minutes) not production (days).

### Design process (5 steps)

1. **Start with scope, not implementation** — do not fix data structures upfront.
2. **Define observations first** — how users extract information; observations
   define equality (two values equal if no observation distinguishes them).
3. **Add operations incrementally** — for each, write rules connecting it to
   existing ones. The web of rules IS the design.
4. **Let messy rules signal problems** — complex rules mean coarse building
   blocks; decompose until each rule is near-trivial.
5. **Generalize aggressively** — remove unnecessary type constraints; if
   operations ignore contained values, parameterize over them.

### Algebraic structures (recognize → reuse known rules)

| Structure | Defining rule | Design signal / use |
|-----------|---------------|---------------------|
| Semigroup | `(a·b)·c = a·(b·c)` (associative) | Combining where parenthesization is irrelevant (concat, min/max, config merge) |
| Monoid | Associative + identity `e·x = x = x·e` | Safe defaults, fold/reduce over collections (`(+,0)`, `(concat,[])`) |
| Semilattice | Associative + commutative + idempotent | Conflict resolution, CRDTs, eventually-consistent merges (`max`) |
| Functor | Preserves identity + composition under `map` | Operations agnostic to the contained type |
| Applicative | Element-wise combine + uniform fill | Combining containers of differing content |
| Group | Monoid + inverse `x·x⁻¹ = e` | Undo, reversible spatial transforms |

Heuristic: associative? look for an identity → monoid. Have identity? check
commutativity/inverse → semilattice/group. Each upgrade unlocks new rules.

### API design properties (8, three categories)

| Category | Properties |
|----------|-----------|
| Clarity | Compositional · Task-relevant · Interrelated (rules link every operation) |
| Economy | Parsimonious · Orthogonal · Generalized (no needless type constraints) |
| Safety | Closed (valid construction ⇒ valid semantics) · Complete (max structure discovered) |

### Decision tree — is algebraic thinking worth it?

- Domain about COMBINING → rules (order/defaults/inverses) map to a known structure.
- Domain about TRANSFORMING → look for Functor / structure-preserving patterns.
- Small, well-understood surface → conventional design (algebra adds overhead).
- Otherwise → rules still clarify, even without standard structures.

## Domain Modelling with Types

Make illegal states unrepresentable; model workflows as pipelines; push errors to
the type level. Every rule encoded in a type needs no unit test.

### Building blocks and wrappers

1. **AND (record types)** — value has ALL fields (Order = CustomerInfo AND
   Address AND OrderLines).
2. **OR (choice types)** — value is ONE OF alternatives (ProductCode = Widget OR
   Gizmo). Compose recursively to express any domain structure.
3. **Domain precision** — a domain concept gets its own type (record, choice
   type, opaque or newtype-style wrapper), never a raw primitive, string or bare
   collection inside the core. Prefer zero-cost native forms where the language
   offers them; raw primitives belong only at the adapters.
4. **Smart constructors — parse, don't validate** — raw input becomes a domain
   type once, at the boundary, through a constructor that returns a result; the
   core never re-checks it. Reuse the existing owner of an invariant; a native
   representation that already makes the invalid state unconstructible needs no
   extra wrapper.

### Make illegal states unrepresentable

| Smell | Fix |
|-------|-----|
| `{ Email; IsVerified: bool }` flag | Distinct `VerifiedEmail` / `UnverifiedEmail` types; verification-requiring functions take `VerifiedEmail` |
| `{ Email: option; Address: option }` (both could be None) | Choice type `EmailOnly \| AddressOnly \| EmailAndAddress` — "at least one" enforced structurally |
| List that must be non-empty | `NonEmptyList<T>` — zero-element state cannot be constructed |

### Workflow as pipeline

Every workflow is one function: command in, events out. Decompose into stateless,
pure, single-input/output steps, each transforming one document type to the next:

```
UnvalidatedOrder → ValidatedOrder → PricedOrder → Events
```

Each step name is a domain concept; each step is independently testable.

### State machine with types

Model each lifecycle stage / state as a separate type; a top-level choice type
unifies them (`Cart = Empty | Active of ActiveData | Paid of PaidData`).
Transition functions pattern-match the current state and return the next.
Benefits: all states explicit, per-state data, invalid transitions rejected by
types, exhaustiveness warnings reveal unhandled cases. New states (e.g.
`Refunded`) add without breaking existing code.

### Dependencies and naming

- Declare each step's dependencies as leading parameters, primary input last
  (enables partial application = functional DI). Top-level workflow hides
  dependencies; internal steps make them explicit.
- Types as nouns · workflows as verbs · events past-tense · commands imperative ·
  lifecycle prefixes (`Unvalidated…`/`Validated…`/`Priced…`).

### Decision tree — how to model a concept?

```
Simple value with a domain meaning?   → Its own type; smart constructor at the boundary
One of several alternatives?         → Choice Type (sum)
Groups several values?               → Record Type (product)
Distinct lifecycle stages?           → State Machine with Types
Transforms data through stages?      → Workflow Pipeline
```

## Railway

Each step returns a `Result`; the pipeline runs on two tracks (success/failure)
and short-circuits on the first failure. Design the error track up front.

```
rawInput
  |> validateOrder        -- Result<ValidOrder, Error>
  |> bind calculateTotal  -- Result<PricedOrder, Error>
  |> bind checkInventory  -- Result<ConfirmedOrder, Error>
  |> map  generateReceipt -- Result<Receipt, Error>
```

### Combinators

| Combinator | Role |
|------------|------|
| `map` | Transform the success value (one-track → two-track) |
| `bind` | Chain a function that itself returns `Result` |
| `mapError` | Transform the error value (lift a step error into the common type) |
| `tee` | Side effect without changing the value (logging) |

### Error classification (design decision per category)

| Category | Examples | Strategy |
|----------|----------|----------|
| Domain errors | Validation failure, out of stock | Model as types, return via `Result` |
| Panics | Out of memory, null reference | Throw; catch at top level |
| Infrastructure errors | Network timeout, auth failure | Case-by-case |

### Design rules

1. **Unify error types** — define one common error choice type; `mapError` to
   lift each step's error before composing.
2. **Accumulate when the user needs all errors** — use Applicative validation
   (runs all checks, collects errors into a list) for forms / batch input;
   standard `bind` short-circuits on the first.
3. **Document effects in signatures** — `Result` for errors, `Async` for I/O,
   `Option` for missing data; the signature is the contract.
4. **Declared inputs — what does this function READ that nobody passed it?**

   The FP reading of `contract:declared-inputs-not-ambient-reads` (SSOT:
   `nw-cross-cutting-invariants` — the gate list and the anchor live there).

   > For every gate that clause lists, decide in the **signature**: a parameter,
   > a reader environment, an injected capability — with the ambient lookup kept
   > as a default the caller may state.

   A function whose result depends on state absent from its arguments **is not
   pure**, whatever its body looks like, and no amount of `Result` in the return
   type recovers that. It also cannot be property-tested honestly: the generator
   cannot reach the cases the ambient state is silently fixing, so the suite looks
   thorough while the interesting partition is unreachable.

   Test-side mirror: the Algebraic Analysis Before the Scenario mandate
   (`nw-test-design-mandates`), its declared-inputs question.

5. **Count the outcomes before you choose the return type.**

   > **How many outcomes does this operation have — and does its signature carry
   > every one of them?** Answering "it returns the value and raises on the bad
   > case" is the wrong answer: that is N-1 outcomes in the type and one in the
   > control flow. **If any outcome is not in the return type, put it there** —
   > a sum type with one case per outcome, illegal combinations unconstructible.

   Raising is a control-transfer effect, so an operation that raises is not
   total. Two costs, and the second is the one that bites in a polyglot host:

   - **Composition.** A raising step cannot be `bind`-ed. Every caller needs an
     imperative wrapper and the railway degrades to one track with hidden exits.
   - **Identity.** `except`/`catch` matches on the error's *class identity*. Where
     the same module is reachable by more than one path — a source tree plus an
     installed runtime, a harness that adjusts the import path, a plugin cache —
     that identity is not guaranteed, the handler fails to match, and a *handled*
     outcome escapes as a crash in an environment nobody tested. A returned sum
     type has no identity to mismatch.

   Keep raising for a **programming error** — a broken precondition, an
   import-time drift guard — where crashing IS the correct outcome and no handler
   is meant to cross a module boundary.

   Empirical anchor 2026-08-06: a resolver documented three
   outcomes, returned two and threw the third. CI showed the exception escaping
   the `try` whose very next line was the matching `except`. Returning all three
   closed the class WITHOUT establishing why the module had loaded twice — and a
   fix that does not depend on that answer is a design fix, not a patch.

## Cross-cutting invariants (load them — they are not restated here)

Paradigm- and role-independent rules live in ONE shipped home: `nw-cross-cutting-invariants`.
Load it alongside this skill and honour these clauses by id — they are NOT duplicated here:

- `data:consumer-known-before-produced` — a datum is produced only because a named consumer
  reads it, and you must name the JOIN KEY it will be related on. No reader, or no key → the
  datum is unjustified.
- `gate:self-explaining-what-why-how` — every rejection states WHAT / WHY / HOW.
- `gate:design-principles-gdp-1-9` — the canonical gate-design contract.
