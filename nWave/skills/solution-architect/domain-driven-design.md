---
name: domain-driven-design
description: Strategic and tactical DDD patterns, bounded context discovery, context mapping, aggregate design rules, and decision frameworks for when to apply DDD
---

# Domain-Driven Design

## When to Apply DDD

DDD addresses domain complexity (business rules, language, boundaries), not technical complexity (scaling, performance). Apply selectively.

| Domain Type (Cynefin) | DDD Investment | Approach |
|------------------------|----------------|----------|
| Clear/Simple | None -- use CRUD | Standard patterns, no modeling overhead |
| Complicated | Tactical only | Expert analysis, pragmatic patterns suffice |
| Complex | Full strategic + tactical | Iterative modeling, bounded contexts, continuous refinement |
| Chaotic | Stabilize first | Emergency patches, then apply DDD incrementally |

### Signs You Need DDD
- Domain experts and developers frequently misunderstand each other
- Business rules are complex, interconnected, frequently changing
- Multiple teams work on the same codebase with conflicting models
- System has grown into a "big ball of mud"
- Business logic scattered across services, controllers, database procedures

### Signs DDD Is Overkill
- Simple CRUD without complex business rules
- Technical complexity outweighs domain complexity
- Small team, small codebase, single bounded context
- For simple microservices, anemic domain model is acceptable (not an anti-pattern)

## Strategic DDD

### Subdomain Classification

| Criterion | Core | Supporting | Generic |
|-----------|------|------------|---------|
| Competitive advantage | Yes | No | No |
| Unique to organization | Yes | Partially | No |
| Build or buy | Build | Build (simplified) | Buy/integrate |
| DDD investment | Full strategic + tactical | Pragmatic tactical | Minimal/none |
| Developer allocation | Senior/best talent | Mid-level | Junior/integration |

### Bounded Contexts

A bounded context is the boundary within which a particular domain model is defined and applicable. Different from subdomains: a bounded context is a software boundary; a subdomain is a problem-space concept. They should align but are not the same.

**Discovery techniques**:
- **Language divergence**: same term means different things to different groups -- you have crossed a boundary
- **Organizational structure**: different departments often correspond to different contexts
- **Consistency requirements**: where true invariants must be maintained transactionally
- **EventStorming**: Big Picture workshops surface boundaries through hotspots and swimlane divergences
- **Domain Storytelling**: actors, work objects, activity arrows reveal natural boundaries

**Common mistakes**:
1. Confusing contexts with subdomains (software boundary vs. problem-space concept)
2. Assuming one microservice = one bounded context (Evans calls this an "oversimplification")
3. Making contexts too large (big ball of mud with conflicting models)
4. Making contexts too small (excessive cross-context communication overhead)

### Context Mapping Patterns

Nine patterns organized by team relationship type.

| Pattern | Relationship | When to Use |
|---------|-------------|-------------|
| Partnership | Mutually dependent | Teams must deliver together; true reciprocal dependency |
| Shared Kernel | Shared model subset | Close coordination around common concepts. Keep small |
| Customer-Supplier | Upstream-downstream | Asymmetric dependencies requiring structured negotiation |
| Conformist | Downstream adopts upstream | Integration simplicity outweighs design freedom |
| Anti-Corruption Layer | Isolating translation | Protecting domain from poor upstream models; legacy integration |
| Open Host Service | Standardized API | Supporting multiple downstream teams |
| Published Language | Shared schema/format | Standardized formats for inter-context translation (iCalendar, vCard) |
| Separate Ways | No connection | Contexts have no meaningful interdependencies |
| Big Ball of Mud | Recognition only | Demarcate and quarantine legacy/poorly-structured systems |

**Relationship categories**: Mutually Dependent (Partnership) | Upstream/Downstream (Customer-Supplier, Conformist, ACL) | Free (Separate Ways)

**Evolution**: context maps evolve during refactoring. A Conformist relationship can be refactored to Customer-Supplier with an ACL. Draw context maps before writing code.

### Ubiquitous Language

A common, rigorous vocabulary shared between developers and domain experts, scoped per bounded context.

**Rules**:
1. Never use generic technical terms when a domain term exists
2. If developers and domain experts use different words for the same concept, resolve the conflict
3. When the model becomes hard to express in code, the language needs refinement
4. The same word may mean different things in different contexts -- this is expected

Code must reflect the language: class names, method names, variable names use domain terms. When the language changes, the code changes.

## Tactical DDD

### Aggregates -- Four Design Rules (Vernon)

1. **Model true invariants in consistency boundaries**: only include elements that must be consistent within the same transaction
2. **Design small aggregates**: ~70% of aggregates contain only a root entity with value-typed properties. Large aggregates create concurrency contention and scalability failures
3. **Reference other aggregates by identity**: use `ProductId` not `Product`. Prevents accidental cross-aggregate transactions
4. **Use eventual consistency outside the boundary**: domain events are the vehicle. One transaction = one aggregate

