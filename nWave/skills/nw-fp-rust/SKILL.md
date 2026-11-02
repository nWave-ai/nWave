---
name: nw-fp-rust
agent: nw-functional-software-crafter
description: Rust language-specific patterns, compiler-verified exhaustive ADTs, and Result/Option as railway-oriented programming
user-invocable: false
disable-model-invocation: true
---

# FP in Rust -- Functional Software Crafter Skill

Cross-references: [fp-principles](../nw-fp-principles/SKILL.md) | [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md) | [pbt-rust](../nw-pbt-rust/SKILL.md)

## When to Choose Rust

- Best for: making illegal states unrepresentable at the TYPE level, with the compiler enforcing it | systems
  where a wrong state must be a compile error, not a runtime one | performance-critical domain cores
- Not ideal for: teams needing the fastest possible prototyping loop | domains where the borrow checker's
  learning cost outweighs the safety gain (short-lived scripts, throwaway tooling)

## [STARTER] Quick Setup

```bash
cargo new order_service && cd order_service
# Add proptest or quickcheck as a dev-dependency for property-based testing
cargo build && cargo test
```

**Test runner**: `cargo test`. Add `proptest = "1"` (or `quickcheck`) under `[dev-dependencies]`.

## [STARTER] Type System for Domain Modeling

Rust's `enum` is a REAL algebraic sum type with payload per variant, and the compiler REFUSES to compile a
`match` that omits a case -- this is not a lint, it is a hard error. No other mainstream systems language makes
illegal states this unrepresentable by default.

### Choice Types (Enums with Payload)

```rust
enum PaymentMethod {
    CreditCard { number: CardNumber, expiry: ExpiryDate },
    BankTransfer { account: AccountNumber },
    Cash,
}
```

### Record Types and Domain Wrappers (Newtype Pattern)

```rust
struct Customer {
    customer_id: CustomerId,
    customer_name: CustomerName,
    customer_email: EmailAddress,
}

struct OrderId(u64);
struct EmailAddress(String); // private field -- see smart constructor below
```

A tuple struct with a PRIVATE field is Rust's newtype: `EmailAddress` is a distinct type from `String` at compile
time, zero runtime cost, and no way to construct one outside its own module.

### [INTERMEDIATE] Smart Constructors

```rust
pub struct EmailAddress(String);

impl EmailAddress {
    pub fn new(raw: &str) -> Result<Self, ValidationError> {
        if raw.contains('@') {
            Ok(EmailAddress(raw.to_string()))
        } else {
            Err(ValidationError::InvalidEmail(raw.to_string()))
        }
    }
}
```

The tuple field stays private to the module (no `pub` on `String`); every construction path outside the module
goes through `new`, which returns evidence (`Result`), never a bare bool.

## [INTERMEDIATE] Composition Style

### `?` Operator for Railway Chaining

```rust
fn place_order(raw: RawOrder) -> Result<Confirmation, OrderError> {
    let validated = validate_order(raw)?;
    let priced = price_order(validated)?;
    confirm_order(priced)
}
```

`?` propagates an `Err` immediately (returning it from the enclosing function) or unwraps an `Ok` and continues --
the SAME railway shape as `bind`, spelled as a postfix operator the compiler understands natively.

### `Result`/`Option` Combinators

```rust
fn total_after_discount(order: &Order) -> Option<Money> {
    order
        .subtotal()
        .checked_sub(order.discount())
        .filter(|total| *total >= Money::ZERO)
}
```

