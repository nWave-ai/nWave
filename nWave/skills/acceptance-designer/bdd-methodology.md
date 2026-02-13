---
name: bdd-methodology
description: BDD patterns for acceptance test design - Given-When-Then structure, scenario writing rules, pytest-bdd implementation, anti-patterns, and living documentation
---

# BDD Methodology for Acceptance Test Design

## Core Philosophy

Test units of behavior, not units of code. Acceptance tests validate business outcomes through public interfaces, decoupled from implementation details.

## Outside-In Double-Loop TDD

The acceptance-designer creates the outer loop -- the "outside" of Outside-In TDD. Development starts from the user's perspective and drives inward toward implementation.

**Outer loop (acceptance/BDD)**: hours to days, user perspective, business language, defines "done."
- Written from outside: what does the user want? What do they observe?
- Scenarios describe user goals and observable outcomes, not system internals
- A failing outer-loop test is the starting signal for implementation

**Inner loop (unit/TDD)**: minutes, developer perspective, technical terms, implements components.
- Driven from inside: how does the system fulfill the user's goal?
- The software-crafter owns this loop

Workflow:
1. Write failing acceptance test from user's perspective (outer loop -- outside)
2. Software-crafter drops to inner loop: unit tests to implement components (inside)
3. Iterate inner loop until acceptance test passes
4. The passing acceptance test proves user value is delivered
5. Repeat for next behavior

Outer loop defines WHAT users need (outside). Inner loop drives HOW to build it (inside). The acceptance-designer owns the outside; the software-crafter owns the inside.

## Given-When-Then Structure

```gherkin
Scenario: [Business-focused title describing one behavior]
  Given [preconditions - system state in business terms]
  When [single user action or business event]
  Then [observable business outcome]
```

### Scenario Writing Rules

**Rule 1: One scenario, one behavior**
Split multi-behavior scenarios into focused singles.

**Rule 2: Declarative, not imperative**
Describe business outcomes, not UI interactions. "When I log in with valid credentials" not "When I click Login button and enter email in field."

**Rule 3: Concrete examples, not abstractions**
Use specific values: "Given my account balance is $100.00" not "Given the user has sufficient funds."

**Rule 4: Keep scenarios short (3-5 steps)**
If longer, you are testing multiple behaviors or including irrelevant details.

**Rule 5: Background for shared Given steps only**
Background contains only Given steps. Actions and validations belong in scenarios.

## Scenario Categorization

- **Happy path**: Primary successful user workflows
- **Error path**: Invalid inputs, failures, unauthorized access (target 40%+ of scenarios)
- **Edge case**: Boundary conditions, unusual but valid behavior
- **Integration**: Cross-component and cross-system interactions

### Golden Path + Key Alternatives Pattern

For each capability, test:
1. Happy path (most common successful flow)
2. Alternative paths (valid but less common)
3. Error paths (invalid inputs, constraint violations)

Select representative examples that reveal different business rules. Do not test every combination.

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

Organize steps by domain concept, not by feature file:
```
steps/
  authentication_steps.py  # All auth-related steps
  account_steps.py         # All account-related steps
  transaction_steps.py     # All transaction-related steps
```

### Fixture Scopes for Performance

- Session scope: expensive setup (database engine, app instance)
- Module scope: schema creation
- Function scope: data cleanup (autouse=True)

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

Use real services (database, message queue) with test data. Avoid mocks at acceptance test level.

## Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Testing through UI | Test through service/API layer |
| Multiple WHEN actions | Split into separate scenarios |
| Feature-coupled steps | Organize by domain concept |
| Conjunction steps ("Given A and B" as one step) | Break into atomic steps |
| Incidental details | Include only behavior-relevant information |
| Technical jargon in scenarios | Replace with business domain language |
| Abstract scenarios | Use concrete values and specific examples |
| Rambling scenarios (8+ steps) | Extract to 3-5 focused steps |

## Living Documentation

Scenarios serve dual purpose: executable tests and living documentation.

Organization: Business Goal > Capability > Feature > Scenario > Test

Each scenario traces to business capability. Stakeholders see which capabilities are implemented, tested, and passing.

### Documentation-Grade Scenarios

Replace HTTP verbs with business actions, JSON with domain concepts, status codes with business outcomes. Add context about WHO and WHY.
