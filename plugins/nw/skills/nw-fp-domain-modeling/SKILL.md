---
name: nw-fp-domain-modeling
agent: nw-functional-software-crafter
description: Domain modeling with algebraic data types, smart constructors, and type-level error handling
user-invocable: false
disable-model-invocation: true
---

# FP Domain Modeling

Domain modeling with types. Make illegal states unrepresentable, workflows as pipelines, error handling at the type level.

Cross-references: [fp-principles](../nw-fp-principles/SKILL.md) | [fp-hexagonal-architecture](../nw-fp-hexagonal-architecture/SKILL.md) | [fp-algebra-driven-design](../nw-fp-algebra-driven-design/SKILL.md)

---

## 1. The Two Building Blocks

[STARTER]

All domain types compose from two operations:

- **AND (Record Types)**: Value has ALL of these fields. Order requires CustomerInfo AND ShippingAddress AND OrderLines.
- **OR (Choice Types)**: Value is ONE OF these alternatives. ProductCode is either WidgetCode OR GizmoCode.

Combined recursively, these express virtually any domain structure.

---

## 2. Domain Wrappers for Primitives

[STARTER]

Never use primitives directly in the domain model. Each domain concept gets its own wrapper type.

**What**: Wrap primitives so the compiler distinguishes CustomerId from OrderId.
**When**: Every primitive with domain meaning.
**Why**: Prevents accidental mixing (compiler rejects comparing CustomerId with OrderId). Each wrapper carries its own validation rules. The type name IS the documentation.

---

## 3. Validated Construction (Smart Constructors)

[STARTER]

Raw constructor is private. A `create` function validates input and returns a Result type, making validation failure explicit.

**Pattern**: UnitQuantity must be between 1 and 1000. Its `create` function rejects values outside that range. A companion `value` function provides read access to the inner primitive.

**When**: Every domain wrapper with validation rules.
**Why**: Once constructed, a value is guaranteed valid. No defensive checks deeper in the code.

---

## 4. Making Illegal States Unrepresentable

[STARTER]

The central design guideline. Instead of flags and runtime checks, model the domain so invalid states cannot be constructed.

### Replace Flags with Distinct Types

Instead of `{ EmailAddress; IsVerified: bool }`, create separate `VerifiedEmailAddress` and `UnverifiedEmailAddress` types. Functions requiring verification take `VerifiedEmailAddress`, making misuse a compile error.

### Replace Optional Fields with Choice Types

Instead of `{ Email: option; Address: option }` (where both could be None), create: `EmailOnly | AddressOnly | EmailAndAddress`. The "at least one required" rule becomes structurally enforced.

### NonEmptyList for "At Least One" Rules

Define a type guaranteeing at least one element. Order with `OrderLines: NonEmptyList<OrderLine>` cannot have zero lines.

---

## 5. Workflows as Functions

[STARTER]

Every business workflow is a single function: Command in, Events out.

```
PlaceOrderWorkflow : PlaceOrderCommand -> AsyncResult<PlaceOrderEvent list>
```

### Pipeline Composition

Workflows decompose into steps, each transforming one document type into the next:

```
UnvalidatedOrder -> ValidatedOrder -> PricedOrder -> Events
```

Each step is stateless, pure, has single input/output type, and is independently testable. The workflow assembles by piping steps together.

**Why**: Pipeline makes the business process visible. Each step name is a domain concept.

---

## 6. Document Lifecycle as State Types

[INTERMEDIATE]

Rather than one Order type with flags, create separate types for each lifecycle stage:

- `UnvalidatedOrder` (raw input, all fields strings)
- `ValidatedOrder` (all fields checked)
- `PricedOrder` (prices calculated)

A top-level Order choice type unifies all states. New states (e.g., `Refunded`) added without breaking existing code.

**When**: Domain entities with distinct lifecycle stages where different data is available at each stage.

---

## 7. State Machines with Types

[INTERMEDIATE]

When an entity has distinct states with different data and different allowed operations, model each state as a separate type.

```
ShoppingCart = EmptyCart | ActiveCart of ActiveCartData | PaidCart of PaidCartData
```

Transition functions take the choice type, pattern-match on current state, return new state.

**Benefits**: All states explicit | each state has own data | invalid transitions prevented by types | pattern matching warnings reveal unhandled edge cases.

---

## 8. Error-Track Pipelines (Railway Pattern)

[INTERMEDIATE]

Each function returns a Result type. Pipeline short-circuits on first failure.

