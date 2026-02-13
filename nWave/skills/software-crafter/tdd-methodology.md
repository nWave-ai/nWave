---
name: tdd-methodology
description: Deep knowledge for Outside-In TDD - double-loop architecture, ATDD integration, port-to-port testing, walking skeletons, and test doubles policy
---

# Outside-In TDD Methodology

## Double-Loop TDD Architecture

Outer loop: ATDD/E2E Tests (customer view) - business requirements, hours-days to green.
Inner loop: Unit Tests (developer view) - technical implementation, minutes to green, RED->GREEN->REFACTOR.

Outer stays red while inner cycles. Outer drives WHAT to build, inner drives HOW.
Never build components not needed by actual user scenarios.

## Outside-In vs Inside-Out

Inside-Out (Classic/bottom-up): discovers collaborators through refactoring. TDD guides design completely.
Outside-In (London/top-down/mockist): knows collaborators upfront, mocks them, implements each moving inward.

Use Outside-In when: architectural boundaries known (hexagonal), program to interface not implementation.

## ATDD Integration (Lightweight)

Original 2008 heavyweight ATDD was "too heavyweight for most real teams." Updated approach (Hendrickson 2024):
- Few Given/When/Then examples, not many
- Separate requirements (communicate intent) from tests (verify behavior)
- Smallest subset of team with relevant skills
- Value = shared understanding, not executable specs
- Automate only where high-value

## BDD Integration

BDD emerged from Outside-In TDD. Given(context)->When(action)->Then(outcome) maps to outside-in mindset.
BDD reframes TDD as design/specification technique, not just testing. More accessible to stakeholders.
Gherkin: structured format bridging technical/non-technical. Use pragmatically - automate only where high value.

## Outside-In Development Workflow (Bache)

1. Write Guiding Test (acceptance) from user perspective - thick slice of functionality
2. Start at top-level entry point, design collaborating classes incrementally
3. Use mocks to experiment with interfaces/protocols
4. As each layer implemented, move to previously mocked collaborators, TDD again
5. Never build what isn't needed for actual user scenarios

## Port-to-Port Testing

Tests enter through driving port (application service / public API) and assert outcomes at driven port boundaries.
Internal classes (entities, value objects, domain services) are exercised indirectly - never instantiated directly in test code.

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

## Unit of Behavior (not Unit of Code)

Test = story about the problem your code solves. Granularity related to stakeholder needs.
A unit of behavior may span multiple classes. Test from driving port to driven port boundary.
Key question: "Can you explain this test to a stakeholder?" If not, you're testing implementation details.

## Classical vs Mockist Verification

Classical TDD: real objects, state verification, less coupled to implementation, survives refactoring better.
Mockist TDD: mocks for objects with behavior, behavior verification, lighter setup, more coupled to impl.
Best practice: combine strategically. Behavior verification at layer boundaries, state verification within layers.

## Test Doubles Taxonomy (Meszaros)

- Dummy: passed but never used
- Fake: working impl with shortcuts (in-memory DB)
- Stub: predefined answers
- Spy: stub that records interactions
- Mock: pre-programmed with expectations for behavior verification

Choose type by need: mock for interaction design, stub when don't care about interaction, fake for integration bridge.

## Hexagonal Architecture Testing Strategy

### Domain Layer
Tested indirectly through driving port (application service) unit tests with real domain objects.
Domain entities, value objects, domain services are implementation details. Testing them directly couples tests to internal structure.

Exception: Standalone domain logic with complex algorithms (e.g., pricing engine) MAY be tested directly when complexity warrants it and the class has a stable public interface. This is the EXCEPTION, not the rule.

### Application Layer
Classical TDD within layer, Mockist TDD at port boundaries.
Use real Order, Money, Customer objects in application service tests.
Mock IPaymentGateway, IEmailService ports when testing orchestration.

### Infrastructure Layer
Integration tests ONLY - no unit tests for adapters.
Mocking infrastructure inside an adapter test is testing the mock, not the adapter.
Use real infrastructure (testcontainers, in-memory databases) to verify actual behavior.

### E2E Tests
Minimal mocking - only truly external systems (3rd party APIs beyond your control).
Use real domain services, application services, repositories.

## Test Doubles Policy

Acceptable (port boundaries only):
- `Mock<IPaymentGateway>` - external payment service port
- `Mock<IEmailService>` - external email provider port
- `InMemoryUserRepository` - fake for fast tests (implements IUserRepository port)

Do not mock inside the hexagon:
- Domain entities (Order, Customer) - use real objects
- Value objects (Money, Email) - cheap to create, deterministic
- Application services (OrderProcessor) - use real with mocked ports
- Domain services (PricingService) - use real objects

## Walking Skeleton Protocol

At most one walking skeleton per new feature. When `is_walking_skeleton: true` in roadmap:
- Write exactly ONE E2E/acceptance test proving end-to-end wiring
- Implement the thinnest possible slice - hardcoded values, minimal branching
- Do NOT write unit tests - the E2E test IS the deliverable
- Do NOT add error handling, edge cases, or validation
- Skip inner TDD loop, go directly from RED_ACCEPTANCE to GREEN

E2E tests are inherently slow and flaky. The walking skeleton is the ONE justified E2E test per feature.

## E2E Test Management

Enable ONE E2E test at a time to prevent commit blocks:
1. All E2E tests except first one marked with skip/ignore
2. Complete first scenario through Outside-In TDD
3. Commit working implementation
4. Enable next E2E test
5. Repeat until all scenarios implemented

## Step Method Pattern

Step methods call production services, not test infrastructure:

```csharp
[When("business action occurs")]
public async Task WhenBusinessActionOccurs()
{
    var service = _serviceProvider.GetRequiredService<IBusinessService>();
    _result = await service.PerformBusinessActionAsync(_testData);
}
```

Scaffold unimplemented collaborators with `NotImplementedException`:
```csharp
throw new NotImplementedException(
    "Business capability not yet implemented - driven by outside-in TDD"
);
```

## Business-Focused Testing

### Unit Test Naming
- Class pattern: `<DrivingPort>Should`
- Method pattern: `<ExpectedOutcome>_When<SpecificBehavior>[_Given<Preconditions>]`
- Example: `AccountServiceShould.IncreaseBalance_WhenDepositMade_GivenSufficientFunds`

### Behavior Types
- Command behavior: changes system state (Given-When-Then)
- Query behavior: returns state projection (Given-Then)
- Process behavior: orchestrates multiple commands/queries

### Test Structure
- Arrange: set up business context and test data
- Act: perform business action
- Assert: validate business outcome and state changes

## Environment-Adaptive Testing

- Local development: in-memory infrastructure for fast feedback (~100ms)
- CI/CD pipeline: production-like infrastructure for integration validation (~2-5s)
- Same scenarios: single source of truth across all environments
