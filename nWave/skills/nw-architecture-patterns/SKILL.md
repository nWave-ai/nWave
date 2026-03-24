---
name: nw-architecture-patterns
description: "Architecture patterns (C4, hexagonal, event-driven), quality frameworks, and evaluation methods. Load when designing system architecture, selecting patterns, or evaluating architectural trade-offs."
user-invocable: false
disable-model-invocation: true
---

# Architecture Patterns and Methodologies

## C4 Model -- Hierarchical Architecture Visualization

Four levels for different audiences:
1. **System Context**: system + users + external systems (stakeholder view)
2. **Containers**: applications, data stores, deployment units (technical overview)
3. **Components**: internal modules within containers (developer view)
4. **Code**: class/module level (optional, often auto-generated)

Notation/tooling independent. Reduces communication overhead, shared visual language across stakeholders.

## Hexagonal Architecture (Ports and Adapters)

Isolate business logic from infrastructure through ports (interfaces) and adapters (implementations).

- **Ports**: technology-agnostic interfaces for external communication
- **Primary ports** (driving): REST controllers, CLI handlers, message consumers -- inbound
- **Secondary ports** (driven): DB repos, external service clients, filesystem -- outbound
- **Adapters**: technology-specific port implementations

Benefits: testability (isolated core) | flexibility (swap infrastructure) | technology independence | maintainability

Testing: unit tests through driving ports, mock driven ports | integration tests with real infrastructure | acceptance tests end-to-end through primary ports

## Architectural Pattern Selection

### Layered Architecture
Horizontal layers with defined dependencies. Use for: traditional enterprise apps, clear separation. Trade-off: familiar but potential overhead, layer coupling.

### Microservices
Independent deployable services per capability. Use for: large teams, component scaling, tech diversity. Trade-off: scalability vs operational complexity. 2025 consensus: "start monolith, evolve when needed." Modular monolith = valid middle ground.

### Event-Driven Architecture
Components communicate via events through broker. Use for: real-time, complex processes, loose coupling. Trade-off: scalability/decoupling vs event ordering, debugging.

### CQRS + Event Sourcing
Separate read/write models; store events not state. Use for: financial, audit, temporal queries. Trade-off: complete history + independent scaling vs eventual consistency + complexity. NOT for: simple CRUD, strong consistency, inexperienced teams.

## Domain-Driven Design (DDD)

### Strategic Patterns
- **Bounded Context**: explicit boundaries for domain model; prevents "single unified model" trap
- **Context Mapping**: Shared Kernel | Customer/Supplier | Anti-Corruption Layer | Open Host Service

### Tactical Patterns
- **Aggregates**: consistency/transactional boundaries; root = only entry point
- **Domain Events**: represent occurrences; enable loose coupling between contexts

### Identifying Boundaries
Language differences between departments | representation differences | consistency requirements define aggregate boundaries. Bounded contexts often map to microservice boundaries and team ownership.

## ISO 25010 Quality Attributes

Eight characteristics:
1. **Functional Suitability**: completeness, correctness, appropriateness
2. **Performance Efficiency**: time behavior, resource utilization, capacity
3. **Compatibility**: coexistence, interoperability
4. **Usability**: learnability, operability, accessibility
5. **Reliability**: maturity, availability, fault tolerance, recoverability
6. **Security**: confidentiality, integrity, non-repudiation, accountability, authenticity
7. **Maintainability**: modularity, reusability, analyzability, modifiability, testability
8. **Portability**: adaptability, installability, replaceability

Trade-offs: Security vs Performance | Scalability vs Consistency (CAP) | Flexibility vs Performance | Usability vs Security

Application: identify priority attributes, define measurable requirements, analyze trade-offs, validate with ATAM.

## ATAM (Architecture Trade-off Analysis Method)

Systematic evaluation from SEI/CMU.

**Phase 1 - Presentation**: business drivers, architecture approaches, design decisions
**Phase 2 - Investigation**: quality attribute scenarios, evaluate approaches, identify sensitivity/trade-off points
**Phase 3 - Testing**: prioritize scenarios, analyze top in depth, document risks/non-risks

