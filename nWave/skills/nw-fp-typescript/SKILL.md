---
name: nw-fp-typescript
agent: nw-functional-software-crafter
description: TypeScript language-specific patterns with fp-ts/Effect, discriminated unions, and railway-oriented error handling
user-invocable: false
disable-model-invocation: true
---

# FP in TypeScript -- Functional Software Crafter Skill

Cross-references: [fp-principles](../nw-fp-principles/SKILL.md) | [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md) | [pbt-typescript](../nw-pbt-typescript/SKILL.md)

## When to Choose TypeScript

- Best for: teams already on the Node/browser ecosystem wanting FP DISCIPLINE without a new runtime | full-stack
  projects sharing domain types between client and server | the most common first encounter with FP for many
  engineers
- Not ideal for: teams wanting the compiler to ENFORCE purity (TS purity is a convention, `any`/`as` can always
  escape it) | CPU-bound work needing a stricter type system's exhaustiveness guarantees

## [STARTER] Quick Setup

```bash
mkdir order-service && cd order-service && npm init -y
npm install typescript fp-ts --save
npm install --save-dev fast-check vitest
npx tsc --init --strict
```

**Test runner**: Vitest or Jest. `"strict": true` in `tsconfig.json` is load-bearing -- without it, `null`/
`undefined` silently widen every type and most patterns below lose their guarantee.

## [STARTER] Type System for Domain Modeling

### Choice Types (Discriminated Unions)

```typescript
type PaymentMethod =
  | { readonly _tag: "CreditCard"; readonly cardNumber: string; readonly expiryDate: string }
  | { readonly _tag: "BankTransfer"; readonly accountNumber: string }
  | { readonly _tag: "Cash" };
```

The shared `_tag` field is the discriminant: a `switch` on `_tag` narrows the union per-branch, and with
`"strict": true` a missing case is a compile error via the `never` exhaustiveness check below.

### Record Types and Branded Domain Wrappers

```typescript
interface Customer {
  readonly customerId: CustomerId;
  readonly customerName: CustomerName;
  readonly customerEmail: EmailAddress;
}

type OrderId = number & { readonly __brand: "OrderId" };
type EmailAddress = string & { readonly __brand: "EmailAddress" };
```

TypeScript has no true newtype -- a branded intersection type is the idiomatic substitute: `OrderId` is
structurally a `number` at runtime (zero cost) but the `__brand` phantom field stops the compiler from accepting
a bare `number` where an `OrderId` is expected.

### [INTERMEDIATE] Smart Constructors

```typescript
import { Either, left, right } from "fp-ts/Either";

function mkEmailAddress(raw: string): Either<ValidationError, EmailAddress> {
  return raw.includes("@")
    ? right(raw as EmailAddress)
    : left({ _tag: "InvalidEmail", raw });
}
```

The brand cast (`as EmailAddress`) happens ONLY inside the smart constructor -- callers never cast directly, so
every `EmailAddress` in scope has passed `mkEmailAddress`.

## [INTERMEDIATE] Composition Style

### `pipe` for Left-to-Right Composition

```typescript
import { pipe } from "fp-ts/function";
import * as E from "fp-ts/Either";

const placeOrder = (raw: RawOrder): Either<OrderError, Confirmation> =>
  pipe(raw, validateOrder, E.chain(priceOrder), E.chain(confirmOrder));
```

`E.chain` is `Either`'s `bind` -- short-circuits on `Left`, threads the `Right` value forward.

### Effect (the newer alternative to fp-ts)

```typescript
import { Effect } from "effect";

const placeOrder = (raw: RawOrder): Effect.Effect<Confirmation, OrderError> =>
  Effect.gen(function* () {
    const validated = yield* validateOrder(raw);
    const priced = yield* priceOrder(validated);
    return yield* confirmOrder(priced);
  });
```

Generator-based `Effect.gen` reads imperatively while remaining a pure DESCRIPTION of the computation until
`Effect.runPromise`/`runSync` actually executes it -- the same "build a value, run it at the edge" discipline
Haskell's `IO` enforces at the type level.

### Accumulating Validation Errors

```typescript
import { validate } from "fp-ts/Apply";

const validateCustomer = (raw: RawCustomer) =>
  pipe(
    { name: validateName(raw.name), email: validateEmail(raw.email) },
    ({ name, email }) => E.Do.pipe(E.apS("name", name), E.apS("email", email)),
  );
```

`apS`/Applicative validation collects ALL failures via `Either`'s `Semigroup` on the error side, unlike `chain`
which stops at the first.

## [INTERMEDIATE] Effect Management

Plain TypeScript has no purity enforcement -- `Effect`'s own `Effect<A, E, R>` type is the closest analogue to
Haskell's `IO`: a VALUE describing a computation, not the computation itself, so a function returning
`Effect<Order, never, never>` is provably side-effect-free by its type alone (no ambient `R` requirement, no `E`
to fail with) in a way a bare `Order` return never was.

