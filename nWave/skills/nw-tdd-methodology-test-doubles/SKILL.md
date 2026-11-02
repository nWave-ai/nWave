---
name: nw-tdd-methodology-test-doubles
description: Choosing and building a test double - Meszaros taxonomy, classical-vs-mockist verification, the mock-only-at-port-boundaries policy, and the contract that every InMemory double must validate inputs like the real adapter
user-invocable: false
disable-model-invocation: true
---

# Test Doubles — Taxonomy, Policy, Input-Validation Contract

**Trigger**: choosing a test double or verification style — what to mock, which double type, classical-vs-mockist, and the input-validation contract every InMemory double must satisfy.

## Classical vs Mockist Verification

Classical TDD: real objects | state verification | less coupled to implementation | survives refactoring better.
Mockist TDD: mocks for objects with behavior | behavior verification | lighter setup | more coupled to impl.
Best practice: combine strategically. Behavior verification at layer boundaries, state verification within layers.

## Test Doubles Taxonomy (Meszaros)
- Dummy: passed but never used
- Fake: working impl with shortcuts (in-memory DB)
- Stub: predefined answers
- Spy: stub that records interactions
- Mock: pre-programmed with expectations for behavior verification

Choose type by need: mock for interaction design | stub when don't care about interaction | fake for integration bridge.

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

## Integration Test Contract: Test Doubles Must Validate Inputs

Every InMemory test double MUST enforce the same input preconditions as the real adapter. A test double that accepts inputs the real adapter would reject creates invisible wiring bugs that only surface in production.

**The rule**: if the real adapter crashes on an input, the test double must also fail on that input.

**What to validate in every test double:**
- Required parameters are not None
- Required string fields are not empty
- Numeric fields are within valid ranges (turns > 0, timeout > 0, budget >= 0)
- Enum fields contain valid values
- Complex objects have required nested fields populated

**Why**: dogfood empirics found 3 wiring bugs that 96 acceptance tests missed — because InMemoryVendorAdapter accepted None config, empty prompt file, and wrong field names. The real adapter crashed on all 3. The tests were green but the system was broken.

**Example**:
```python
# WRONG — too permissive, hides wiring bugs
class InMemoryVendorAdapter:
    def dispatch(self, config):
        return Success(self._canned_result)  # accepts anything

# CORRECT — validates like the real adapter
class InMemoryVendorAdapter:
    def dispatch(self, config):
        assert config is not None, "PhaseDispatchConfig required"
        assert config.assembled_prompt_file, "Prompt file must be set"
        assert config.max_turns > 0, "max_turns must be positive"
        return Success(self._canned_result)
```

This is not optional. A test double without input validation is a test double that lies.
