---
name: nw-fp-principles
agent: nw-functional-software-crafter
description: Core functional programming thinking patterns and type system foundations, language-agnostic
user-invocable: false
disable-model-invocation: true
---

# FP Principles

Core functional programming thinking patterns. Language-agnostic.

Cross-references: [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md) | [fp-hexagonal-architecture](../nw-fp-hexagonal-architecture/SKILL.md) | [fp-algebra-driven-design](../nw-fp-algebra-driven-design/SKILL.md)

---

## 1. Higher-Order Functions as Problem Decomposition

[STARTER]

Three operations replace most loops:

| Operation | Purpose | Replaces |
|-----------|---------|----------|
| **Map** | Transform each element, preserve structure | Loop building new collection |
| **Filter** | Keep elements matching condition | Loop with conditional |
| **Fold** | Accumulate elements into single result | Loop with running total |

**When to use Map**: Transform every element without changing collection shape. Nested maps handle nested structures.
**When to use Filter**: Select elements without changing their values.
**When to use Fold**: Reduce collection to single value. Accumulator IS your state. Combining function IS your state transition. Folds make state machines explicit.

**Decision**: "Am I transforming, selecting, or accumulating?" Pick matching operation. If none fit, compose two.

**Why**: These operations communicate intent. Map says "same shape, different values." Fold says "many inputs, one output." Loops say nothing about intent until you read every line.

---

## 2. Type-Driven Design

[STARTER]

Write the type signature before implementation. The type tells you what the function can and cannot do.

**Process**:
1. Declare what the function consumes and produces
2. Ask: "which type-specific operations do I actually use?"
3. Replace concrete types with type variables for everything you don't inspect
4. Add constraints only for capabilities you use (equality, ordering, display)

**Design progression**: Concrete types -> type variables -> constrained type variables. Each step increases reuse while documenting minimal assumptions.

**Why**: Function's type signature is a contract. Narrower types mean fewer possible implementations, fewer bugs.

---

## 3. Pattern Matching as Decision Decomposition

[STARTER]

Decompose decisions by data shape, not boolean conditions. Each clause handles one concrete case. Compiler verifies exhaustiveness.

**When to use pattern matching**: "What shape is this data?"
**When to use guards/conditions**: "What property does this value have?"
**When to use named bindings**: Intermediate results need a name to avoid repetition.

**Heuristic**: Prefer small extracted functions over giant match expressions. Pattern match on top-level shape, delegate to named functions for sub-decisions.

**Exhaustiveness as safety net**: When you add a new variant to a choice type, compiler flags every match that doesn't handle it.

---

## 4. Composition Patterns

[INTERMEDIATE]

### Partial Application

Fix some arguments of a general function to create specialized version. Eliminates throwaway helper functions.

**When**: General function exists and you need specialized version for specific context.

### Function Composition (Pipelines)

Chain functions where output of one feeds into next. Each function has single responsibility.

**Why**: Composition reveals architecture of computation. Pipelines read as sequence of steps, making business process visible.

### Point-Free Style

Omit explicit argument when function is just a composition. Use when it reveals intent. Avoid when it obscures meaning.

---

## 5. Container Abstractions

[INTERMEDIATE] -> [ADVANCED]

Progressive hierarchy for working with values inside containers (nullables, lists, futures, results).

### [INTERMEDIATE] Transformable Container (Functor)

**What**: Apply function to values inside container without changing structure.
**Plain English**: "I have a value in a box. Transform the value without opening the box."
**When**: You have nullable/optional/list/future and want to transform contents without inspecting the container.
**Guarantees**: Transforming with identity does nothing. Can fuse or split transformations freely.

### [INTERMEDIATE] Combinable Containers (Applicative)

**What**: Apply a function inside a container to values inside other containers.
**Plain English**: "I have a function in a box AND values in boxes. Combine them."
**When**: Validation -- check multiple fields independently, combine results only if all succeed. Doesn't short-circuit; collects all errors.

