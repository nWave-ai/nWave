---
name: nw-fp-usable-design
agent: nw-functional-software-crafter
description: Naming conventions, API ergonomics, and usability patterns for functional code
user-invocable: false
disable-model-invocation: true
---

# FP Usable Design

Make functional code usable. The developer is the user of your design. Apply usability thinking to code organization, naming, and architecture.

Cross-references: [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md) | [fp-hexagonal-architecture](../nw-fp-hexagonal-architecture/SKILL.md) | [fp-algebra-driven-design](../nw-fp-algebra-driven-design/SKILL.md)

---

## 1. Core Insight

[STARTER]

The user of software design is the developer, not the end user. When developers struggle, blame the design, not the people. Pressure, team churn, unclear specs, and noisy environments produce unusable designs. Improve the design.

---

## 2. Five Evaluation Goals

[STARTER]

| Goal | What It Means | How to Assess |
|---|---|---|
| **Learnability** | How quickly a new developer becomes productive | Timed tasks for unfamiliar developers |
| **Efficiency** | How fast common tasks are performed | Count unnecessary navigation and decisions |
| **Memorability** | How easily proficiency returns after time away | What do returning developers re-learn? |
| **Error resistance** | How many bugs the design induces | Track bug locations; ask "what design change prevents this category?" |
| **Satisfaction** | How pleasant to work in the codebase | Developer interviews, retrospectives |

---

## 3. Naming Conventions

[STARTER]

### Domain Language in Function Names

Use domain expert's vocabulary, not mathematical conventions or technical jargon. No `OrderFactory`, `OrderManager`, `OrderHelper`.

### Verb-Noun for Transformations (Pipeline-Friendly)

```
rawOrder
  |> validateOrderFields
  |> enrichWithCustomerData
  |> calculateOrderTotal
  |> applyDiscountRules
  |> generateOrderConfirmation
```

### Predicate Functions Use Question-Style Names

```
isActiveCustomer     -- not: checkActive, activeP
hasShippingAddress   -- not: shippingAddr, addrCheck
canPlaceOrder        -- not: orderOk, validateOrderBool
```

### When Short Names Are Acceptable

Single-letter names appropriate only in: library internals and generic utilities | lambda parameters in trivial operations | type variables | mathematical domains where convention IS domain language.

### Lifecycle Prefixes

Types at different workflow stages get prefixed: `UnvalidatedOrder`, `ValidatedOrder`, `PricedOrder`. Stage immediately visible in any type signature.

### Error Type Naming

Named after what went wrong, scoped to context: `ValidationError`, `PricingError`. Pipeline-level: `PlaceOrderError` (choice type unifying step errors).

---

## 4. Feature-Oriented Organization

[STARTER]

Organize by feature domain rather than technical layer.

**Instead of** (technical layers):
```
controllers/
services/
models/
```

**Use** (feature domains):
```
auth/
speakers/
speakers/profile/
order/
```

**When**: Developers frequently need to find and modify all code related to a specific feature.
**Why**: When something changes in "call for speakers," it's obvious where to look. Technical layering scatters related code across entire codebase.

### Module Organization Within a Feature

- Simple types at top (no dependencies)
- Compound domain types in middle
- Aggregates and workflow types at bottom
- Types and functions in same file or types-first, functions-second

---

## 5. Navigability as First-Class Concern

[STARTER]

Typical developer workflow (find, navigate, read, write, test) executes hundreds of times per day. Small improvements compound.

**Eliminate**: Long methods requiring scrolling | unclear method names forcing reading implementations | tests unrelatable to features | inconsistent placement of similar logic.

**Naming as navigation**: Consistent patterns where suffix/prefix indicates design role. Names precise enough that search yields 3-4 results at most. IDE-friendly casing enables fast jump-to.

**Why**: Navigability is quasi-ignored with enormous cumulative impact.

---

## 6. Design Elements (Constrained Roles)

[INTERMEDIATE]

Define constrained roles for your codebase. Each role specifies: responsibilities, allowed collaborators, and testing approach.

| Role | Responsibilities | Can Call | Test With |
|---|---|---|---|
| Controller | Delegates operations, renders views | Services, Command Objects | Component tests |
| Command Object | Validates input, delegates writes | Database services, queries | Unit tests |
| Application Service | Orchestrates business logic | Commands, other services | Integration tests |
| Database Query | Read-only data access | Database only | Unit tests |
| View Model | Shapes data for presentation | Nothing | Unit tests |