```typescript
// Pure domain logic -- ordinary function, no Effect wrapper needed
const calculateDiscount = (order: Order): Discount =>
  order.lines.length > 10 ? 0.1 : 0.0;

// Effectful boundary -- Effect<A, E, R> makes the DB dependency explicit in R
const saveOrder = (order: Order): Effect.Effect<void, DbError, OrderRepository> =>
  Effect.gen(function* () {
    const repo = yield* OrderRepository;
    yield* repo.save(order);
  });
```

### [ADVANCED] Ports as Interfaces, Adapters as Layers (Hexagonal Architecture)

```typescript
class OrderRepository extends Context.Tag("OrderRepository")<
  OrderRepository,
  { readonly findOrder: (id: OrderId) => Effect.Effect<Option<Order>>; readonly save: (o: Order) => Effect.Effect<void> }
>() {}

const PostgresOrderRepository = Layer.succeed(OrderRepository, {
  findOrder: (id) => Effect.tryPromise(() => db.query("SELECT * FROM orders WHERE id = $1", [id])),
  save: (order) => Effect.tryPromise(() => db.insert("orders", order)),
});
```

`Context.Tag` is the port; `Layer` provides the adapter. Tests substitute a `Layer.succeed` backed by an in-memory
map, with no framework or DI container needed.

## [INTERMEDIATE] Testing

**Frameworks**: fast-check (property-based, integrates with Vitest/Jest) | Vitest (fast, ESM-native) | `Effect`'s
own `@effect/vitest` for testing `Effect` values directly. See [pbt-typescript](../nw-pbt-typescript/SKILL.md)
for detailed PBT patterns.

### Property Test Example

```typescript
import fc from "fast-check";
import { test } from "vitest";

test("round-trips through serialization", () =>
  fc.assert(fc.property(orderArbitrary, (order) => deserialize(serialize(order)) === order)));

test("validated orders always have a positive total", () =>
  fc.assert(
    fc.property(rawOrderArbitrary, (raw) => {
      const result = validateOrder(raw);
      return E.isLeft(result) || result.right.total > 0;
    }),
  ));
```

### Custom Arbitrary

```typescript
const emailArbitrary: fc.Arbitrary<EmailAddress> = fc
  .tuple(fc.stringMatching(/^[a-z]{1,10}$/), fc.stringMatching(/^[a-z]{1,8}$/))
  .map(([user, domain]) => `${user}@${domain}.com` as EmailAddress);
```

## [ADVANCED] Idiomatic Patterns

### Exhaustiveness Checking via `never`

```typescript
function describe(method: PaymentMethod): string {
  switch (method._tag) {
    case "CreditCard": return `Card ending ${method.cardNumber.slice(-4)}`;
    case "BankTransfer": return `Transfer from ${method.accountNumber}`;
    case "Cash": return "Cash";
    default: {
      const _exhaustive: never = method; // compile error if a case is missing
      return _exhaustive;
    }
  }
}
```

### `Option` Instead of `null`/`undefined`

```typescript
import { Option, some, none, fromNullable } from "fp-ts/Option";

const findCustomer = (id: CustomerId): Option<Customer> =>
  fromNullable(database.get(id));
```

Composes with `map`/`chain` the same way `Either` does, avoiding a `null`-check tree at every call site.

## Maturity and Adoption

- **fp-ts is in low-maintenance mode**: `Effect` is the actively developed successor (built by overlapping
  authors) and is where new projects should start; fp-ts remains fine for existing codebases.
- **Purity is a convention, not enforced**: nothing stops a "pure" function from calling `Date.now()` or
  `Math.random()` inline; code review and the effect-typing discipline above are the only guard.
- **`Effect`'s learning curve is steep**: `Effect<A, E, R>`'s three type parameters and generator syntax take
  longer to internalize than fp-ts's `Either`/`TaskEither` alone; introduce incrementally.

## Common Pitfalls

1. **`as` casts defeating brands**: a branded type (`OrderId`) is only as strong as the discipline never to cast
   an arbitrary `number` into it outside the smart constructor.
2. **Mixing `Promise` and `Effect`/`TaskEither`**: pick one effect representation per boundary; interop
   (`Effect.tryPromise`, `TE.tryCatch`) at the edge, never scattered through domain logic.
3. **`interface` merging surprises**: TypeScript's structural typing means two unrelated interfaces with the same
   shape are interchangeable; branded types (above) are the fix, not a naming convention alone.
4. **Non-exhaustive `switch` without `strict`**: the `never` exhaustiveness check in Idiomatic Patterns only
   fires under `"strict": true`; without it a missing case silently falls through.
