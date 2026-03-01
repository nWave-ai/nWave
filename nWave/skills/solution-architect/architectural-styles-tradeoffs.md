---
name: architectural-styles-tradeoffs
description: Architectural style selection decision matrices, trade-off analysis, structural enforcement rules, and combination patterns. Load when choosing or evaluating architecture styles.
---

# Architectural Styles: Selection and Trade-offs

## Style Selection Decision Tree

Start here. Answer the dominant driver, follow to recommended style.

```
Is the domain complex with rich business rules?
  YES -> Do you need infrastructure independence and high testability?
    YES -> Hexagonal / Clean / Onion (functionally equivalent, different terminology)
    NO  -> Is the domain well-understood with clear module boundaries?
      YES -> Modular Monolith (single deployment, structured boundaries)
      NO  -> Layered Architecture (simple, well-known, fast to start)
  NO -> Is this a feature-heavy application with independent feature teams?
    YES -> Vertical Slice (per-feature organization, CQRS-friendly)
    NO  -> Do you need independent deployment and scaling per capability?
      YES -> Can the team handle distributed system operational complexity?
        YES -> Microservices
        NO  -> Modular Monolith (extract to services later)
      NO  -> Is the primary concern async workflows or event-driven processing?
        YES -> Event-Driven Architecture
        NO  -> Is this a data processing pipeline?
          YES -> Pipe and Filter
          NO  -> Layered Architecture (sensible default)
```

## Cross-Cutting Comparison Matrix

| Style | Dep. Direction | Organization | Deployment | Best For | Team Size |
|-------|---------------|-------------|------------|----------|-----------|
| Hexagonal/Clean/Onion | Inward (DIP) | Ports + adapters | Single process | Infrastructure-agnostic domains | Any |
| Layered (N-Tier) | Top-down | Horizontal layers | Single/multi-tier | Simple CRUD, rapid development | Small-medium |
| Vertical Slice | Per-feature | Feature folders | Single process | Feature-heavy, CQRS systems | Medium-large |
| Microservices | Per-service | Service boundaries | Distributed | Independent teams, polyglot | Large |
| Event-Driven | Pub-sub | Events + handlers | Distributed | Async workflows, audit, decoupling | Medium-large |
| CQRS | Read/write split | Command + query models | Single or distributed | Different read/write scaling | Medium |
| Pipe and Filter | Data flow | Sequential filters | Single or distributed | ETL, data processing | Any |
| Modular Monolith | Inward per module | Domain modules | Single process | Structured monolith, future extraction | Small-medium |

## When-to-Use / When-NOT Decision Matrix

### Hexagonal / Clean / Onion (equivalent patterns, different names)

| Use When | Avoid When |
|----------|-----------|
| Multiple client types consume same domain logic | Simple CRUD with single data store |
| UI/DB technologies need periodic refresh | Latency-critical paths (added indirection) |
| High testability required -- domain testable without infra | Small team where adapter overhead outweighs benefit |
| Alignment with DDD desired | Application will never change infrastructure |

### Vertical Slice

| Use When | Avoid When |
|----------|-----------|
| Teams understand code smells and refactoring patterns | Teams unfamiliar with refactoring -- slices diverge |
| Feature-heavy apps where changes affect one feature | Heavy cross-cutting concerns (shared validation, auth) |
| CQRS systems with independent commands/queries | Early projects with poorly understood domain |
| Minimize cross-cutting changes on new features | Need strong architectural governance |

### Microservices

| Use When | Avoid When |
|----------|-----------|
| Multiple teams need independent deployment cycles | Small teams (operational overhead per service) |
| Different system parts need different tech stacks | Greenfield with unclear boundaries -- start modular monolith |
| Independent scaling of capabilities adds value | Strong transactional consistency required across boundaries |
| Organization supports operational complexity | Risk of "grains of sand" anti-pattern |

### Modular Monolith

| Use When | Avoid When |
|----------|-----------|
| Greenfield with unclear domain boundaries | Independent deployment of components required |
| Non-trivial complexity benefiting from module isolation | Different modules need different tech stacks |
| Module autonomy without distributed overhead | Team ready for microservices operational complexity |
| Microservice-like structure with monolith simplicity | -- |