**Why**: Makes design "easy to use correctly, hard to use incorrectly." Controller can't write to database, so database bugs can't originate in Controllers.

**Rules for design elements**:
- Derive after building 10+ features, not upfront
- Cover 80% of cases; handle exceptions case-by-case
- Review periodically as product evolves
- Make compliance easier than deviation (samples, generators, testing support)

---

## 7. Constraints as Clarity

[INTERMEDIATE]

Deliberately restrict what each component can do. Constrain both behavior (what a thing does) and collaboration (what it can call).

**Why**: Unconstrained components express too much. Good abstractions restrict possibilities to make remaining ones clearer. Immutability is a prime example.

**When a use case doesn't fit**: Extract into separate module with its own consistency rules rather than polluting main design.

---

## 8. Root-Cause Bugs in the Design

[INTERMEDIATE]

Ask "what design change prevents this category of bug?" rather than fixing individual instances. Track bug-prone areas and redesign them.

**Fear of making changes signals design problem**: unclear side effects | missing tests | tangled responsibilities. Fixing individual bugs without addressing design guarantees recurrence.

See [fp-algebra-driven-design](../nw-fp-algebra-driven-design/SKILL.md) section 5 for algebraic contradiction analysis.

---

## 9. Prescribed Testing Strategy

[INTERMEDIATE]

Assign testing approach to each design element role. Controllers get component tests. Command objects get unit tests. Removes "how should I test this?" decision entirely.

**Why**: Reduces decision fatigue. Tests also document and enforce what each role should do.

---

## 10. Usability Testing the Design

[ADVANCED]

Apply UX research techniques to your codebase:

| Technique | Application |
|---|---|
| Developer interviews | What was hard? Confusing? Risky? |
| Personas | Developer profiles (skill level, domain knowledge, tool familiarity) |
| Flow analysis | Map steps for common tasks; identify bottlenecks |
| Timed tasks | Give unfamiliar developers specific tasks; observe friction |
| Continuous feedback | Retrospectives and root-cause analysis as ongoing design feedback |

---

## Decision Tree: How to Organize This Module?

```
Does this module represent a feature domain?
  YES --> Feature-oriented folder (auth/, order/, speakers/)
    Does the feature have sub-features?
      YES --> Nested feature folders (speakers/profile/)
      NO --> Single feature folder
  NO --> Is it shared infrastructure?
    YES --> Infrastructure folder, organized by capability
    NO --> Is it a cross-cutting concern?
      YES --> Shared module, referenced by feature modules
      NO --> Evaluate whether it belongs in an existing feature
```

---

## 11. Design Heuristics

1. **Blame the design, not the people** -- foundational heuristic
2. **No best practices, only contextual practices** -- SOLID helps when you need low cost of change; skip it otherwise
3. **Constraints enable creativity** -- limiting what a component can do leads to more focused solutions
4. **Improve incrementally** -- use the imperfect name now, improve next time you can't find it
5. **Action over analysis** -- make things work first, then refine structure
6. **Consistency at module level** -- system-wide conceptual integrity is hard; module-level consistency is practical

---

## 12. Combining with Other Patterns

**Design Elements + Algebraic Rules**: Each element's constraints ("a Controller can only call Services") are formalizable as algebraic rules, making constraints machine-checkable. See [fp-algebra-driven-design](../nw-fp-algebra-driven-design/SKILL.md). Example: `imports(controllerModule) intersect dbModules == empty`.

**Navigability + Simple Rules**: Algebraic decomposition produces small, orthogonal operations with simple rules. Small operations are easy to name well. Example: `applyDiscount` and `calculateTax` are instantly searchable; `processOrder` is not.

**Feature Organization + Domain Modeling**: Feature folders align with bounded contexts. Each feature owns its domain types and workflows. See [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md). Example: `order/types.fs`, `order/validate.fs`, `order/price.fs`.

**Prescribed Testing + Property-Based Testing**: Design elements prescribe WHAT kind of test. PBT prescribes HOW to write those tests as properties. Example: Command objects get conservation properties (`forAll(order -> totalOf(applyDiscount(order)) <= totalOf(order))`). Controllers get round-trip properties.