**Common mistakes**: including objects for compositional convenience | "god aggregates" | direct object references | requiring immediate consistency where eventual suffices

### Entities vs. Value Objects

| Criterion | Entity | Value Object |
|-----------|--------|--------------|
| Identity matters | Yes (tracked over time) | No (interchangeable if same values) |
| Mutability | Mutable (state changes) | Immutable (replace, do not modify) |
| Equality | By identity (ID) | By attribute values (structural) |
| Examples | Customer, Order, Account | Money, Address, DateRange, Email |

**Self-validating value objects**: the only way for a value object to exist is to be valid. Validate in constructor; reject invalid input. Eliminates scattered validation logic.

**Context sensitivity**: whether something is Entity or Value Object depends on the bounded context. Address is a VO in e-commerce but an Entity in utility billing.

### Domain Events

Represent something that happened. Named in past tense: `OrderPlaced`, `UserRegistered`, `PaymentProcessed`.

- **Domain events** (in-process): within a bounded context, dispatched via mediator. Deferred dispatch preferred (collect during command, dispatch before/after commit)
- **Integration events** (distributed): cross bounded contexts via message brokers. Always asynchronous. Published only after successful persistence

### Repositories

One repository per aggregate (not per entity). Interface in domain layer, implementation in infrastructure. Never expose persistence details to the domain.

- **Collection-oriented**: add/remove/find operations, repository tracks changes (Unit of Work)
- **Persistence-oriented**: explicit save/load, common with document DBs or event-sourced systems

### Domain Services

Stateless operations spanning multiple aggregates. Named using ubiquitous language. Operate on domain types only.

Danger: overuse strips entities of behavior, creating anemic domain models.

| Aspect | Domain Service | Application Service |
|--------|---------------|-------------------|
| Contains | Domain logic | Orchestration logic |
| Dependencies | Domain types only | Domain objects + infrastructure ports |
| Layer | Domain model | Application |
| Example | TransferFunds, CalculateDiscount | PlaceOrderHandler, RegisterUserUseCase |

## Integration Patterns

### DDD + Hexagonal Architecture

Natural fit: domain in center (no infrastructure dependencies), ports as use cases, adapters for infrastructure. ACL at adapter boundaries. Each bounded context = a separate hexagon with own ports and adapters.

### DDD + CQRS

Command side uses full tactical DDD toolkit. Query side bypasses domain model entirely -- read models are denormalized views. CQRS is NOT event sourcing (they are independent patterns).

| CQRS Adds Value | CQRS Adds Complexity Without Value |
|-----------------|-----------------------------------|
| Complex domain with rich business rules | Simple CRUD applications |
| Different read/write patterns | Minimal business logic |
| Scale reads/writes independently | Small team without distributed experience |
| Event-driven or event-sourced systems | Strong immediate consistency required everywhere |

### DDD + Event Sourcing

Store domain events instead of current state. State = fold(initialState, events). Apply selectively to core domains only -- "not a top-level architecture" (Greg Young). Use for: audit trails, temporal queries, complex business domains.

### DDD + Microservices

Bounded contexts provide decomposition tool, but the mapping is not one-to-one. A bounded context may contain multiple services; a microservice may handle a focused subdomain within a larger context.

**Decomposition criteria**: subdomain boundaries (primary) | single responsibility | common closure | team autonomy | loose coupling

**Cross-context operations**: Saga pattern with compensating transactions. Choreography (decentralized, simple workflows) vs. Orchestration (centralized, complex workflows).

## Anti-Patterns

| Anti-Pattern | Signal | Fix |
|-------------|--------|-----|
| Anemic Domain Model | Entities = data only, logic in services | Move business rules into entities/aggregates |
| God Aggregate | Too many entities/VOs, concurrency contention | Split by true invariant boundaries |
| Domain Logic in App Layer | Business "if" statements in services | Push logic down to domain objects |
| Primitive Obsession | Raw strings for domain concepts | Create value objects for every domain concept |
| Missing Boundaries | Single unified model for entire system | Identify bounded contexts via language divergence |
| Events as RPCs | Events depend on handler response | Events represent facts, fire-and-forget |
| Database-Driven Design | Entities mirror tables | Model domain first, map to persistence second |

## EventStorming Quick Reference

Three levels: **Big Picture** (25-30 people, entire business line) | **Process Modeling** (structured workflow grammar) | **Design Level** (DDD vocabulary, 1:1 to code).

Key artifacts: Domain Events (orange, past tense) | Commands (blue, imperative) | Aggregates (yellow, consistency boundaries) | Policies (lilac, automation rules) | Read Models (green, decision info) | External Systems (pink) | Hotspots (red, problems/questions).

Start with chaotic event exploration, enforce timeline, add commands/actors, identify aggregates/policies, mark hotspots. Iterate between divergent and convergent phases.
