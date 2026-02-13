---
name: architecture-patterns
description: Comprehensive architecture patterns, methodologies, quality frameworks, and evaluation methods for solution architects. Load when designing system architecture or selecting patterns.
---

# Architecture Patterns and Methodologies

## C4 Model -- Hierarchical Architecture Visualization

Four levels for different audiences:
1. **System Context**: System + users + external systems (stakeholder view)
2. **Containers**: Applications, data stores, deployment units (technical overview)
3. **Components**: Internal modules within containers (developer view)
4. **Code**: Detailed class/module level (optional, often auto-generated)

Notation independent, tooling independent. Business value: reduces communication overhead, shared visual language across technical/non-technical stakeholders.

## Hexagonal Architecture (Ports and Adapters)

Core concept: isolate business logic from infrastructure through ports (interfaces) and adapters (implementations).

- **Ports**: Technology-agnostic interfaces defining how external actors communicate with the application
- **Primary ports** (driving): REST controllers, CLI handlers, message consumers -- inbound
- **Secondary ports** (driven): Database repositories, external service clients, file system -- outbound
- **Adapters**: Technology-specific implementations of ports

Benefits: testability (core logic tested in isolation), flexibility (replace infrastructure without changing business logic), technology independence, maintainability.

Testing strategy:
- Unit tests invoke through driving ports only, mock driven ports
- Integration tests verify adapter implementations with real infrastructure
- Acceptance tests validate end-to-end user scenarios through primary ports

## Architectural Pattern Selection

### Layered Architecture
- Horizontal layers with defined dependencies
- Use for: traditional enterprise apps, clear separation of concerns
- Trade-off: familiar but potential performance overhead, layer coupling

### Microservices
- Independent, deployable services per business capability
- Use for: large teams, component-specific scaling, technology diversity
- Trade-off: scalability and independence vs operational complexity, distributed system challenges
- 2025 consensus: "start with monolith, evolve to microservices when needed"
- Modular monolith is a valid middle ground

### Event-Driven Architecture
- Components communicate through events via broker
- Use for: real-time systems, complex processes, loose coupling
- Trade-off: scalability and decoupling vs event ordering complexity, debugging challenges

### CQRS + Event Sourcing
- Separate read/write models; store events instead of current state
- Use for: financial systems, audit requirements, temporal queries
- Trade-off: complete history and independent scaling vs eventual consistency and mental model complexity
- When NOT to use: simple CRUD, strong consistency everywhere, team lacks experience

## Domain-Driven Design (DDD)

### Strategic Patterns
- **Bounded Context**: Explicit boundaries where domain model is valid; prevents "single unified model" trap
- **Context Mapping**: Relationships between contexts (Shared Kernel, Customer/Supplier, Anti-Corruption Layer, Open Host Service)

### Tactical Patterns
- **Aggregates**: Consistency boundaries around entities; transactional boundary; root is only entry point
- **Domain Events**: Represent occurrences; enable loose coupling between contexts

### Identifying Boundaries
- Language differences between departments (same term, different meaning)
- Representation differences (in-memory vs stored)
- Consistency requirements define aggregate boundaries

Bounded contexts often map to microservice boundaries and team ownership.

## ISO 25010 Quality Attributes

Eight characteristics for architecture evaluation:

1. **Functional Suitability**: Completeness, correctness, appropriateness
2. **Performance Efficiency**: Time behavior, resource utilization, capacity
3. **Compatibility**: Coexistence, interoperability
4. **Usability**: Learnability, operability, accessibility
5. **Reliability**: Maturity, availability, fault tolerance, recoverability
6. **Security**: Confidentiality, integrity, non-repudiation, accountability, authenticity
7. **Maintainability**: Modularity, reusability, analyzability, modifiability, testability
8. **Portability**: Adaptability, installability, replaceability

Common trade-offs:
- Security vs Performance (encryption overhead)
- Scalability vs Consistency (CAP theorem)
- Flexibility vs Performance (abstraction overhead)
- Usability vs Security

Application: identify priority attributes per system, define measurable requirements, analyze trade-offs, validate with ATAM.

## ATAM (Architecture Trade-off Analysis Method)

Systematic architecture evaluation from SEI/CMU.

**Phase 1 - Presentation**: Business drivers, architecture approaches, design decisions
**Phase 2 - Investigation**: Quality attribute scenarios, evaluate approaches, identify sensitivity and trade-off points
**Phase 3 - Testing**: Prioritize scenarios, analyze top ones in depth, document risks and non-risks

Key concepts:
- **Sensitivity Point**: Decision significantly impacting one quality attribute
- **Trade-off Point**: Decision affecting multiple quality attributes (improving some, degrading others)
- **Architectural Risk**: Decision potentially preventing quality attribute achievement

CBAM extends ATAM with economic analysis (ROI-driven prioritization).

Perform early in SDLC when cost of change is minimal. Lightweight alternative: Mini-ATAM (half-day workshop).

## Cloud Resilience Patterns

### Circuit Breaker
Monitor failures; after threshold, fail fast ("open circuit"); periodically test recovery. States: Closed, Open, Half-Open. Prevents cascading failures.

### Retry with Exponential Backoff
Retry transient failures: 1s, 2s, 4s, 8s. Add jitter to prevent thundering herd. Only retry transient errors, not business logic failures. Operations must be idempotent.

### Bulkhead
Isolate elements into pools; one failure does not affect others. Separate connection pools, thread pools per feature/tenant.

### Throttling
Limit request rate per user/tenant/service. Rate limiting, concurrency limiting, resource quotas.

### Saga Pattern
Distributed transactions as sequence of local transactions with compensating transactions for rollback. Choreography (decentralized) vs Orchestration (centralized).

## API Architecture: REST vs GraphQL

**REST**: Resource-based URLs, HTTP verbs, stateless, standard caching. Best for: public APIs, simple CRUD, caching-critical scenarios.

**GraphQL**: Single endpoint, client-specified queries, strongly typed schema. Best for: mobile apps (bandwidth), complex nested data, rapid frontend iteration.

**Hybrid**: GraphQL as API gateway aggregating REST/RPC backend services.

Security for GraphQL: query depth limiting, complexity analysis, timeout protection, field-level authorization.

## ADR Templates

### Nygard (most common)
Title, Status (Proposed/Accepted/Deprecated/Superseded), Context, Decision, Consequences

### MADR (extended)
Adds explicit trade-off analysis and considered options with pros/cons

### Y-Statement (concise)
"In the context of [use case], facing [concern], we decided for [option] to achieve [quality], accepting [downside]"

Best practices: single decision per ADR, immutable (supersede, never modify), store in version control, create when decision is made.

## Technology Selection: Open Source Priority

Evaluation order:
1. Mature open source with strong community (first choice)
2. Newer open source with active development (second choice)
3. Proprietary only when user explicitly specifies or no viable OSS exists (last resort)

Open source criteria: last commit within 6 months, regular releases, quick issue resolution, 10+ regular contributors, GitHub stars >1000 for critical components.

License preference: MIT > Apache 2.0 > BSD > MPL 2.0 > LGPL (caution) > GPL (careful evaluation) > AGPL (extreme caution). Proprietary forbidden without explicit user request.

Document for every selection: library name/version, license type, GitHub URL/stats, maintenance assessment, alternatives considered.
