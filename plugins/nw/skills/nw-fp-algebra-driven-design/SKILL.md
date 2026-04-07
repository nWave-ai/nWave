---
name: nw-fp-algebra-driven-design
agent: nw-functional-software-crafter
description: Algebra-driven API design with monoids, semigroups, and interpreters via algebraic equations
user-invocable: false
disable-model-invocation: true
---

# FP Algebra-Driven Design

Algebraic thinking for API design. Discover the right API before implementing by specifying rules (equations) that operations must satisfy.

Cross-references: [fp-principles](../nw-fp-principles/SKILL.md) | [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md) | [fp-usable-design](../nw-fp-usable-design/SKILL.md)

---

## 1. Why Algebraic Thinking

[STARTER]

Code is the wrong abstraction level for design. Starting with data structures inherits unnecessary constraints.

- **Specify rules first, implement second.** Implementation is a solution to a system of equations.
- **Rules generate tests automatically.** Every rule is directly a property test generating thousands of cases.
- **Rules reveal missing features.** Analysis often exposes operations you need but haven't designed.
- **Rules catch contradictions early.** Contradiction during design costs minutes; in production, days.

---

## 2. The Design Process

[STARTER]

1. **Start with scope, not implementation.** Don't decide data structures upfront.
2. **Define observations first.** How do users extract information? Observations define equality: two values equal if no observation distinguishes them. Gives enormous implementation freedom.
3. **Add operations incrementally.** For each new operation, immediately write rules connecting it to existing ones. This web of rules IS the design.
4. **Let messy rules signal problems.** Complex rules mean coarse building blocks. Decompose until each rule is nearly trivial.
5. **Generalize aggressively.** Remove unnecessary type constraints. If most operations don't inspect contained values, parameterize over them.

---

## 3. Common Algebraic Structures

[STARTER] -> [ADVANCED]

Recurring patterns in software. Recognizing them unlocks known rules and capabilities.

### [STARTER] Combinable Values (Semigroup)

**What**: Type with one merge operation where grouping doesn't matter.
**Rule**: `(a merge b) merge c = a merge (b merge c)` (associativity)
**When**: Combining things where parenthesization shouldn't matter.
**Examples**: String concatenation | config merging | min/max.

### [STARTER] Combinable Values with Default (Monoid)

**What**: Combinable Value with a default element inert under combination.
**Rules**: Associativity + `default merge x = x` and `x merge default = x`
**When**: Safe defaults | fold operations | "nothing happened yet" values.
**Examples**: `(+, 0)` | `(*, 1)` | `(concat, [])` | `(and, true)`.
**Design signal**: If you find an associative operation, look for a default element. Finding one enables fold/reduce over collections.

### [INTERMEDIATE] Merge-and-Forget Values (Semilattice)

**What**: Combinable Value where merging is also order-independent and idempotent.
**When**: Conflict resolution | eventually-consistent systems | CRDTs.
**Example**: Status tracker with `seen < failed < completed` uses `max` as merge.

### [INTERMEDIATE] Structure-Preserving Transformations (Functor)

**What**: Container type where you can transform contents without changing structure. Preserves identity and composition.
**When**: Operations that work on data shape rather than values inside.
**Design signal**: If most operations are agnostic to contained type, you likely have this.

### [ADVANCED] Combinable Containers (Applicative)

**What**: Container where you can combine contents element-wise and fill with uniform values.
**When**: Combining containers holding different content types.

### [ADVANCED] Reversible Operations (Group)

**What**: Combinable Value with Default where every element has an inverse that cancels it.
**When**: Undo operations | spatial transformations.
**Example**: Clockwise/counter-clockwise rotation are inverses; horizontal flip is its own inverse.

---

## 4. Properties of a Well-Designed API

[INTERMEDIATE]

Three categories, eight properties:

**Clarity** (communicates well):
- **Compositional**: Complex values built from simpler ones
- **Task-relevant**: Operations provide high-level functionality useful to actual users
- **Interrelated**: Rules connect every operation to others

**Economy** (no waste):
- **Parsimonious**: Each operation does one thing well
- **Orthogonal**: No half-baked concept shared across multiple operations
- **Generalized**: Unnecessary type constraints removed

**Safety** (prevents mistakes):
- **Closed**: Every syntactically valid construction is semantically valid
- **Complete**: Maximum algebraic structure discovered for every concept

