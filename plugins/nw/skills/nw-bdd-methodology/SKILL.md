---
name: nw-bdd-methodology
description: BDD patterns for acceptance test design - Given-When-Then structure, scenario writing rules, pytest-bdd implementation, anti-patterns, and living documentation
disable-model-invocation: true
---

# BDD Methodology for Acceptance Test Design

## Core Philosophy

Test units of behavior, not units of code. Acceptance tests validate business outcomes through public interfaces, decoupled from implementation.

## Outside-In Double-Loop TDD

The acceptance-designer creates the outer loop of Outside-In TDD. Development starts from user perspective, drives inward.

**Outer loop (acceptance/BDD)**: Hours to days | User perspective, business language | Defines "done" | Scenarios describe user goals and observable outcomes, not internals | Failing outer-loop test is the starting signal for implementation

**Inner loop (unit/TDD)**: Minutes | Developer perspective, technical terms | Software-crafter owns this loop

Workflow:
1. Write failing acceptance test from user perspective (outer loop -- outside)
2. Software-crafter drops to inner loop: unit tests to implement components (inside)
3. Iterate inner loop until acceptance test passes
4. Passing acceptance test proves user value delivered
5. Repeat for next behavior

Outer loop defines WHAT users need (outside). Inner loop drives HOW to build it (inside).

## Given-When-Then Structure

```gherkin
Scenario: [Business-focused title describing one behavior]
  Given [preconditions - system state in business terms]
  When [single user action or business event]
  Then [observable business outcome]
```

### Scenario Writing Rules

**Rule 1: One scenario, one behavior** -- Split multi-behavior scenarios.

**Rule 2: Declarative, not imperative** -- Business outcomes, not UI interactions. "When I log in with valid credentials" not "When I click Login button and enter email."

**Rule 3: Concrete examples, not abstractions** -- "Given my account balance is $100.00" not "Given the user has sufficient funds."

**Rule 4: Keep scenarios short (3-5 steps)** -- Longer means testing multiple behaviors or irrelevant details.

**Rule 5: Background for shared Given steps only** -- Only Given steps. Actions/validations in scenarios.

## Scenario Categorization

- **Happy path**: Primary successful workflows
- **Error path**: Invalid inputs, failures, unauthorized access (target 40%+ of scenarios)
- **Edge case**: Boundary conditions, unusual but valid behavior
- **Integration**: Cross-component/system interactions

### Golden Path + Key Alternatives

Per capability: 1. Happy path (most common success) | 2. Alternative paths (valid but less common) | 3. Error paths (invalid inputs, constraint violations). Select representative examples revealing different business rules. Do not test every combination.

### Scenario Outlines for Boundary Testing

```gherkin
Scenario Outline: Account minimum balance validation
  Given I have an account with balance $<initial_balance>
  When I attempt to withdraw $<withdrawal_amount>
  Then the withdrawal is <result>

  Examples: Valid withdrawals
    | initial_balance | withdrawal_amount | result   |
    | 100.00         | 50.00            | accepted |
    | 25.00          | 25.00            | accepted |

  Examples: Invalid withdrawals
    | initial_balance | withdrawal_amount | result                       |
    | 100.00         | 101.00           | rejected (insufficient funds) |
```

Use outlines for boundary conditions and calculation variations. Avoid when scenarios diverge structurally.

## pytest-bdd Implementation

### Step Definitions with Fixture Injection

```python
from pytest_bdd import scenarios, given, when, then, parsers

scenarios('../features/account.feature')

@given("I am authenticated", target_fixture="authenticated_user")
def authenticated_user(auth_service):
    user = auth_service.create_and_authenticate("test@example.com")
    return user

@given(parsers.parse('my account balance is ${amount:g}'),
       target_fixture="account")
def account_with_balance(authenticated_user, account_service, amount):
    return account_service.create_account(authenticated_user, balance=amount)
```

### Step Organization by Domain

Organize by domain concept, not feature file:
```
steps/
  authentication_steps.py  # All auth-related steps
  account_steps.py         # All account-related steps
  transaction_steps.py     # All transaction-related steps
```

### Fixture Scopes for Performance
Session: expensive setup (DB engine, app instance) | Module: schema creation | Function: data cleanup (autouse=True)

### Production-Like Test Environment

```python
@pytest.fixture(scope="session")
def app():
    """Application instance with production-like configuration."""
    app = create_app({"environment": "test", "database": "postgresql://localhost/test_db"})
    with app.app_context():
        app.db.create_all()
    yield app
    with app.app_context():
        app.db.drop_all()
```

Use real services (database, message queue) with test data. Avoid mocks at acceptance level.

## Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Testing through UI | Test through service/API layer |
| Multiple WHEN actions | Split into separate scenarios |
| Feature-coupled steps | Organize by domain concept |
| Conjunction steps ("Given A and B" as one step) | Break into atomic steps |
| Incidental details | Include only behavior-relevant info |
| Technical jargon in scenarios | Business domain language |
| Abstract scenarios | Concrete values, specific examples |
| Rambling scenarios (8+ steps) | Extract to 3-5 focused steps |

## Living Documentation

Scenarios serve dual purpose: executable tests and living documentation. Organization: Business Goal > Capability > Feature > Scenario > Test. Each scenario traces to business capability. Stakeholders see which capabilities are implemented, tested, passing.

### Documentation-Grade Scenarios
Replace HTTP verbs with business actions, JSON with domain concepts, status codes with business outcomes. Add context about WHO and WHY.