`map`, `and_then` (`Result`'s `bind`), `filter`, `unwrap_or` -- the same vocabulary as Haskell's `Maybe`/`Either`,
under names chosen for readability over category-theory precedent.

### Accumulating Validation Errors

```rust
fn validate_customer(raw: &RawCustomer) -> Result<Customer, Vec<ValidationError>> {
    let name = validate_name(&raw.name);
    let email = validate_email(&raw.email);
    match (name, email) {
        (Ok(n), Ok(e)) => Ok(Customer { name: n, email: e }),
        (n, e) => Err([n.err(), e.err()].into_iter().flatten().collect()),
    }
}
```

`?` short-circuits on the first error; collect explicitly with a tuple match (or the `validator`/`garde` crates)
when the caller needs every failure, not just the first.

## [INTERMEDIATE] Effect Management

Rust has no `IO` type -- effects are ordinary function calls, and PURITY is a discipline the type signature
documents by what it takes and returns, not something the compiler enforces the way Haskell's `IO` does. `async
fn` marks a function that MAY suspend on I/O; ownership (`&self` vs `&mut self` vs consuming `self`) documents
mutation.

```rust
// Pure domain logic -- no I/O, no interior mutability
fn calculate_discount(order: &Order) -> Discount {
    if order.lines().len() > 10 { Discount(0.1) } else { Discount(0.0) }
}

// Effectful boundary -- async, explicit dependency injection
async fn save_order(repo: &impl OrderRepository, order: Order) -> Result<(), OrderError> {
    repo.save(order).await
}
```

### [ADVANCED] Ports as Traits, Adapters as Impls (Hexagonal Architecture)

```rust
#[async_trait]
trait OrderRepository {
    async fn find_order(&self, id: OrderId) -> Option<Order>;
    async fn save_order(&self, order: Order) -> Result<(), OrderError>;
}

struct PostgresOrderRepository { pool: PgPool }

#[async_trait]
impl OrderRepository for PostgresOrderRepository {
    async fn find_order(&self, id: OrderId) -> Option<Order> {
        sqlx::query_as("SELECT * FROM orders WHERE id = $1").bind(id.0).fetch_optional(&self.pool).await.ok()?
    }
    async fn save_order(&self, order: Order) -> Result<(), OrderError> {
        sqlx::query("INSERT INTO orders ...").execute(&self.pool).await.map(|_| ()).map_err(Into::into)
    }
}
```

A `trait` is the port; the domain core is generic over `impl OrderRepository` (or holds a `Box<dyn
OrderRepository>`), so tests substitute an in-memory implementation with no framework needed.

## [INTERMEDIATE] Testing

**Frameworks**: proptest (composable strategies, Hypothesis-like) | quickcheck (closer to the original Haskell
API) | `cargo test` (built-in, table-driven by convention). See [pbt-rust](../nw-pbt-rust/SKILL.md) for detailed
PBT patterns.

### Property Test Example (proptest)

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn round_trips_through_serialization(order in order_strategy()) {
        prop_assert_eq!(deserialize(&serialize(&order)), Ok(order));
    }

    #[test]
    fn validated_orders_always_have_a_positive_total(raw in raw_order_strategy()) {
        if let Ok(validated) = validate_order(raw) {
            prop_assert!(validated.total() > Money::ZERO);
        }
    }
}
```

### Custom Strategy

```rust
fn email_strategy() -> impl Strategy<Value = EmailAddress> {
    ("[a-z]{1,10}", "[a-z]{1,8}")
        .prop_map(|(user, domain)| EmailAddress::new(&format!("{user}@{domain}.com")).unwrap())
}
```

## [ADVANCED] Idiomatic Patterns

### Typestate for Compile-Time-Checked Lifecycles

```rust
struct Order<State> { data: OrderData, _state: PhantomData<State> }
struct Unvalidated;
struct Validated;
struct Priced;

impl Order<Unvalidated> {
    fn validate(self) -> Result<Order<Validated>, OrderError> { /* ... */ }
}
impl Order<Validated> {
    // price_order only exists on Order<Validated> -- calling it on
    // Order<Unvalidated> is a COMPILE ERROR, not a runtime check.
    fn price(self) -> Order<Priced> { /* ... */ }
}
```

The zero-sized `PhantomData<State>` marker makes an illegal call sequence a type error, the same guarantee
Haskell's GADT state machine gives, without a language extension.

### `From`/`TryFrom` for Fallible Conversion Boundaries

```rust
impl TryFrom<RawOrder> for ValidatedOrder {
    type Error = ValidationError;
    fn try_from(raw: RawOrder) -> Result<Self, Self::Error> { validate_order(raw) }
}
```

## Maturity and Adoption

- **Borrow checker learning curve is real**: budget extra ramp-up time for teams new to ownership; it front-loads
  design decisions other languages defer to runtime GC.
- **Async ecosystem fragmentation**: tokio vs async-std vs smol are not fully interoperable; pick one runtime
  project-wide, do not mix.
- **Compile times**: large workspaces compile slowly relative to Go or JVM incremental builds; `cargo check`
  during development, full `cargo build` before commit.

## Common Pitfalls

1. **`unwrap()`/`expect()` in domain logic**: acceptable in tests and truly-impossible-to-fail invariants only;
   production paths return `Result`/`Option` and let the caller decide.
2. **Fighting the borrow checker with `.clone()`**: a correctness fix that hides a real ownership design question;
   prefer restructuring data flow (pass by reference, return owned data) over reflexive cloning.
3. **`unsafe` as a first resort**: nearly every domain-modeling problem has a safe solution; reach for `unsafe`
   only for FFI or a measured, documented performance requirement.
4. **Stringly-typed IDs**: `String` for every identifier defeats the newtype pattern this skill leads with --
   wrap each concept so `CustomerId` and `OrderId` cannot be swapped by the compiler's own type checker.