---

## 5. Refactoring with Rules

[INTERMEDIATE]

### Decompose Large Operations

Complex rules mean coarse building blocks. Split operations with many parameters into smaller, orthogonal ones. If a rule ignores some parameters, those should be separate operations.

### Find Contradictions

Algebraic manipulation reveals contradictions before code is written. Requiring order-independence while returning an ordered list is a contradiction. Fix: use unordered collection.

### Unify Observations

When multiple observations share traversal logic, find one observation from which all others derive. Simplifies entire rule set.

### Use Symmetry to Discover Missing Features

When you have a "both" operation (parallel composition), look for its symmetric "either" counterpart. Symmetry discovers functionality not explicitly requested but inevitably needed.

---

## 6. Three-Phase Testing Strategy

[INTERMEDIATE]

1. **Build naive implementation**: Implement each operation as direct data constructor. Obviously correct because it mirrors the spec exactly.
2. **Discover all rules**: Feed naive implementation to a tool that enumerates well-typed expressions and finds observational equalities. Discovers specified AND emergent rules.
3. **Freeze as regression tests**: Convert rules into executable property tests protecting any future optimized implementation.

**Key insight**: Two values are equal if no observation distinguishes them. Testing through observations allows completely different implementations to pass the same suite.

---

## 7. Decision Tree: When Is Algebraic Thinking Worth It?

```
Is your domain about COMBINING things?
  YES --> Algebraic thinking helps significantly
    Do combinations have rules (order irrelevant, defaults, inverses)?
      YES --> Known algebraic structures; use their rules directly
      NO --> Rules still help, but structures are not standard
  NO --> Is your domain about TRANSFORMING things?
    YES --> Look for Structure-Preserving Transformation patterns
    NO --> Is your API surface small and well-understood?
      YES --> Algebraic thinking adds overhead; use conventional design
      NO --> Rules can still clarify, even without standard structures
```

---

## 8. Combining with Other Patterns

**Rules + Property-Based Testing**: Rules ARE property tests. Algebraic constructors become PBT generators. Example: `empty merge x = x` becomes `forAll(x -> assertEquals(empty.merge(x), x))`.

**Rules + Domain Modeling** (see [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md)): Domain wrappers with smart constructors are algebraic rules. State machine transitions are rules about valid sequences. Example: `items(addItem(cart, item))` contains `item` -- directly a property test.

**Rules + Usable Design** (see [fp-usable-design](../nw-fp-usable-design/SKILL.md)): Simple algebraic rules map to simple, searchable, nameable operations -- improving navigability and learnability. Example: decomposing `processOrder` into `validate`, `price`, `confirm` gives three nameable functions instead of one opaque one.

**Decomposition + Feature Organization**: When algebraic decomposition splits a monolithic operation into orthogonal pieces, organize by feature domain. Example: splitting `configureWidget(size, color, border)` into `resize`, `recolor`, `restyle` lets each live in its own feature module.

### Full Cycle: Rules to Tests

```
-- 1. Define operations and observations
CartOps = { empty, addItem, removeItem, itemCount, totalPrice }

-- 2. Write rules
rule: itemCount(empty) == 0
rule: itemCount(addItem(cart, item)) == itemCount(cart) + 1
rule: removeItem(addItem(empty, x), x) == empty
rule: totalPrice(addItem(cart, item)) == totalPrice(cart) + item.price

-- 3. Rules become property tests
forAll(item -> assertEquals(itemCount(addItem(empty, item)), 1))
forAll(cart, item -> assertEquals(totalPrice(addItem(cart, item)), totalPrice(cart) + item.price))

-- 4. Implement naive version, run tests, then optimize
```

---

## 9. Design Heuristics

1. **Don't start with an implementation.** Rules first, code second.
2. **Simple rules indicate good decomposition.** Complex rules mean coarse building blocks.
3. **Every new operation needs rules connecting it to existing ones.** Isolated operations indicate missing relationships.
4. **Look for algebraic structures.** Associative? Look for default. Default found? Check for commutativity or inverses. Each upgrade brings new rules.
5. **Generalize by removing type constraints.** If rules don't mention a specific type, parameterize.
6. **Build naive first, optimize second.** Generate tests from naive implementation, then build optimized one against those tests.
7. **Invariants belong in types, not business logic.** When rules require commutativity but data structure is ordered, change the data structure.
