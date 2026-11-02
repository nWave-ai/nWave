# Advanced Haskell ergonomics, diagnostics, and compatibility

## Call-site review

Review one ordinary use, one composition use, and one intended invalid use before committing to a public type-level interface.

| Ask | Healthy result | Red flag / response |
| --- | --- | --- |
| What is inferred? | Main types and indices infer from values | Every use needs `Proxy`, visible kind syntax, or ordered `@` applications; add a facade or simplify |
| Who chooses each type? | Quantifier placement explains ownership | A client must understand an internal existential, region token, or `Eval` label |
| What does failure say? | It names operation, requirement, supplied state, and remedy | Constraint soup; add a boundary-specific name or custom error, or reduce machinery |
| What does it cost? | Compile-time and abstraction cost are acceptable for the invariant | Nested families, overlap, or Generic/type-level reduction dominate builds without a critical benefit |
| What is still dynamic? | Input parsing, I/O failure, exceptions, and migrations are explicit | Static indices are claimed to guarantee behavior beyond the modeled transition system |

`ScopedTypeVariables` needs an explicit `forall` to reuse a signature variable. `TypeApplications` exposes the quantifier order, making that order part of the API; changing it can break callers. `AllowAmbiguousTypes` is acceptable only when a short, documented disambiguation route is available.

## Diagnostics

For a foreseeable invalid call, prefer a small public boundary whose diagnostic contains:

1. the operation the client attempted;
2. the required phase/type/label;
3. the supplied or available phase/type/labels; and
4. the next action.

Use `TypeError` at a stable API boundary, not to narrate the internals of a family reduction. Avoid messages coupled to private implementation names; those age poorly as types evolve.

## Version and package drift gate

Before producing implementation-level advice, obtain the project's exact GHC version, language edition/default extensions, Cabal/Stack/Nix constraints, and whether the public library must support multiple compilers. Consult that version's GHC User Guide and the selected package's compatibility bounds; do not infer availability from a book-era extension list.

Pay particular attention to these drift-prone areas:

- extensions and extension bundles around `DataKinds`, `GADTs`, `TypeFamilies`, visible type application, quantified/scoped types, custom errors, and roles;
- legacy terminology or aliases such as `TypeInType`, which should not be prescribed without checking the supported compiler;
- singleton-generation, first-class-family, generic, and inspection libraries, whose generated APIs and supported compiler ranges move independently;
- instance overlap, type-family reduction behavior, inference, and error rendering across compiler releases.

Record any deliberately required extension and the user-visible reason for it. If compatibility cannot be established, give a concept-level design and label implementation details as provisional rather than guessing syntax or package APIs.

## Performance boundary

`newtype` representation and a successful `coerce` are a different claim from generic derivation, large family reduction, singleton plumbing, or indexed encodings. Do not infer runtime or compilation performance from elegance. Keep performance-sensitive transformations value-level or measure them in the owning project; this skill does not prescribe a test strategy.