Key concepts: **Sensitivity Point** (impacts one attribute) | **Trade-off Point** (affects multiple attributes) | **Architectural Risk** (may prevent attribute achievement)

CBAM extends ATAM with economic analysis (ROI-driven). Perform early when cost of change is minimal. Lightweight: Mini-ATAM (half-day workshop).

## Cloud Resilience Patterns

### Circuit Breaker
Monitor failures; after threshold fail fast ("open"); periodically test recovery. States: Closed, Open, Half-Open. Prevents cascading failures.

### Retry with Exponential Backoff
1s, 2s, 4s, 8s + jitter. Only transient errors, not business logic. Operations must be idempotent.

### Bulkhead
Isolate elements into pools; one failure doesn't affect others. Separate connection/thread pools per feature/tenant.

### Throttling
Rate limiting, concurrency limiting, resource quotas per user/tenant/service.

### Saga Pattern
Distributed transactions as local transaction sequence with compensating rollbacks. Choreography (decentralized) vs Orchestration (centralized).

## API Architecture: REST vs GraphQL

**REST**: resource-based URLs, HTTP verbs, stateless, standard caching. Best for: public APIs, simple CRUD, caching-critical.
**GraphQL**: single endpoint, client-specified queries, typed schema. Best for: mobile (bandwidth), nested data, rapid frontend iteration.
**Hybrid**: GraphQL gateway aggregating REST/RPC backends.
Security for GraphQL: query depth limiting, complexity analysis, timeout, field-level auth.

## ADR Templates

**Nygard** (most common): Title, Status (Proposed/Accepted/Deprecated/Superseded), Context, Decision, Consequences
**MADR** (extended): adds trade-off analysis, considered options with pros/cons
**Y-Statement** (concise): "In context of [use case], facing [concern], decided for [option] to achieve [quality], accepting [downside]"

Best practices: single decision per ADR | immutable (supersede, never modify) | store in VCS | create when decided

## Technology Selection: Open Source Priority

Evaluation order: 1. Mature OSS with strong community | 2. Newer OSS with active dev | 3. Proprietary only when specified or no viable OSS

OSS criteria: last commit <6 months | regular releases | quick issue resolution | 10+ regular contributors | >1000 GitHub stars for critical components

License preference: MIT > Apache 2.0 > BSD > MPL 2.0 > LGPL (caution) > GPL (careful) > AGPL (extreme caution). Proprietary forbidden without explicit request.

Document per selection: name/version, license, GitHub URL/stats, maintenance assessment, alternatives considered.

## Contract Testing for External Integrations

External integrations (web APIs, third-party services, webhooks, OAuth providers) are the highest-risk boundary in any system. Breaking changes in external APIs cause production failures that unit and integration tests cannot catch.

**Consumer-driven contracts** verify that the provider's API still satisfies the consumer's expectations. The consumer defines the contract; the provider verifies against it. Breaking changes are detected at build time, not in production.

### When to Recommend

Annotate for contract testing when the design includes:
- Third-party REST/GraphQL APIs (payment, email, analytics, auth providers)
- Webhooks from external services (Stripe events, GitHub webhooks)
- OAuth/OIDC providers (token exchange, userinfo endpoints)
- Internal APIs consumed across team boundaries (same org, different team)

### Tool Recommendations by Language

| Language | Tool | Notes |
|----------|------|-------|
| Polyglot (any) | Pact | Consumer-driven, widest language support, Pact Broker for contract sharing |
| JVM (Java/Kotlin) | Spring Cloud Contract | Groovy/YAML DSL, generates stubs for consumers, tight Spring integration |
| .NET | PactNet | Pact implementation for .NET, NuGet package |
| Python | pact-python | Pact implementation for Python, pytest integration |
| JavaScript/TS | Pact-JS | Pact implementation for Node.js, Jest/Vitest compatible |

### Handoff Annotation Format

When external integrations are detected, include in the handoff to platform-architect:

```
External Integrations Requiring Contract Tests:
- [Service Name] ([API type]): [what the system consumes]
  Recommended: consumer-driven contracts via [tool] in CI acceptance stage
```

This enables platform-architect to include contract test execution in the CI/CD pipeline design.
