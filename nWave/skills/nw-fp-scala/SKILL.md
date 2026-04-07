---
name: nw-fp-scala
agent: nw-functional-software-crafter
description: Scala 3 language-specific patterns with ZIO, Cats Effect, and opaque types
user-invocable: false
disable-model-invocation: true
---

# FP in Scala 3 -- Functional Software Crafter Skill

Cross-references: [fp-principles](../nw-fp-principles/SKILL.md) | [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md) | [pbt-jvm](../nw-pbt-jvm/SKILL.md)

## When to Choose Scala

- Best for: JVM with full FP power | large-scale systems | data engineering | richest effect ecosystem
- Not ideal for: small teams wanting simplicity | Android (use Kotlin) | teams allergic to OO/FP duality

## [STARTER] Quick Setup

```bash
cs install scala3-compiler scala3-repl sbt
sbt new scala/scala3.g8 && cd order-service
# Add zio, zio-test, scalacheck to build.sbt
sbt compile && sbt test
```

## [STARTER] Type System for Domain Modeling

### Choice Types and Record Types

```scala
enum PaymentMethod:
  case CreditCard(cardNumber: String, expiryDate: String)
  case BankTransfer(accountNumber: String)
  case Cash

case class Customer(
  customerId: CustomerId,
  customerName: CustomerName,
  customerEmail: EmailAddress
)
```

Case classes provide structural equality, copy, and pattern matching for free.

### [STARTER] Domain Wrappers (Opaque Types) -- Zero Cost

```scala
object OrderDomain:
  opaque type OrderId = Int
  object OrderId:
    def apply(value: Int): OrderId = value
  extension (id: OrderId) def value: Int = id

  opaque type EmailAddress = String
  object EmailAddress:
    def from(raw: String): Either[ValidationError, EmailAddress] =
      if raw.contains("@") then Right(raw)
      else Left(InvalidEmail(raw))
```

Inside defining scope, alias is transparent. Outside, only exported operations available.

## [INTERMEDIATE] Composition Style

### For-Comprehensions (Monadic Chaining)

```scala
def placeOrder(raw: RawOrder): Either[OrderError, Confirmation] =
  for
    validated <- validateOrder(raw)
    priced    <- priceOrder(validated)
    confirmed <- confirmOrder(priced)
  yield confirmed
```

### Error Accumulation (Cats Validated or ZIO)

```scala
import cats.data.Validated
import cats.syntax.all.*

def validateCustomer(raw: RawCustomer): ValidatedNel[ValidationError, Customer] =
  (validateName(raw.name), validateEmail(raw.email), validateAddress(raw.address))
    .mapN(Customer.apply)
```

## [ADVANCED] Effect Management

### ZIO vs Cats Effect

ZIO: `ZIO[R, E, A]` with built-in typed errors, DI (ZLayer), batteries-included. Cats Effect: `IO[A]`, minimal type-class-based, Typelevel ecosystem (http4s, FS2, Doobie). Pick one and stay consistent.

### ZIO Hexagonal Architecture

```scala
trait OrderRepository:
  def findOrder(id: OrderId): Task[Option[Order]]
  def saveOrder(order: Order): Task[Unit]

def placeOrder(raw: RawOrder): ZIO[OrderRepository & PricingService, OrderError, Confirmation] =
  for
    repo      <- ZIO.service[OrderRepository]
    validated <- ZIO.fromEither(validateOrder(raw))
    priced    <- ZIO.fromEither(priceOrder(validated))
    _         <- repo.saveOrder(priced)
  yield Confirmation(priced.orderId)

// Adapter
class PostgresOrderRepository(ds: DataSource) extends OrderRepository:
  def findOrder(id: OrderId): Task[Option[Order]] = ZIO.attemptBlocking { /* query */ }
  def saveOrder(order: Order): Task[Unit] = ZIO.attemptBlocking { /* insert */ }

val appLayer: ZLayer[Any, Nothing, OrderRepository & PricingService] =
  PostgresOrderRepository.layer ++ PricingServiceLive.layer
```

### Cats Effect / Tagless Final

```scala
trait OrderRepository[F[_]]:
  def findOrder(id: OrderId): F[Option[Order]]

def placeOrder[F[_]: Monad](repo: OrderRepository[F])(raw: RawOrder): F[Either[OrderError, Confirmation]] =
  for
    validated <- Monad[F].pure(validateOrder(raw))
    result <- validated match
      case Left(err) => Monad[F].pure(Left(err))
      case Right(v)  => repo.findOrder(v.orderId).map(_.toRight(OrderNotFound))
  yield result
```

## [INTERMEDIATE] Testing

**Frameworks**: ScalaCheck (PBT) | ZIO Test (integrated PBT + unit) | ScalaTest (BDD) | MUnit (lightweight). See [pbt-jvm](../nw-pbt-jvm/SKILL.md) for detailed PBT patterns.

### Property Test (ScalaCheck)

```scala
import org.scalacheck.Properties
import org.scalacheck.Prop.forAll

object OrderSpec extends Properties("Order"):
  property("serialization round-trips") = forAll { (order: Order) =>
    deserialize(serialize(order)) == Right(order)
  }
  property("validated orders have positive totals") = forAll { (raw: RawOrder) =>
    validateOrder(raw) match
      case Left(_)     => true
      case Right(valid) => valid.total.value > 0
  }
```

## [ADVANCED] Idiomatic Patterns

### Enum-Based State Machines

```scala
enum OrderState:
  case Unvalidated(raw: RawOrder)
  case Validated(order: ValidatedOrder)
  case Priced(order: PricedOrder)
  case Confirmed(confirmation: Confirmation)

def transition(state: OrderState, command: OrderCommand): Either[OrderError, OrderState] =
  (state, command) match
    case (OrderState.Unvalidated(raw), OrderCommand.Validate) =>
      validateOrder(raw).map(OrderState.Validated(_))
    case (OrderState.Validated(order), OrderCommand.Price) =>
      priceOrder(order).map(OrderState.Priced(_))
    case _ => Left(InvalidTransition(state, command))
```

### Extension Methods for Domain Operations

```scala
extension (order: PricedOrder)
  def totalWithTax(taxRate: BigDecimal): Money = Money(order.total.value * (1 + taxRate))
  def isHighValue: Boolean = order.total.value > 1000
```

## Maturity and Adoption

- **Ecosystem fragmentation**: ZIO vs Cats Effect creates split ecosystem. Libraries often target one or the other. Mixing is painful.
- **Slow compilation**: Scala 3 faster than 2 but still significantly slower than Kotlin or Java. Keep modules small; consider Mill over sbt.
- **Complexity reputation**: Scala's power (implicits, type-level programming, macros) creates wildly varying codebases. Establish team conventions early.
- **Migration burden**: Scala 2 to 3 migration non-trivial. Ecosystem has mostly caught up by 2025-2026.

## Common Pitfalls

1. **Ecosystem fragmentation**: Pick one effect ecosystem (ZIO or Cats) and stay consistent. Mixing creates dependency conflicts.
2. **Implicit/given complexity**: Keep `given` instances close to their types. Deep resolution chains produce cryptic errors.
3. **OO/FP tension**: Prefer case classes + enums + pure functions over class hierarchies with mutable state.
4. **Slow compilation**: Use sbt incremental compilation, keep modules small, consider Mill for faster builds.