### [INTERMEDIATE] Combinable Values (Monoid)

**What**: Combine two values of same type into one, with default element that changes nothing.
**Plain English**: "I have many values. Smash them together into one."
**When**: Folding/reducing collections. Combining operation must be associative, enabling parallelism.
**Examples**: String concatenation with empty string | addition with zero | list append with empty list.

### [ADVANCED] Chainable Operations (Monad)

**What**: Chain operations where each step produces wrapped value, next step depends on previous result.
**Plain English**: "Step 1's output determines what step 2 does. Each step might fail/branch/have effects."
**When**: Sequential dependent operations where each step can fail, branch, or produce effects.

### Decision Tree: Which Abstraction Do I Need?

```
Do I need to transform values inside a container?
  YES, one function, one container --> Transformable (Functor)
  YES, combine multiple independent containers --> Combinable Containers (Applicative)
  YES, chain dependent operations sequentially --> Chainable Operations (Monad)
Do I need to combine values of the same type?
  YES --> Combinable Values (Monoid)
```

### Progression Summary

Each level adds a new kind of combination:
- **Transformable**: one function, one container
- **Combinable Containers**: one function, multiple containers (independent)
- **Chainable**: sequential dependent operations, each producing container
- **Combinable Values**: same-type values collapsed into one

### Runnable Example: Map, Filter, Fold on Domain Objects

```
orders = [Order(100, "pending"), Order(250, "shipped"), Order(50, "pending")]

pendingTotals = orders
  |> filter (o -> o.status == "pending")    -- [Order(100, "pending"), Order(50, "pending")]
  |> map (o -> o.amount)                    -- [100, 50]
  |> fold 0 (acc, x -> acc + x)            -- 150
```

---

## 6. Specialized Chainable Patterns

[ADVANCED]

| Pattern | What It Manages | When to Use |
|---------|----------------|-------------|
| **Optional** (Maybe/Option) | Possible absence | Operations that can fail without explanation |
| **Result** (Either) | Failure with context | Operations that fail with error details |
| **Environment** (Reader) | Shared read-only config | Dependency injection, configuration threading |
| **Accumulator** (Writer) | Side-channel output | Logging, auditing, collecting metadata |
| **Stateful** (State) | Sequential state changes | Counters, parsers, accumulators |

These compose: real applications stack multiple patterns. See [fp-hexagonal-architecture](../nw-fp-hexagonal-architecture/SKILL.md) for DI patterns.

---

## 7. Lazy Evaluation as Design Pattern

[INTERMEDIATE]

Separate WHAT to compute from WHEN it gets computed. Define potentially infinite sequences and let consumer determine how much to evaluate.

**When**: Generating candidates then selecting results | pagination and streaming | decoupling producers from consumers | build systems that only rebuild what changed.

**Separation principle**: Generate all possibilities, then filter. Declarative style says WHAT you want, not HOW to search.

---

## 8. The FP Problem-Solving Method

[STARTER]

1. **Start with type signature**: What does this function consume and produce?
2. **Identify traversal pattern**: Map, filter, fold, or search?
3. **Recognize accumulator**: If folding, what is the state and how does each element change it?
4. **Decompose by data shape**: Pattern match on constructors, handle each case independently
5. **Compose small functions**: Build complex behavior from simple, tested pieces

**Mindset shift**: Describe WHAT to compute (transformations, compositions, constraints) rather than HOW (loops, mutations, control flow).

| Imperative Thinking | Functional Thinking |
|---------------------|---------------------|
| Loop through items | Map/filter/fold over collections |
| Mutate variables | Transform immutable values |
| Check conditions with if/else | Pattern match on data shapes |
| Inherit from base class | Satisfy capability constraints |
| Call methods on objects | Compose functions into pipelines |
| Handle errors with try/catch | Use Optional/Result for explicit failure in types |
| Pass dependencies explicitly | Use Environment pattern for implicit config |
