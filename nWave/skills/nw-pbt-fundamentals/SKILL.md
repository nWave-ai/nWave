---
name: nw-pbt-fundamentals
agent: nw-functional-software-crafter
description: Property-based testing core concepts, property taxonomy, and strategy selection (language-agnostic)
disable-model-invocation: true
---

# PBT Fundamentals

Core property-based testing knowledge, language-agnostic. Load language-specific skills for framework syntax.

## What PBT Is

Instead of specifying individual test cases, define properties (rules for all valid inputs) and let the framework generate hundreds of random inputs to attempt falsification. On failure, framework automatically shrinks input to minimal reproducing case.

PBT complements example-based tests. Use both.

## Property Types Taxonomy

### Decision Table: Choosing Property Types

| Property Type | Use When | Example Domain |
|--------------|----------|----------------|
| Invariant | Output has structural guarantees regardless of input | sort preserves length, tree stays balanced |
| Idempotency | Applying operation twice equals applying once | formatting, deduplication, HTTP PUT |
| Round-trip | Two operations are inverses | encode/decode, serialize/deserialize, compress/decompress |
| Oracle | Simpler reference implementation exists | optimized algo vs naive, new parser vs stdlib |
| Metamorphic | Can't verify single output but can relate multiple outputs | ML classifiers, search engines, numeric computation |
| Commutativity | Operation order shouldn't matter | set operations, independent migrations |
| Inductive | Property holds for base case and each incremental step | recursive data structures, incremental builds |
| Hard-to-find, easy-to-verify | Solution expensive to compute but cheap to check | pathfinding, factorization, compilation |

### Decision Tree: Given a Function, Which Properties Apply?

```
Start: What does the function do?
  |
  +-- Has an inverse? (encode/decode, serialize/deserialize)
  |     -> Round-trip: decode(encode(x)) == x
  |
  +-- Has a simpler equivalent? (stdlib, naive version)
  |     -> Oracle: my_impl(x) == reference(x)
  |
  +-- Repeated application should be stable? (formatting, normalization)
  |     -> Idempotency: f(f(x)) == f(x)
  |
  +-- Output has structural guarantees? (length, type, range, ordering)
  |     -> Invariant: check structural properties of output
  |
  +-- Hard to verify single output but can relate inputs?
  |     -> Metamorphic: f(transform(x)) relates to f(x) predictably
  |
  +-- Order of operations should not matter?
  |     -> Commutativity: f(g(x)) == g(f(x))
  |
  +-- Works on recursive/incremental data?
  |     -> Inductive: base case holds, step preserves property
  |
  +-- Output is hard to compute but easy to verify?
        -> Hard-to-find/easy-to-verify: verify(solve(x)) == true
```

Most functions have 2-4 applicable property types. Start with easiest to express, then add more.

### Property Type Details

**Invariant**: `len(sort(xs)) == len(xs)`. Most common starting point. Look for structural guarantees of output.

**Idempotency**: `f(f(x)) == f(x)`. Applies to normalization, formatting, caching, PUT requests.

**Round-trip**: `decode(encode(x)) == x`. Highest-value property when applicable -- tests two functions simultaneously.

**Oracle**: `my_sort(xs) == sorted(xs)`. Use when trusted reference exists. Oracle should be "so simple it's obviously correct."

**Metamorphic**: Define relations between executions. Example: `sin(pi - x) == sin(x)`. Valuable when single-output verification is impossible.

**Commutativity**: `f(g(x)) == g(f(x))`. Applies when operations should be order-independent.

**Inductive**: Verify base case + step preservation. Natural for recursive structures.

**Hard-to-find, easy-to-verify**: `product(factorize(n)) == n`. Generate input, run algorithm, verify output cheaply.

## Generator Composition Patterns

### Pattern Hierarchy (simplest first)

1. **Built-in primitives**: integers, strings, booleans, lists, dicts
2. **Map**: Transform generated values: `integers().map(x => x * 2)` for even numbers
3. **Filter**: Reject invalid values (use sparingly -- prefer constraining generators)
4. **FlatMap/Chain**: When one value determines shape of next (dependent generation)
5. **Recursive**: For tree-like structures -- requires base case + recursive case with size control
6. **Frequency/Weighted**: Control distribution to ensure edge case coverage

### Generator Design Rules

- Prefer constraining generators over filtering. `integers(min=1)` beats `integers().filter(x > 0)`
- Use map for simple transformations, flatmap for dependent generation
- Always verify generator distribution with statistics/collect
- Recursive generators need explicit size control to prevent infinite loops
- Weighted generation ensures rare-but-important cases get tested

## Shrinking Strategies

| Strategy | How It Works | Used By | Trade-off |
|----------|-------------|---------|-----------|
| Type-based | Separate shrink function per type; returns list of simpler candidates | QuickCheck, PropEr, FsCheck | Explicit control but manual composition |
| Integrated | Generators produce shrink trees (rose trees); composition automatic | Hedgehog, fast-check, jqwik | Automatic but poor with dependent generators |
| Internal | Shrinks underlying byte stream, replays strategies | Hypothesis, rapid | Fully automatic, works with monadic bind |

Shrinking transforms `[847, -23, 0, 445, 12]` into `[0, -1]` -- minimal failing case. Without shrinking, PBT finds bugs but makes them hard to understand.

## When NOT to Use PBT

- **Highly specified I/O**: Functions with single correct output per input (use example-based tests)
- **UI/visual testing**: Properties of visual output hard to express mathematically
- **Integration tests with external services**: Non-determinism confuses shrinking
- **Simple CRUD with no business logic**: Overhead exceeds benefit
- **Performance testing**: PBT tests correctness, not speed

## When PBT Adds the Most Value

- Serialization/deserialization (round-trip)
- Data structure implementations (invariants)
- Parsers and compilers (oracle, round-trip)
- Mathematical/financial calculations (metamorphic, oracle)
- State machines and protocols (stateful PBT -- see pbt-stateful skill)
- Any function with complex input space and clear correctness rules

## Adoption Guidance

1. Start with round-trip properties -- easiest to write and highest-value
2. Add invariant checks for data structure operations
3. Introduce oracle properties when reference implementations exist
4. Move to stateful PBT for mutable state systems (load pbt-stateful skill)
5. Monitor generator distributions -- tests that never exercise edge cases provide false confidence

### Round-trip Property Example

```pseudocode
property "encode/decode round-trip" {
  for_all input in generate(valid_document):
    encoded = encode(input)
    decoded = decode(encoded)
    assert decoded == input
}
```

Collect statistics over 1000 runs; edge cases should appear in at least 5% of generated inputs.

For sequential operations or mutable state, see pbt-stateful skill.
