---
name: nw-fp-hexagonal-architecture
agent: nw-functional-software-crafter
description: Hexagonal architecture patterns with pure core and side-effect shell for functional codebases
user-invocable: false
disable-model-invocation: true
---

# FP Hexagonal Architecture

Ports and adapters in functional programming. Structure applications with a pure core and side-effect shell.

Cross-references: [fp-principles](../nw-fp-principles/SKILL.md) | [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md) | [fp-usable-design](../nw-fp-usable-design/SKILL.md)

---

## 1. The Natural Fit

[STARTER]

Functional architecture naturally implements ports and adapters. The paradigm's separation of pure functions from side effects IS the hexagonal boundary.

| OOP Concept | FP Equivalent | Why |
|---|---|---|
| Port (interface) | Function type signature / type alias | Port defines contract; function signature IS that contract |
| Adapter (class) | Concrete function implementation | Adapter fulfills contract; matching function does same |
| DI container | Function parameters / partial application | Dependencies passed as arguments, no container needed |
| Domain service class | Module of pure functions | Related pure functions replace stateful service object |
| Entity with behavior | Immutable data + functions operating on it | Data and behavior separated; functions transform immutable values |

---

## 2. Pure Core / Side-Effect Shell

[STARTER]

All business logic is pure; all side effects live at the system's edges.

**The Sandwich Pattern**: Read (impure) -> Decide (pure) -> Write (impure)

```
+--------------------------------------------------+
|  Side-Effect Shell (thin)                        |
|  - HTTP handlers, CLI, message consumers         |
|  - Database access, file I/O, network calls      |
|  - Reads data, calls core, writes results        |
|                                                  |
|  +--------------------------------------------+ |
|  |  Pure Core (large)                          | |
|  |  - Pure functions only                      | |
|  |  - Domain logic, validation, calculation    | |
|  |  - No I/O, no side effects                  | |
|  |  - Immutable data transformations           | |
|  +--------------------------------------------+ |
+--------------------------------------------------+
```

**Dependency Rule**: Shell may call core. Core never calls shell. Core is unaware of shell's existence.

**Why**: Pure core is trivially testable (no mocks, no setup, no teardown). Shell is thin and needs few integration tests.

---

## 3. Ports as Function Types

[STARTER]

A port is a function type signature describing a capability the domain needs:

```
FindOrder    : OrderId -> AsyncResult<Order option>
SaveOrder    : Order -> AsyncResult<unit>
SendEmail    : Email -> AsyncResult<unit>
GetPrice     : ProductCode -> Price
CheckExists  : ProductCode -> bool
```

**When to define**: Domain needs a capability involving I/O or external systems. Domain declares WHAT; adapter provides HOW.

**Naming**: Verb-noun. Name describes capability, not technology.

---

## 4. Adapters as Implementations

[STARTER]

An adapter is a concrete function matching a port's type signature:

```
PostgresOrderRepo.findOrder  : OrderId -> AsyncResult<Order option>
InMemoryOrderRepo.findOrder  : OrderId -> AsyncResult<Order option>
```

Both match the `FindOrder` port. Domain doesn't know which is used.

---

## 5. Dependency Injection via Functions

[STARTER] -> [INTERMEDIATE] -> [ADVANCED]

### Decision Tree: How to Inject This Dependency?

```
How many dependencies does the function need?
  1-3 --> [STARTER] Functions as Parameters
  4-6 --> [INTERMEDIATE] Consider Environment Pattern or grouping
  7+  --> [ADVANCED] Capability Interfaces or Effect System
         (also: reconsider function responsibilities)
```

### [STARTER] Functions as Parameters

Pass dependencies as function parameters. Partially apply at composition root.

```
placeOrder (findCustomer) (saveOrder) (rawOrder) = ...
placeOrderHandler = placeOrder Database.findCustomer Database.saveOrder
```

### [INTERMEDIATE] Environment Pattern (Reader)

Dependencies in a record, provided once at top level. Use when parameter threading becomes painful (4+ deps).

```
placeOrder (rawOrder) = reader { env = ask(); env.findCustomer(rawOrder.customerId) ... }
placeOrder(rawOrder) |> runWith(productionEnv)
```

