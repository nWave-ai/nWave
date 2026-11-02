---
name: nw-fp-kotlin
agent: nw-functional-software-crafter
description: Kotlin language-specific patterns with Arrow, Raise DSL, and coroutine-based effects
user-invocable: false
disable-model-invocation: true
---

# FP in Kotlin -- Functional Software Crafter Skill

Cross-references: [fp-principles](../nw-fp-principles/SKILL.md) | [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md) | [pbt-jvm](../nw-pbt-jvm/SKILL.md)

## When to Choose Kotlin

- Best for: gentlest FP onboarding for Java teams | Android | coroutines | pragmatic FP with great IDE support
- Not ideal for: teams wanting compiler-enforced purity | full effect systems | higher-kinded type abstractions

## [STARTER] Quick Setup

```bash
mkdir order-service && cd order-service
gradle init --type kotlin-application --dsl kotlin
# Add arrow-core, arrow-fx-coroutines, kotest-property to build.gradle.kts
./gradlew build && ./gradlew test
```

## [STARTER] Type System for Domain Modeling

### Choice Types (Sealed Hierarchies)

```kotlin
sealed interface PaymentMethod {
    data class CreditCard(val cardNumber: String, val expiryDate: String) : PaymentMethod
    data class BankTransfer(val accountNumber: String) : PaymentMethod
    data object Cash : PaymentMethod
}
```

Exhaustive `when` expressions ensure all cases handled.

### Record Types and Domain Wrappers

```kotlin
data class Customer(
    val customerId: CustomerId,
    val customerName: CustomerName,
    val customerEmail: EmailAddress
)

@JvmInline
value class OrderId(val value: Int)

@JvmInline
value class EmailAddress private constructor(val value: String) {
    companion object {
        fun from(raw: String): Either<ValidationError, EmailAddress> =
            if ("@" in raw) EmailAddress(raw).right()
            else InvalidEmail(raw).left()
    }
}
```

Value classes inlined by compiler -- zero allocation overhead.

### [INTERMEDIATE] Validated Construction with Raise DSL

```kotlin
import arrow.core.raise.Raise
import arrow.core.raise.ensure

context(Raise<ValidationError>)
fun validateEmail(raw: String): EmailAddress {
    ensure(raw.contains("@")) { InvalidEmail(raw) }
    return EmailAddress.unsafeCreate(raw)
}
```

## [INTERMEDIATE] Composition Style

### Scope Functions as Lightweight Pipelines

```kotlin
val result = rawOrder
    .let(::validateOrder)
    .map(::priceOrder)
    .map(::confirmOrder)
```

### Arrow Raise DSL (Direct-Style Typed Errors)

```kotlin
import arrow.core.raise.either

fun placeOrder(raw: RawOrder): Either<OrderError, Confirmation> = either {
    val validated = validateOrder(raw).bind()
    val priced = priceOrder(validated).bind()
    confirmOrder(priced).bind()
}
```

Looks imperative, behaves functionally. `bind()` short-circuits on `Left`.

### Accumulating Errors

```kotlin
import arrow.core.raise.zipOrAccumulate

fun validateCustomer(raw: RawCustomer): Either<NonEmptyList<ValidationError>, Customer> = either {
    zipOrAccumulate(
        { validateName(raw.name) },
        { validateEmail(raw.email) },
        { validateAddress(raw.address) }
    ) { name, email, address -> Customer(name, email, address) }
}
```

## [INTERMEDIATE] Effect Management

Kotlin is impure by default. `suspend` marks functions performing side effects or async work.

### Pure Core / Imperative Shell with Coroutines

```kotlin
// Pure domain logic (no suspend, no side effects)
object OrderDomain {
    fun calculateDiscount(order: Order): Discount =
        if (order.lines.size > 10) Discount(0.1) else Discount(0.0)
}

// Imperative shell (suspend = side effects)
class OrderService(
    private val orderRepo: OrderRepository,
    private val pricingService: PricingService
) {
    suspend fun placeOrder(raw: RawOrder): Either<OrderError, Confirmation> = either {
        val validated = OrderDomain.validateOrder(raw).bind()
        val priced = pricingService.price(validated).bind()
        orderRepo.save(priced)
        Confirmation(priced.orderId)
    }
}
```

### [ADVANCED] Hexagonal Architecture with Interfaces

```kotlin
// Port: interface defining capability
interface OrderRepository {
    suspend fun findOrder(id: OrderId): Order?
    suspend fun saveOrder(order: Order)
}

// Adapter: concrete implementation
class PostgresOrderRepository(private val db: Database) : OrderRepository {
    override suspend fun findOrder(id: OrderId): Order? =
        db.query("SELECT * FROM orders WHERE id = ?", id.value)
    override suspend fun saveOrder(order: Order) =
        db.execute("INSERT INTO orders ...", order)
}
```

DI: constructor injection via Koin, Dagger/Hilt, or manual wiring.

## [INTERMEDIATE] Testing

**Frameworks**: Kotest (test framework + PBT) | jqwik (PBT on JUnit 5) | MockK (coroutine-aware mocking). See [pbt-jvm](../nw-pbt-jvm/SKILL.md) for detailed PBT patterns.

### Property Test (Kotest)

```kotlin
import io.kotest.core.spec.style.FunSpec
import io.kotest.property.forAll

class OrderSpec : FunSpec({
    test("serialization round-trips") {
        forAll(orderArb) { order -> deserialize(serialize(order)) == order.right() }
    }
    test("validated orders have positive totals") {
        forAll(rawOrderArb) { raw ->
            when (val result = validateOrder(raw)) {
                is Either.Left -> true
                is Either.Right -> result.value.total.value > 0
            }
        }
    }
})
```

### Custom Generator

```kotlin
val emailArb: Arb<EmailAddress> = arbitrary {
    val user = Arb.string(minSize = 1, maxSize = 10, codepoints = Codepoint.az()).bind()
    val domain = Arb.string(minSize = 1, maxSize = 8, codepoints = Codepoint.az()).bind()
    EmailAddress.unsafeCreate("$user@$domain.com")
}
```

## [ADVANCED] Idiomatic Patterns

### Null Safety as Option Alternative

```kotlin
fun findCustomer(id: CustomerId): Customer? = ...
val email = findCustomer(id)?.customerEmail?.value

// Use Either/Raise when you need error context
context(Raise<CustomerError>)
fun getCustomer(id: CustomerId): Customer =
    findCustomer(id) ?: raise(CustomerNotFound(id))
```

## Arrow Maturity Caveat

Arrow is capable with active development, but carries honest risks:

- **Context receivers/parameters** (Raise DSL relies on) are still experimental in Kotlin. Feature renamed and redesigned multiple times.
- Arrow's API changed significantly between 1.x and 2.x, requiring substantial rewrites.
- Smaller contributor base than ZIO or Cats Effect.
- For long-term stability needs, evaluate whether Arrow's API surface will remain stable for your project's lifetime.

## Common Pitfalls

1. **Arrow API instability**: Pin versions carefully. Read migration guides before major upgrades.
2. **No higher-kinded types**: Use concrete types or Arrow's Raise DSL as abstraction mechanism.
3. **FP is library-dependent**: Without Arrow, Kotlin FP limited to null safety, sealed classes, and extensions.
4. **Coroutine complexity**: `CoroutineScope`, `Dispatcher`, `SupervisorJob` interactions are subtle. Test with `runTest`.
