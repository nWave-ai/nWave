---
name: test-organization-conventions
description: Test directory structure patterns by architecture style, language conventions, naming rules, and fixture placement. Decision tree for selecting test organization strategy.
---

# Test Organization Conventions

## Core Principle

Test directory structure encodes architectural boundaries. If a developer cannot infer the architecture from the test tree alone, the organization is wrong.

## Architecture-to-Organization Decision Tree

```
What is the project's architectural style?
|
+-- Hexagonal / Clean Architecture
|   --> Test-type-first: tests/{unit,integration,acceptance,e2e}/
|   --> Domain concepts nested within each type
|   --> Port contract tests in tests/integration/
|
+-- Vertical Slice
|   --> Co-located: features/{slice}/tests/
|   --> Cross-slice tests in top-level tests/cross_feature/
|
+-- Modular Monolith
|   --> Module-first: tests/modules/{module}/{unit,integration}/
|   --> Architecture tests per module (dependency rule enforcement)
|   --> Inter-module tests in tests/inter_module/
|
+-- Microservices
|   --> Per-service test tree: {service}/tests/{unit,integration,component,contract}/
|   --> Contract tests: consumer writes in own repo, provider verifies in own repo
|   --> Cross-service E2E in separate project: e2e-tests/
|
+-- Event-Driven
|   --> Test-type-first with event-specific categories
|   --> Unique: schema contract tests, idempotency tests, saga compensation tests
|
+-- CQRS
|   --> Command/Query split within each test type
|   --> Unique: projection tests (rebuild + idempotency)
|
+-- Layered (N-Tier)
|   --> Mirror source: tests mirror src layer hierarchy
|   --> Integration tests verify layer boundary contracts
|
+-- DDD (Tactical)
|   --> Bounded-context-first: tests/{context}/domain/aggregates/
|   --> Cross-context contract tests in tests/bounded_context_integration/
```

## Comparative Summary

| Architecture | Primary Axis | Secondary Axis | Unique Test Types | Co-located? |
|-------------|-------------|----------------|-------------------|-------------|
| Hexagonal | Test type | Domain concept | Port contract | No |
| Clean | Test type | Architecture ring | Gateway | No |
| Layered | Mirror source | Test type | Layer boundary | No (Java: yes) |
| Vertical Slice | Feature | Test type | Cross-slice | Yes |
| Modular Monolith | Module | Test type | Architecture, inter-module | No |
| Microservices | Per-service | Test type | Contract (Pact) | No |
| Event-Driven | Test type | Event flow role | Schema, idempotency, saga | No |
| CQRS | Command/Query | Test type | Projection | No |
| DDD | Bounded context | Building block | Aggregate, cross-context | No |

## Mirror vs. Feature vs. Hybrid

| Strategy | Best For | Strengths | Weaknesses |
|----------|----------|-----------|------------|
| Mirror source | Layered, Clean, Hexagonal | Predictable paths, IDE navigation, package-private access (Java) | Feature changes touch multiple dirs |
| Feature co-located | Vertical Slice, React | All feature code in one place, team ownership | Cross-feature tests homeless, hard to run by tier |
| Hybrid (recommended) | Most projects | Type-first for CI stages, feature-nested within | Slightly deeper nesting |

Hybrid pattern (type-first, then feature within):

```
tests/
  unit/
    features/
      order/test_create_order.py
      payment/test_process_payment.py
  integration/
    features/
      order/test_order_repository.py
  e2e/
    test_checkout_flow.py
```

## Language-Specific Conventions

| Language | File Convention | Discovery Rule | Co-located? |
|----------|---------------|----------------|-------------|
| Python (pytest) | `test_*.py` or `*_test.py` | Prefix/suffix match | Separate `tests/` (recommended) or inlined |
| TypeScript/JS (Jest) | `*.test.ts`, `*.spec.ts`, `__tests__/*.ts` | testMatch pattern | Either |
| Java (JUnit/Maven) | `*Test.java` in mirrored package | `src/test/java` mirrors `src/main/java` | Mirrored packages |
| Go | `*_test.go` in same directory | Language-enforced co-location | Always co-located |
| C# (xUnit/NUnit) | `*Tests.cs` in parallel project | Separate test project | Separate project |
| Rust | `#[cfg(test)] mod tests` inline + `tests/` | Inline for unit, `tests/` for integration | Unit: inline, Integration: separate |

### Python conftest.py Placement

Place `conftest.py` at the lowest directory where fixtures apply. Pytest discovers from outermost to innermost, enabling hierarchical fixture scoping:

```
tests/
  conftest.py              # Session fixtures: DB engine, app instance
  unit/
    conftest.py            # Unit-specific: auto-mock markers
  integration/
    conftest.py            # Integration: real DB fixtures
  acceptance/
    conftest.py            # Acceptance: feature file paths
```

### BDD Feature Files

```
tests/
  features/                # Gherkin .feature files by domain
    order/
      place_order.feature
    payment/
      process_payment.feature
  step_defs/               # Step implementations by domain concept
    conftest.py
    order_steps.py
    payment_steps.py
```

Organize step definitions by domain concept, not by feature file. Shared steps across features prevent duplication.

## Hexagonal Architecture Test Tiers

| Tier | Location | Tests | Adapters |
|------|----------|-------|----------|
| Unit | tests/unit/ | Domain model, value objects, service layer | None (pure) or mock driven ports |
| Integration | tests/integration/ | Individual adapters against real infra | Real infrastructure |
| Acceptance | tests/acceptance/ | Use cases through driving ports | In-memory adapters |
| E2E | tests/e2e/ | Full stack through HTTP/CLI | Real adapters |

Port contract tests: when multiple adapters implement one driven port, create shared contract test suite and run against each adapter.

```
tests/integration/
  test_repository_contract.py     # Abstract tests for RepositoryPort
  test_postgres_repository.py     # Runs contract against Postgres
  test_inmemory_repository.py     # Runs contract against in-memory
```

## Fixture Organization

| Scope | What | Placement |
|-------|------|-----------|
| Session | Expensive setup (DB engine, app) | Root conftest.py |
| Module | Schema creation, service containers | Directory conftest.py |
| Function | Data cleanup, test isolation | autouse=True in conftest.py |
| Shared across types | Factories, builders | tests/conftest.py or tests/fixtures/ |

## Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| Flat tests/ with no structure | Cannot run by tier, no boundary visibility | Organize by primary axis of architecture |
| Mirroring hex layers in test tree | Couples tests to implementation structure | Organize by test type, not source structure |
| Acceptance tests alongside E2E | Acceptance should use in-memory adapters and run fast | Separate: acceptance/ (fast) vs e2e/ (slow) |
| Feature-coupled step definitions | Steps for login.feature only usable there | Organize steps by domain concept |
| Mixing test tiers in one directory | Cannot run unit-only in pre-commit | Separate directories per tier |
| Cross-module imports in tests | Violates module boundaries | Use inter-module tests with event bus |
| E2E inside single microservice | They span services by definition | Move to separate e2e-tests/ project |
| No contract tests between services | Mocks drift from reality | Consumer-driven contract tests (Pact) |