### [ADVANCED] Capability Interfaces / Effect Systems

Abstract over effect types (tagless final) or use fine-grained effect tracking (ZIO, Koka). Use for large codebases with many effects.

### Recommendation by Context

| Context | Approach |
|---|---|
| Small/medium codebase | Functions as parameters |
| Large codebase, many effects | Capability interfaces or effect system |
| Pragmatic TypeScript/F# | Functions as parameters + modules |

---

## 6. Pipeline Composition Through Architecture

[INTERMEDIATE]

Workflows flow through architecture as pipelines:

```
HTTP Request
  -> Parse (shell: impure)
  -> Validate (core: pure)
  -> Calculate (core: pure)
  -> Persist (shell: impure)
  -> Respond (shell: impure)
```

Each pure step is a function in the pipeline. Shell handles I/O at start and end.

**Error-track pipelines**: Each step returns Result type; pipeline short-circuits on first failure. See [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md).

**Collect-all-errors**: When you need ALL validation errors, use Applicative style. See [fp-principles](../nw-fp-principles/SKILL.md) section 5.

---

## 7. Testing Strategy

[INTERMEDIATE]

| Layer | Test Type | Volume | Speed | Mocks |
|---|---|---|---|---|
| Pure core (domain) | Unit + Property-based | Many | Fast (ms) | None |
| Composition root | Integration (wiring) | Few | Medium | None |
| Adapters | Integration | Few per adapter | Slow | None (real deps) |
| End-to-end | System tests | Very few | Slowest | None |

**Key insight**: Pure functions need no mocking. Input in, output out. Strongest practical argument for maximizing the pure core.

**Property-based testing** is the natural companion. Define rules that hold for all valid inputs. See [fp-algebra-driven-design](../nw-fp-algebra-driven-design/SKILL.md).

---

## 8. Side Effect Management Approaches

[ADVANCED]

| Approach | Enforcement | Granularity | Best For |
|---|---|---|---|
| Convention (discipline) | None | N/A | Any language, small teams |
| IO Type (Haskell) | Compile-time | Binary (pure/impure) | Haskell |
| Effect Systems (ZIO, Koka) | Compile-time | Per-effect | Large systems |
| Pure Core / Shell | Architectural | Module-level | Any language, pragmatic |

**IO actions as values**: Side effects are descriptions of actions, not actions themselves. Can be stored, composed, and only execute when runtime reaches them.

**Type-level effect tracking**: Mark impure functions clearly -- through return types, naming conventions, or annotations. Even without compiler enforcement, the discipline applies.

---

## 9. Combining Patterns

```
Domain Wrappers + Smart Constructors (fp-domain-modeling)
        |
        v
Choice Types for State Machines -----> Error-Track Pipelines
        |                                       |
        v                                       v
Pure Core / Side-Effect Shell ---------> Functions as Parameters (DI)
        |                                       |
        v                                       v
Pipeline Composition <-----------------  Property-Based Testing
```

### Worked Example: Place Order Workflow

```
-- Ports (function signatures)
FindCustomer : CustomerId -> AsyncResult<Customer>
SaveOrder    : Order -> AsyncResult<Unit>

-- Pure Core (domain logic)
validateOrder : RawOrder -> Result<ValidOrder, ValidationError>
priceOrder    : ValidOrder -> PricedOrder

-- Pipeline (Pure Core + Error Pipeline + DI via parameters)
placeOrder (findCustomer) (saveOrder) (raw) =
    raw
    |> validateOrder                     -- pure, Result
    |> bindAsync (o -> findCustomer o.customerId |> map (c -> (o, c)))  -- port call
    |> map (fun (o, c) -> priceOrder o)  -- pure
    |> bindAsync saveOrder               -- port call
```

**Recommended learning sequence**:

[STARTER]: Pure Core/Shell -> Domain Wrappers -> Smart Constructors -> Pipeline Composition

[INTERMEDIATE]: Choice Types -> Error-Track Pipelines -> Functions as Parameters -> Property Testing

[ADVANCED]: Capability Interfaces -> Effect Systems -> Collect-All-Errors Validation
