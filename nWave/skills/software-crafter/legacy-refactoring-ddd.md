---
name: legacy-refactoring-ddd
description: DDD-guided legacy refactoring patterns -- strangler fig, bubble context, ACL migration, 14 tactical/strategic/infrastructure patterns, and incremental monolith-to-microservices methodology
---

# Legacy Refactoring with DDD

Refactoring legacy systems using Domain-Driven Design as the strategic compass. DDD tells you WHERE and WHY to refactor; traditional techniques (progressive-refactoring, mikado-method) tell you HOW.

Principle: "Start simple, grow big" -- incremental steps tested at each stage.

## Decision Framework: Before Refactoring

Ask three questions before any DDD refactoring:
1. **Business value**: what business outcome does refactoring this area enable?
2. **Risk**: what breaks if we refactor vs. if we do not?
3. **Cost**: time, effort, disruption -- is it justified?

### When NOT to Refactor
- System scheduled for replacement
- Stable system with no new development
- Cost exceeds benefit
- Team lacks DDD experience with no learning budget
- Domain is genuinely simple (CRUD-dominated)

### Cynefin-Refactoring Mapping

| Cynefin Domain | Refactoring Approach |
|---------------|---------------------|
| Clear | Apply established patterns directly; standard refactoring catalogs |
| Complicated | Analyze with experts, then apply patterns; multiple valid solutions |
| Complex | Probe with safe-to-fail experiments; EventStorming to discover patterns |
| Chaotic | Act first to stabilize, then refactor; emergency patches acceptable |
| Confusion | Gather information before deciding; avoid premature refactoring |

## Migration Methodology (4 Phases)

### Phase 1: Understand and Stabilize
1. Run EventStorming to map current system (Big Picture)
2. Assess complexity using Cynefin framework
3. Write characterization tests for critical paths (Feathers technique)
4. Identify bounded contexts in existing codebase via language divergence

### Phase 2: Modularize the Monolith
1. Introduce module structure aligned with bounded contexts
2. Use mediator pattern for initial decoupling between modules
3. Apply fitness functions to measure progress (coupling, cohesion, dependency direction)
4. Refactor database schemas toward context alignment

### Phase 3: Introduce Events and CQRS
1. Replace mediator with event-driven communication
2. Implement CQRS for contexts benefiting from read/write separation
3. Split databases per bounded context using expand/contract pattern
4. Use event-based data synchronization for cross-context data needs

### Phase 4: Extract Services (if justified)
1. Evaluate microservices readiness (6 signals below)
2. Start with most independent bounded context
3. Use strangler fig pattern -- incrementally extract while legacy still runs
4. Apply appropriate saga pattern for distributed transactions

### Microservices Readiness Signals
1. Clear domain boundaries already established
2. Scaling pressure on specific areas (not uniform)
3. Independent development needs across teams
4. Operational maturity (CI/CD, monitoring, automated testing in place)
5. Technical expertise in distributed systems
6. Business justification (not trend-following)

## Strategic Refactoring Patterns

### Strangler Fig
Build new DDD-modeled functionality alongside legacy. Route requests to new code as features complete. Legacy gradually shrinks until fully replaced. Changes are incremental, monitored, low risk of unexpected breakage.

**Mikado integration**: use Mikado exploration to discover dependencies between legacy components before extracting. Each Mikado leaf becomes an atomic refactoring step.

### Bubble Context
Create a small bounded context (the "bubble") where DDD principles apply. The bubble communicates with legacy through an Anti-Corruption Layer. Progressively expand the bubble to encompass more legacy functionality.

**Steps**:
1. Identify the most valuable bounded context (core domain) for initial DDD investment
2. Create an ACL between the new context and legacy
3. Apply tactical DDD within the bubble (aggregates, value objects, domain events)
4. Gradually expand, moving more logic behind the ACL
5. Retire legacy components as new context absorbs their functionality

### Evolve Context Map
Integration patterns change as refactoring progresses. Map current relationships, identify mismatches, propose new patterns. Typical evolution: Conformist -> Customer-Supplier with ACL -> Partnership.

### Split Bounded Context
When a context grows too large or serves conflicting purposes:
1. Domain decomposition to break responsibilities into subdomains
2. Context mapping to plan the split and redefine integration patterns
3. Isolate related aggregates
4. Introduce domain events for communication
5. Gradually refactor dependent code

