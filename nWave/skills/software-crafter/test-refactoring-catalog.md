---
name: test-refactoring-catalog
description: Detailed refactoring mechanics with step-by-step procedures, and test code smell catalog with detection patterns and before/after examples
---

# Test Refactoring Catalog

## Test Code Smells (Full Detail)

### L1 Readability Smells

#### Obscure Test

- **Problem**: test name does not reveal business scenario being tested
- **Detection**: generic names like Test1(), ProcessOrderTest(), or names requiring reading test body to understand
- **Solution**: rename to Given_When_Then or should_do_expected_thing_when_condition format

```
Before: public void Test1() { /* ... */ }
After:  public void ProcessOrder_PremiumCustomer_AppliesCorrectDiscount() { /* ... */ }
```

#### Hard-Coded Test Data

- **Problem**: magic numbers and strings obscure business rules being tested
- **Detection**: numbers like 1000, 0.15, strings without explanation
- **Solution**: extract to named constants that reveal business meaning

```
Before: Assert.Equal(850, result.Total);  // What discount?
After:  const decimal EXPECTED_TOTAL = 1000 * (1 - 0.15m);
        Assert.Equal(EXPECTED_TOTAL, result.Total);
```

#### Assertion Roulette

- **Problem**: multiple assertions without messages make failures unclear
- **Detection**: multiple Assert.* calls without message parameter
- **Solution**: add descriptive message to each assertion explaining expected business outcome

### L2 Complexity Smells

#### Eager Test

- **Problem**: single test verifies multiple unrelated behaviors
- **Detection**: multiple arrange/act/assert cycles or assertions testing different concerns
- **Solution**: split into focused tests, one per business scenario

```
Before: ProcessOrderTest() { /* tests discount AND shipping AND tax */ }
After:  ProcessOrder_AppliesDiscount()
        ProcessOrder_CalculatesShipping()
        ProcessOrder_CalculatesTax()
```

Prefer parameterized tests for variations of the same behavior.

#### Test Code Duplication

- **Problem**: repeated test setup logic across multiple tests
- **Detection**: same object creation, mock setup, or data builders copied in 3+ tests
- **Solution**: extract helper methods

```
Extract: CreatePremiumCustomer(), CreateHighValueOrder()
```

#### Conditional Test Logic

- **Problem**: if/switch statements in test code make tests non-deterministic
- **Detection**: if, switch, for loops in test methods
- **Solution**: replace with parameterized tests

```python
# Before: if/else in test
# After:
@pytest.mark.parametrize("input,expected", [...])
def test_behavior(input, expected): ...
```

### L3 Organization Smells

#### Mystery Guest

- **Problem**: test depends on external files or hidden dependencies
- **Detection**: File.ReadAllText, database queries, external config in tests
- **Solution**: inline test data or make dependency explicit in test setup

#### Test Class Bloat

- **Problem**: single test class contains tests for multiple unrelated concerns
- **Detection**: test class with 15+ tests covering different features
- **Solution**: split by feature

```
Before: UserServiceTests (31 tests)
After:  UserAuthTests, UserProfileTests, UserNotificationTests
```

#### General Fixture

- **Problem**: shared fixture used by tests with different needs
- **Detection**: SetUp method creates data used by only some tests
- **Solution**: move to per-test setup methods or test-specific fixtures



For production code refactoring techniques and mechanics, load the progressive-refactoring skill.
