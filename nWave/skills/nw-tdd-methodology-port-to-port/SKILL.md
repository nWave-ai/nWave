---
name: nw-tdd-methodology-port-to-port
description: What a test asserts on and where it enters - port-to-port discipline at all test levels, the layer-specific Universe, refactoring-resilience, and the hexagonal per-layer testing strategy
user-invocable: false
disable-model-invocation: true
---

# Port-to-Port Testing and the Layered Universe

**Trigger**: deciding a test's entry/exit boundary and what it asserts on — at any layer (unit, acceptance, integration, WS/E2E) of a hexagonal system.

## Port-to-Port Testing (ALL test levels)

Acceptance and unit tests enter through a declared public driving port and assert public outcomes. Adapter integration tests exercise the real adapter against infrastructure through its port contract.
Private entities, value objects and domain services are exercised indirectly. A declared public constructor or domain function is itself a driving port; its public contract may be tested directly.

- **Acceptance test**: enters from application service driving port, asserts at driven port boundary (port-to-port)
- **Unit test**: enters from domain function driving port (pure function public API), asserts on return value (port-to-port at domain scope)
- **Integration test**: verifies adapter correctly implements port contract against real infrastructure (adapter-to-port, NOT port-to-port). Tests the bridge between infrastructure and port.

Unit tests are NOT "isolated object tests." They are port-to-port at a smaller scope. The driving port for a pure domain function IS the function's public signature.

Flow: Driving Port -> Application -> Domain -> Driven Port (mocked)

```python
def test_order_service_processes_payment():
    # Setup - mock driven port (external dependency)
    payment_gateway = MockPaymentGateway()
    order_repo = InMemoryOrderRepository()

    # Test through driving port (application service)
    order_service = OrderService(payment_gateway, order_repo)
    result = order_service.place_order(customer_id, items)

    # Assert observable outcomes
    assert result.is_confirmed()
    payment_gateway.verify_charge_called(amount=100.00)
```

### Layered test discipline — Universe per layer

Each layer is port-to-port at its scope. The PBT + state-delta paradigm applies at all layers; the **Universe** is layer-specific (port-exposed names only, never internal field names — refactoring stays GREEN).

| Layer | Surface | Speed target | Universe shape |
|---|---|---|---|
| **Unit** | Port boundary at unit-of-behaviour scope | <1ms | port-exposed observable states (return values, captured port-call args, state-delta over port-level slots) |
| **Acceptance (general)** | Driving port invoked **directly**; driven ports = in-memory doubles | ~10ms | use-case observable outcomes (events emitted on port, state on driven-port double, error class returned) |
| **Integration** | Adapter ↔ real external dependency (FS, DB, network, subprocess) | ~100ms | adapter-to-dep round-trip (file written and re-read, row inserted and queried, HTTP call and response shape) |
| **Walking Skeleton + `@wiring_e2e`** | CLI subprocess / HTTP / real composition root + real driven I/O | ~1-3s | user-visible end-to-end output (stdout, exit code, FS side-effects) |
| **E2E** | Full system with real environment | seconds | full pipeline assurance |

**Walking Skeleton subset rule**: WS / `@wiring_e2e` scenarios go through real subprocess + real I/O. Feature-level skeleton scope and applicability belong to `nw-tdd-methodology-walking-skeleton`; read it when authoring or validating that skeleton. The rest of acceptance scenarios run through driving-port direct invocation with in-memory doubles for driven ports. Mandate 1 ("subprocess invocation real I/O") in `walking-skeleton.feature` is for WS only, not all acceptance.

**Universe construction rule**: derive Universe from the layer's *observable surface*, never from internal struct/field names. A Universe entry like `composition.startup_status` is correct (port-exposed); `fold._rows_cells_dict` is wrong (internal mutation detail — refactor will red the test).

**Refactoring resilience smoke check**: rename a private helper → suite stays GREEN. If red, the test was coupling to impl. Eliminate or refactor port-to-port at the right layer.

## Hexagonal Architecture Testing Strategy

### Domain Layer
Test private domain objects indirectly through the application's driving port. Test a declared public domain constructor or function through its own public contract; visibility and contract determine the boundary, not the object's category.

Pure domain functions (e.g., evaluate_gate, check_tier) ARE their own driving ports — calling them directly in tests IS port-to-port testing because the function signature IS the public interface. This is not an exception; it's the correct application of port-to-port to the domain layer.

### Application Layer
Classical TDD within layer, Mockist TDD at port boundaries.
Use real Order, Money, Customer objects in application service tests.
Mock IPaymentGateway, IEmailService ports when testing orchestration.

### Infrastructure Layer (Adapters)
Integration tests ONLY — no unit tests for adapters. Mocking infrastructure inside an adapter test is testing the mock, not the adapter.
Use real infrastructure (testcontainers, in-memory databases, real filesystem via tmp_path, real subprocess) to verify actual behavior.

Adapter integration tests are typically created to make the Walking Skeleton pass — the WS requires real adapters, which drives the implementation of the adapter AND its integration test. Additional adapter tests for specific error conditions (disk full, timeout, permission denied) are created in subsequent focused scenarios tagged `@infrastructure-failure` (see `nw-tdd-methodology-walking-skeleton` Mandate 6). Subsequent happy-path scenarios use InMemory doubles for speed; the adapter correctness is proven by the WS + infrastructure failure scenarios.

### E2E Tests
Minimal mocking - only truly external systems (3rd party APIs beyond your control).
Use real domain services, application services, repositories.
