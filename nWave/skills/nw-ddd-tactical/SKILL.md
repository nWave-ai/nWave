---
name: nw-ddd-tactical
description: Tactical DDD — aggregate design rules, entities, value objects, domain events, repositories, domain services, and anti-pattern detection
user-invocable: false
disable-model-invocation: true
---

# Tactical DDD

Implementation patterns within a bounded context. Tactical DDD answers: "How do we structure the domain model?"

## Aggregates

An aggregate is a consistency boundary -- a cluster of domain objects that must be transactionally consistent.

### Vernon's Four Design Rules

1. **Model true invariants in consistency boundaries**: Only include elements that MUST be consistent within the same transaction. If two entities don't share an invariant, they belong in separate aggregates.

2. **Design small aggregates**: ~70% of aggregates contain only a root entity with value-typed properties. Large aggregates create concurrency contention, scalability failures, and memory pressure.

3. **Reference other aggregates by identity**: Use `ProductId` not `Product`. Direct object references create accidental cross-aggregate transactions and prevent independent scaling.

4. **Use eventual consistency outside the boundary**: Domain events communicate across aggregates. One transaction = one aggregate. If you need to update two aggregates "atomically," reconsider your boundaries.

### Aggregate Design Checklist

- [ ] Contains only elements sharing true invariants
- [ ] Root entity controls all access (no direct child manipulation)
- [ ] External references by ID only (no object graphs)
- [ ] Small enough for single-transaction performance
- [ ] Command produces events (in event-sourced systems) or mutates state (in traditional)
- [ ] Business rules validated in command handling, not in persistence layer

### Common Aggregate Smells

| Smell | Signal | Fix |
|-------|--------|-----|
| God Aggregate | >5 entities, frequent concurrency conflicts | Split by invariant analysis |
| Anemic Aggregate | All logic in services, aggregate = data bag | Move business rules into aggregate methods |
| Cross-Aggregate Transaction | Two aggregates modified in one DB transaction | Use domain events + eventual consistency |
| Deep Nesting | Aggregate root -> entity -> entity -> value | Flatten; promote nested entities to own aggregates |
| Missing Aggregate | Business rules scattered in application services | Identify invariant cluster, create aggregate |

## Entities

Objects with identity that persists across state changes. An entity is the "same" entity even when all its attributes change (a person who changes name, address, and job is still the same person).

**Design rules**: Identity is assigned once and never changes | Equality by identity, not attributes | Track lifecycle (created, modified, archived) | Place business rules that depend on identity here

## Value Objects

Objects defined by their attributes, not identity. Two value objects with the same attributes are interchangeable.

**Design rules**:
- **Immutable**: Never modify; create new instances
- **Self-validating**: Constructor rejects invalid state. If a `Money` object exists, it has a valid amount and currency
- **Side-effect-free behavior**: Methods return new values, don't mutate
- **Structural equality**: Compare by attributes, not reference

**Examples**: Money(amount, currency) | Email(address) | DateRange(start, end) | Address(street, city, zip, country) | Temperature(value, unit)

**Context sensitivity**: Whether something is Entity or Value Object depends on bounded context. Address is a VO in e-commerce (shipping destination) but an Entity in utility billing (service location with lifecycle).

## Domain Events

Represent something that happened in the domain. Always past tense.

### Naming Convention

| Correct (past tense) | Wrong (imperative) |
|----------------------|-------------------|
| OrderPlaced | PlaceOrder (that's a command) |
| PaymentReceived | ReceivePayment |
| UserRegistered | RegisterUser |
| InventoryReserved | ReserveInventory |

### Event Design Guidelines

- **Self-contained**: Include all data needed to understand what happened
- **Cross-context payload**: an integration event shared with another context carries the fact's type and the meaningful ids; data only one consumer needs belongs in that consumer's query
- **Domain language**: Business terms, not technical jargon
- **One fact per event**: `OrderConfirmed` not `OrderStatusChanged`
- **No behavior**: Events carry data only
- **Granularity matters**: Too coarse (OrderUpdated) loses meaning; too fine (OrderFieldChanged) is a generic audit log

### Event Categories

**Domain events** (in-process): Within a bounded context, dispatched via mediator. Collected during command handling, dispatched before/after commit.

**Integration events** (distributed): Cross bounded-context via message brokers. Always asynchronous. Published only after successful persistence. May use different schema than domain events (translated at boundary).

## Repositories

One repository per aggregate (not per entity). Interface defined in domain layer, implementation in infrastructure.

**Collection-oriented**: add/remove/find -- repository tracks changes (Unit of Work pattern). Natural for ORMs.

**Persistence-oriented**: explicit save/load -- caller manages lifecycle. Natural for document DBs and event-sourced systems.

**Rules**: Never expose persistence details (SQL, JSON) to domain | Return domain objects, not DTOs | Query methods use domain language (findActiveOrders, not findByStatusEquals)

## Domain Services

Stateless operations that span multiple aggregates or don't naturally belong to any single entity.

**When to use**: Operation involves multiple aggregates | Logic doesn't belong to any entity | Named using ubiquitous language

**Danger**: Overuse creates anemic domain models. First try to place the behavior on an entity or aggregate. Domain service is the last resort for truly cross-aggregate logic.

| Domain Service | Application Service |
|---------------|-------------------|
| Domain logic (rules, calculations) | Orchestration (transaction, security, events) |
| Domain types only | Domain + infrastructure ports |
| Domain layer | Application layer |
| TransferFunds, CalculateDiscount | PlaceOrderHandler, RegisterUserUseCase |

## Anti-Pattern Detection

When analyzing existing code, look for these patterns:

| Anti-Pattern | Code Signal | Recommendation |
|-------------|-------------|----------------|
| Anemic Domain Model | Entities = data classes, services contain all `if` logic | Move business rules to entities/aggregates |
| Primitive Obsession | `String email`, `double amount`, `int quantity` | Create value objects: Email, Money, Quantity |
| Database-Driven Design | Entities mirror DB tables 1:1, foreign keys as navigation | Model domain first, map to persistence second |
| Missing Boundaries | Single model used by all features, vocabulary conflicts | Identify contexts via language divergence |
| Logic in Wrong Layer | Business rules in controllers/handlers | Push down to domain objects |
| Service Bloat | Service class with 20+ methods | Split by use case, push logic to aggregates |
| Event as RPC | Event handler returns result that caller depends on | Events are fire-and-forget; use command for request-response |
