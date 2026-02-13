---
name: property-based-testing
description: Property-based testing strategies, mutation testing, shrinking, and combined PBT+mutation workflow for test quality validation
---

# Property-Based Testing and Mutation Testing

> Deferred to Phase 2.25: Mutation testing runs ONCE per feature as a final quality gate at orchestrator Phase 2.25 (after all steps complete). Do NOT run mutation testing during the inner TDD loop.

## Property-Based Testing (PBT)

Instead of examples ("given X, expect Y"), write properties ("for all valid inputs, condition Z holds").
Framework generates hundreds/thousands of inputs checking property. Dramatically expands test coverage.

## Property Patterns

1. **Invariants**: "for all inputs, condition holds" (sorted list is ordered, balance >= 0)
2. **Roundtrip**: "encode then decode = original" (serialize/deserialize, compress/decompress)
3. **Oracle**: "compare against reference implementation" (optimized vs correct-but-slow)
4. **Metamorphic**: "different operations, same result" (add(a,b)==add(b,a), filter can't increase size)

## Shrinking

When property fails, framework auto-finds minimal failing input. Dramatically accelerates debugging.
Algorithm: find failing input -> try simpler variants -> if still fails, use as new candidate -> repeat.

## PBT Tools by Language

| Language | Framework |
|----------|-----------|
| Python | Hypothesis |
| JavaScript/TypeScript | fast-check |
| Haskell | QuickCheck |
| Rust | quickcheck |
| Java | jqwik |
| C# | FsCheck |

Adopted by Amazon, Volvo, Stripe, Jane Street (ICSE 2024 study).

## When PBT Adds Value

HIGH value: algorithms, data structures, serialization, business rules (validation, calculations), protocols/state machines.
LOW value: simple CRUD, UI logic, external API integrations.
PBT complements example-based testing, doesn't replace it.

## PBT + TDD Integration

1. Start with example-based TDD for specific cases (drives detailed design)
2. Once basic implementation works, write properties to generalize
3. If property fails: found bug or need refined implementation
4. Refactor freely - properties verify behavior preservation

Properties = higher-level spec that survives refactoring better than examples.

## Mutation Testing

Evaluates test suite quality by introducing artificial bugs (mutations) and checking if tests catch them.
Mutation score = killed mutants / total mutants. Stronger metric than code coverage.

## Mutation Score Targets

| Score | Quality |
|-------|---------|
| < 60% | Weak suite, significant gaps |
| 60-80% | Moderate, some gaps |
| > 80% | Strong, few gaps |

Target: 75-80% minimum. Not all survivors indicate bad tests (equivalent mutants exist).

## Mutation Operators

Change == to !=, + to -, remove method call, change constant, modify loop boundary, alter comparison.

## Mutation Testing Tools

| Language | Tool |
|----------|------|
| Java | PIT |
| JavaScript/TypeScript/C# | Stryker |
| Python | mutmut, Cosmic Ray |

Computationally expensive. Use incremental: on changed code in PRs, full codebase weekly.

## Combined PBT + Mutation Workflow

1. Write example-based tests (TDD) -> cover known scenarios
2. Apply mutation testing -> identify assertion gaps -> write more tests
3. Add PBT for complex logic -> cover input space systematically
4. Mutation testing again -> verify properties are comprehensive

Quality ratchet: each technique exposes gaps others miss. Prioritize critical paths and complex algorithms.

## PBT Performance Guidance

- Fast feedback: ~100 examples
- CI/CD: ~1000 examples
- Nightly builds: ~10000+ examples

Modern frameworks allow configuring example count per context.