Validation: bounded context splits are driven by business evolution, not technical convenience. Validate with domain experts.

### Merge Bounded Contexts
When separation causes more friction than value:
1. Identify redundancies (overlapping models, duplicate logic, tight coupling)
2. Establish unified ubiquitous language
3. Consolidate aggregates and deprecate redundant events
4. Revisit context map

## Tactical Refactoring Patterns

These patterns apply tactical DDD concepts (aggregates, value objects, domain events, domain services, CQRS) to refactoring. For foundational definitions and design rules, load `domain-driven-design` from `solution-architect/`.

| Pattern | What It Fixes | Key Step |
|---------|--------------|----------|
| Replace primitives with VOs | Primitive obsession | Create self-validating type, replace in aggregate, update mapping |
| Enrich anemic model | Logic in services, data in entities | Move business rules from service "if" statements into owning entity |
| Introduce domain events | Direct coupling between aggregates | Replace method calls with immutable past-tense events + handlers |
| Extract domain service | Cross-aggregate operations in application layer | Create stateless domain-typed service; guard against overuse |
| Introduce CQRS | Read/write contention on same model | Separate read DTOs from write aggregates; CQRS != event sourcing |

## Infrastructure Refactoring Patterns

### Split Database by Bounded Context
Most challenging aspect of DDD refactoring. Use expand/contract pattern for safe migration.

1. Identify table ownership by bounded context
2. **Expand**: add new schema/tables aligned with target context
3. **Migrate**: copy data, set up synchronization
4. **Contract**: remove old schema after validation
5. Test integrity at each step

### Event-Based Data Synchronization
When contexts need data owned by another context:

1. Owning context publishes integration events on state changes
2. Consuming context maintains read-only local copy, updated via event handlers
3. ACL translates between event format and local model
4. Accept eventual consistency (design for it, test for it)

### Replace Mediator with Events
Prepare for microservice extraction. Mediator is a stepping stone, not a destination.

1. Identify all mediator interactions between modules
2. Define domain/integration events for each interaction
3. Implement event bus (in-process initially, message broker for distribution)
4. Remove mediator dependencies
5. Test behavioral equivalence (async vs. sync differences)

### Extract Microservice
Only when module is stable, independently deployable, and business-justified.

1. Verify bounded context independence (no shared database, no synchronous coupling)
2. Extract module to independent service with own persistence
3. Define API contract and integration events
4. Deploy independently with monitoring
5. Apply saga pattern for any cross-service transactions

## Fitness Functions for Progress

Measure refactoring progress with automated fitness functions in CI:

| Metric | What It Measures | Tool Examples |
|--------|-----------------|---------------|
| Afferent coupling | Incoming dependencies to module | NDepend, SonarQube, jdepend |
| Efferent coupling | Outgoing dependencies from module | Same |
| Dependency direction | Dependencies flow correctly (inward) | ArchUnit, NetArchTest |
| Test coverage | Safety net for refactoring | Coverage tools |
| Cohesion | Relatedness of components within module | LCOM metrics |

Define fitness function thresholds as acceptance criteria for refactoring stories.

## Testing Strategy for Legacy Refactoring

| Test Type | When | Purpose |
|-----------|------|---------|
| Characterization tests | Before touching legacy code | Document current behavior as safety net |
| Contract tests | When splitting contexts | Verify interservice communication |
| Eventual consistency tests | After introducing events | Simulate network failures, verify convergence |
| Schema integrity tests | During database refactoring | Verify constraints and data integrity |

Characterization tests (Feathers): run legacy code, observe output, write tests that assert current behavior -- even if behavior seems wrong. These tests protect against unintended changes during refactoring.

## Integration with Existing Skills

- **mikado-method**: use Mikado exploration to discover dependencies before strangler fig extraction. Each Mikado leaf = one atomic DDD refactoring step
- **progressive-refactoring**: apply L1-L4 refactoring within each bounded context after DDD restructuring. DDD operates at architecture level; RPP operates at code level
- **hexagonal-testing**: each bounded context is a hexagon. Test domain logic through driving ports; mock driven ports for isolation