```
rawInput
  |> validateOrder           -- Result<ValidOrder, Error>
  |> bind calculateTotal     -- Result<PricedOrder, Error>
  |> bind checkInventory     -- Result<ConfirmedOrder, Error>
  |> bind chargePayment      -- Result<PaidOrder, Error>
  |> map generateReceipt     -- Result<Receipt, Error>
```

**Key combinators**:
- **map**: Transform success value (one-track into two-track)
- **bind**: Chain a function that itself returns Result
- **mapError**: Transform error value
- **tee**: Perform side effect without changing value (logging)

### Error Classification

| Category | Examples | Strategy |
|---|---|---|
| Domain Errors | Validation failure, out of stock | Model as types, return via Result |
| Panics | Out of memory, null reference | Throw exceptions, catch at top level |
| Infrastructure Errors | Network timeout, auth failure | Case-by-case |

### Unifying Error Types

Each step may have its own error type. Define a common error choice type and use `mapError` to lift step errors before composing.

### Collecting All Errors (Applicative Validation)

[ADVANCED]

Standard bind short-circuits on first error. For validation where you want ALL errors, use Applicative style -- runs all validations and accumulates errors into a list. See [fp-principles](../nw-fp-principles/SKILL.md) section 5.

**When**: Form validation | batch input checking | any place user needs all errors at once.

---

## 9. Modeling Dependencies

[INTERMEDIATE]

Each workflow step declares exactly the functions it needs as parameters:

```
CheckProductCodeExists : ProductCode -> bool
GetProductPrice        : ProductCode -> Price
```

**Convention**: Dependencies first in parameter list, primary input last. Enables partial application (functional DI).

**Public vs. internal**: Top-level workflow hides dependencies from callers. Internal steps make them explicit.

See [fp-hexagonal-architecture](../nw-fp-hexagonal-architecture/SKILL.md) section 5 for full DI decision tree.

---

## 10. Persistence Ignorance

[INTERMEDIATE]

Domain model has no awareness of databases. Two distinct type hierarchies:

- **Domain types**: Rich, nested, use choice types, validated wrappers. Not serialization-friendly.
- **DTO types**: Flat, primitives, nullable, arrays. Designed for serialization.

### Conversion Pattern

- **fromDomain**: Domain -> DTO. Always succeeds.
- **toDomain**: DTO -> Result<Domain, Error>. May fail (validation happens here).

### Serialization as Pipeline Steps

```
JSON -> deserialize -> DTO -> toDomain -> [WORKFLOW] -> fromDomain -> DTO -> serialize -> JSON
```

Domain workflow never sees JSON or DTOs directly.

---

## 11. Bounded Contexts

[ADVANCED]

Each context has its own dialect of domain language. Contexts communicate only through events and DTOs. Design for autonomy.

**Trust boundaries**: Input gate validates and converts incoming DTOs to domain types. Output gate converts domain types to DTOs, deliberately dropping private information.

**Inter-context relationships**: Shared Kernel (shared design) | Customer/Supplier (downstream defines contract) | Anti-Corruption Layer (translator preventing external model from corrupting internal domain).

---

## Decision Tree: How to Model This Domain Concept?

```
Is it a simple value with validation rules?
  YES --> Domain Wrapper + Smart Constructor
  NO -->
    Does it represent one of several alternatives?
      YES --> Choice Type (sum type)
      NO -->
        Does it group several values together?
          YES --> Record Type (product type)
          NO -->
            Does it have distinct lifecycle stages?
              YES --> State Machine with Types (section 7)
              NO -->
                Is it an operation that transforms data through stages?
                  YES --> Workflow Pipeline (section 5)
                  NO --> Evaluate whether it needs modeling at all
```

---

## 12. Key Design Heuristics

1. **Start from events and workflows**, not data structures
2. **Let the domain expert drive naming** -- their vocabulary, not technical jargon
3. **Use types to enforce business rules at compile time** -- every rule in the type system needs no unit test
4. **Document effects in signatures** -- Result for errors | Async for I/O | Option for missing data
5. **Separate domain types from serialization types** -- domain is pure; serialization is infrastructure
6. **Prefer explicit over implicit** -- every input and dependency is a function parameter

### Naming Patterns

- **Types as nouns**: Order | ProductCode | CustomerInfo
- **Workflows as verbs**: ValidateOrder | PriceOrder | PlaceOrder
- **Events in past tense**: OrderPlaced | OrderShipped
- **Commands in imperative**: PlaceOrder | ShipOrder | CancelOrder
- **Lifecycle prefixes**: UnvalidatedOrder | ValidatedOrder | PricedOrder