### Event-Driven / CQRS

| Use When | Avoid When |
|----------|-----------|
| Loose coupling between producers and consumers | Simple request-response applications |
| Workflows spanning multiple services (eventual consistency) | Strong immediate consistency required |
| Complete audit trails needed (event sourcing) | Team unfamiliar with eventual consistency |
| Read/write workloads have very different scaling needs | Simple CRUD where two models add unjustified overhead |

### Pipe and Filter

| Use When | Avoid When |
|----------|-----------|
| Processing decomposes into independent, reorderable steps | Request-response requiring synchronous completion |
| Steps have different scalability requirements | Steps must execute as single transaction |
| Flexibility to add/remove/reorder steps needed | Steps require significant shared state |
| ETL, image processing, compiler pipelines | -- |

## Combination Patterns

Styles are composable. The "Explicit Architecture" approach (Herberto Graca) combines:

| Pattern | Role in Combined Architecture |
|---------|-------------------------------|
| Hexagonal | Framework connecting external tools to the core |
| Onion | Organizes layers within the hexagon |
| DDD | Supplies domain concepts and bounded contexts |
| Clean | Reinforces dependency inversion rules |
| CQRS | Separates commands from queries within each bounded context |

Practical rule: hexagonal/clean/onion are the SAME pattern with different terminology. All enforce DIP with inward dependency flow. Pick one vocabulary and use it consistently.

## Enforceable Structural Rules

Architecture rules are only real if they are enforced. Key rules by style:

### Hexagonal

| Rule | Enforcement |
|------|-------------|
| Domain has zero imports from adapters/infra | import-linter (Python), ArchUnit (Java), ArchUnitTS (TS) |
| All external communication via port interfaces | Code review + architecture tests |
| No adapter-to-adapter dependencies | Package dependency check |
| All dependencies point inward toward domain | Layer dependency rule |

### Modular Monolith

| Rule | Enforcement |
|------|-------------|
| No cross-module database access | Schema ownership tests |
| Interface-only communication between modules | Module independence contract |
| No circular dependencies between modules | Cycle detection |
| Module internals inaccessible from outside | Package/import visibility rules |

### Vertical Slice

| Rule | Enforcement |
|------|-------------|
| Slices must not import from other slices | Independence contract |
| All code for a feature resides within its slice | Containment check |
| Cross-slice communication via events/contracts only | Import rules |

## Architecture Enforcement Tooling

| Language | Tool | Approach |
|----------|------|----------|
| Java/Kotlin | ArchUnit | Fluent API unit tests, predefined architecture rules |
| TypeScript/JS | ArchUnitTS | File-based dependency rules, Jest/Vitest integration |
| Python | import-linter | Config-based contracts (forbidden, layers, independence) |
| Python | PyTestArch | pytest-based architecture tests |
| .NET | NetArchTest | NUnit/xUnit architecture rules |
| Go | go-arch-lint | YAML-based dependency rules |

### Python Example (import-linter)

```ini
[importlinter:contract:hexagonal-domain]
name = Domain must not import from infrastructure
type = forbidden
source_modules = myapp.domain
forbidden_modules = myapp.infrastructure, myapp.adapters

[importlinter:contract:module-independence]
name = Feature modules must be independent
type = independence
modules =
    myapp.modules.orders
    myapp.modules.billing
    myapp.modules.shipping
```

Run `lint-imports` in CI as first-stage fast check (analyzes imports, no I/O).

## Common Anti-Patterns

| Anti-Pattern | Style | Signal | Fix |
|-------------|-------|--------|-----|
| Shared database | Microservices | Services query each other's tables | Database per service; API contracts |
| Distributed monolith | Microservices | Services deploy together | Re-evaluate boundaries; consider modular monolith |
| Grains of sand | Microservices | Too-fine-grained services, constant coordination | Merge into coarser services aligned to bounded contexts |
| Anemic domain model | Layered | Entities are data bags, logic in services | Move behavior into entities/value objects |
| Big ball of mud | Modular Monolith | Module boundaries violated, cross-imports | Add architecture tests, enforce with CI |
| Pass-through layers | Clean | Layers that add no value, just forward calls | Remove unnecessary layers; keep only those adding behavior |
