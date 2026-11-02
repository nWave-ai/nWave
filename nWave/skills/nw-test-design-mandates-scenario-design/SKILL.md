---
name: nw-test-design-mandates-scenario-design
description: "Scenario-design mandates for acceptance tests — Hexagonal Boundary Enforcement (drive through driving ports, never internals), Business Language Abstraction (three abstraction layers), User Journey Completeness, Pure Function Extraction Before Fixtures, Algebraic Analysis Before the Scenario (name the law, find its narrowest surface, declare every gated input, prove the scenario can fail), the 3 Pillars style backbone, and Walking Skeleton Strategy. Consult while shaping or judging a scenario's boundary, language, journey completeness, and fixture strategy. Canonical definitions; SSOT for these mandates."
user-invocable: false
disable-model-invocation: true
---

# Test-Design Mandates — Scenario Design

**Kind**: KNOWLEDGE (reference). No forced sequence — consulted on its trigger.

**Trigger**: you are shaping or judging a scenario's SHAPE — what to drive (boundary), what language to use, whether it is a complete user journey, and whether fixtures are parameterized correctly. Mandates 1-4 + the 3 Pillars + Walking Skeleton Strategy.

Numbering is an SSOT-internal index defined in the recomposing core `nw-test-design-mandates`; refer to mandates by descriptive name externally. Language-convention frame (non-Python target adaptation) lives in the core — read it before applying any code example below.

## Mandate 1: Hexagonal Boundary Enforcement

Tests invoke through driving ports (entry points), never internal components.

### Driving Ports (Test Through These)
Application services/orchestrators | API controllers/CLI handlers | Message consumers/event handlers | Public API facade classes | For a library: its public function/value API (the exported surface a consumer imports) — a library's public function is a driving port exactly like a service method.

### Not Entry Points (Never Test Directly)
Internal validators, parsers, formatters | Domain entities/value objects | Repository implementations | Internal service components | A library's private/internal classes and helpers not part of its exported API

### Public Library API vs Private Internal Domain Objects

A domain library distinguishes its PUBLIC function/value API (what a consumer is allowed to import and call — the driving boundary) from PRIVATE internal domain objects (implementation detail behind that API). Tests couple to the former only. Coupling to a private internal class or helper — even one that looks stable — is the same boundary violation as calling an internal validator directly; it breaks the moment internals are refactored even though the public contract did not change.

Expected outcomes are derived independently from the requirements/spec, never by reading the implementation and echoing back whatever it currently does — an oracle copied from the code under test cannot catch a defect in that code.

### Correct Pattern

```python
# Invoke through system entry point (driving port)
from myapp.orchestrator import AppOrchestrator

def when_user_performs_action(self):
    orchestrator = AppOrchestrator()
    self.result = orchestrator.perform_action(
        context=self.context
    )
```

### Violation Pattern

```python
# Invoking internal component directly
from myapp.validator import InputValidator  # INTERNAL

def when_user_validates_input(self):
    validator = InputValidator()  # WRONG BOUNDARY
    self.result = validator.validate(self.input)
```

Testing internal components creates Testing Theater: tests pass but users cannot access feature through actual entry point. Integration wiring bugs remain hidden.

## Mandate 2: Business Language Abstraction

Step methods speak business language, abstract all technical details.

### Three Abstraction Layers

**Layer 1 — Business scenario**: Describe the admitted context, user action and outcome with domain terms in the native test layout. Gherkin below is an illustration, not a required dependency. Public protocol terms are valid when the user's actual contract is that protocol.

```gherkin
Scenario: Customer places order for available product
  Given customer has items in shopping cart
  When customer submits order
  Then order is confirmed
  And customer receives confirmation email
```

**Layer 2 - Step Methods**: Business service delegation. Method names use domain terms | Delegate to business service layer (OrderService, not HTTP client) | Assert business outcomes (order.is_confirmed()), not technical state (status_code == 201)

```python
def when_customer_submits_order(self):
    self.result = self.order_service.place_order(
        customer=self.customer, items=self.cart_items
    )

def then_order_is_confirmed(self):
    assert self.result.is_confirmed()
    assert self.result.has_order_number()
```

**Layer 3 - Business Services**: Production services handle technical implementation. HTTP calls, DB transactions, SMTP hidden inside service layer.

### Test Smell Indicators
`requests.post()` in step method | `db.execute()` in step method | `assert response.status_code` | Technical terms in Gherkin

### File/Function Naming

Test file and function names describe the feature/business value under test, not test bookkeeping (`test_1`, `test_helper_setup`, `test_case_final_v2`). The canonical test-identifier rule is `nw-test-design-mandates` → Durable outcome naming; apply it to files and functions as well as scenarios.

## Mandate 3: User Journey Completeness

User-journey tests validate complete journeys with business value, not isolated technical operations; focused contract/property tests protect a named observable contract at its declared boundary.

### Complete Journey Structure
Each scenario body visibly composes typed business-language Given steps, exactly one When, then Then steps for user journeys, or Arrange steps, exactly one Act, then Assert steps for focused contract/property tests. Given/When (or Arrange/Act) steps drive the public driving port; Then/Assert steps own business-named assertions and WHAT/WHY/HOW failure messages internally. Gherkin files are optional; these phases remain visible in the native test framework. No business logic, branching or looping in scenario bodies; no helper owns a whole scenario or branches on scenario kind. Parameterize only data variants of the SAME scenario with the same expected outcome shape; keep identical stimulus/assertion pairs once and reuse domain steps instead of copying the same literals across scenarios.

Each test creates a fresh typed scenario-scoped context for its reusable steps; never share static/global step objects or inherit another scenario's state.

Language-agnostic step composition:

```text
scenario incomplete fleet cannot become ready:
  given captain Marco has created a room
  when captain Marco declares ready with an incomplete fleet
  then ready is refused because the fleet is incomplete
  and the room is unchanged
```

### Correct Example

```gherkin
Scenario: Customer successfully completes purchase
  Given customer has selected products worth $150
  And customer has valid payment method
  When customer submits order
  Then order is confirmed with order number
  And customer receives email confirmation
  And order appears in customer's order history
```

### Violation Example

```gherkin
Scenario: Order validator accepts valid order data
  Given valid order JSON exists
  When validator.validate() is called
  Then validation passes
# Tests isolated validation, not user journey
```

### Scenario Name Test
Does name express user value or technical operation? "Customer completes purchase" = correct. "Validator accepts JSON" = violation.

## Walking Skeleton Strategy

Balance one feature-level E2E walking skeleton with many focused boundary tests. A feature is not "entire feature or extra skeleton per slice" — see `nw-tdd-methodology-walking-skeleton`: exactly ONE walking skeleton per feature, established by its first slice and extended by every later slice; a scenario that needs its own independent E2E boundary is an additional SCENARIO, never a second skeleton.

### The Feature's Walking Skeleton (one per feature)
Trace thin vertical slice delivering observable user value E2E | Answers: "Can a user accomplish this goal and see the result?" | Express simplest complete user journey | Validate system delivers demo-able stakeholder value | Touch all layers as consequence of journey, not as design goal

### Walking Skeleton Litmus Test
1. Title describes user goal ("Customer purchases a product") not technical flow ("Order passes through all layers")
2. Given/When describe user actions/context, not system state setup
3. Then describe user observations (confirmation, email, receipt), not internal side effects (DB row, message queued)
4. Non-technical stakeholder can confirm "yes, that is what users need"

### Focused Scenarios (15-20 per feature, majority)
Test specific business rules at driving port boundary | Test doubles for external dependencies (faster, isolated) | Cover business rule variations and edge cases | Invoke through entry point (OrderService, Orchestrator)

### Recommended Ratio
For a typical feature with 20 scenarios: 1 walking skeleton (user value E2E, established once and extended) | 19 focused scenarios (boundary tests with test doubles, plus any independently-justified extra E2E). The skeleton proves users achieve the goal end-to-end once. Focused scenarios run fast, cover breadth. Both use business language and invoke through entry points.

## Mandate 4: Pure Function Extraction Before Fixtures

BEFORE parametrizing any test fixture with environment variants:

1. Identify ALL business logic in the code under test
2. Extract every piece of business logic into a pure function:
   - Pure function: takes inputs, returns outputs, no side effects
   - Impure code: subprocess calls, file I/O, network, environment variables
3. Test pure functions directly — no fixtures, no mocks, no environment setup needed
4. Test impure code (subprocess, file I/O) through adapter interfaces:
   - Define a port (interface) for each impure operation
   - Create a test adapter (in-memory, fake) for each port
   - Acceptance tests give each driven port its Architecture of Reference treatment (`nw-distill-port-treatment-policy`): an in-memory fake for a driven-internal port, a capturing fake for a driven-external one. Real driven-internal adapters serve only the feature's one walking skeleton and the adapter integration tests (`nw-tdd-methodology-walking-skeleton`)
5. Parametrize fixtures ONLY for the thin adapter layer that connects to real environments

**Rationale**: Parametrizing fixtures across environments is expensive. Pure functions need zero environment setup. Extract first, parametrize the minimum.

### Violation Pattern

Python illustration (pytest binding; the rule — parameterize only the thin adapter layer — is language-neutral):
```python
# WRONG: parametrizing entire test across environments
@pytest.fixture(params=["clean", "with-pre-commit", "with-stale-config"])
def environment(request):
    return setup_environment(request.param)

def test_install_detects_conflicts(environment):
    result = full_install_pipeline(environment)  # Impure: touches filesystem
    assert result.conflicts == []
```

### Correct Pattern

```python
# Step 1: Extract pure logic
def detect_conflicts(config: Config, existing: list[str]) -> list[Conflict]:
    """Pure function — no I/O, no environment dependency."""
    return [Conflict(k) for k in existing if k in config.keys]

# Step 2: Test pure function directly (no fixture needed)
def test_detect_conflicts_with_overlapping_keys():
    conflicts = detect_conflicts(Config(keys=["a", "b"]), existing=["b", "c"])
    assert conflicts == [Conflict("b")]

# Step 3: Parametrize ONLY the adapter layer
@pytest.fixture(params=["clean", "with-pre-commit"])
def fs_adapter(request):
    return create_real_fs_adapter(request.param)

def test_adapter_reads_config_from_environment(fs_adapter):
    config = fs_adapter.read_config()  # Only I/O is parametrized
    assert config is not None
```

### Mandate Compliance (CM-D)

- **CM-D**: Business logic extracted to pure functions. Impure code isolated behind adapters. Fixture parametrization applies only to adapter layer.

## The 3 Pillars (style backbone for acceptance tests)

These three pillars are the lens used during writing and review. They sit above Mandates 1-4: every scenario MUST embody all three before mandate compliance is even considered.

### Pillar 1 — Domain language with specific actions

Scenarios speak the domain, not incidental code. A domain expert can read stimulus/outcome without implementation. Reuse business-named domain steps and isolate parsing/subprocess/timeout mechanics behind them; the visible GWT/AAA step DSL requires no particular framework. Technical terms belong in the scenario only when they are actual public protocol/domain promises, not private plumbing. Assert outcome/state/types/required fields rather than incidental exact representation.

### Pillar 2 — Chained narrative

Within a story line, scenarios read as a sequence of state transitions: **the `Given` of scenario N equals the `Given + When` of scenario N-1**. Read in order, the tests tell the feature. The `Given` of scenario N never duplicates the setup of N-1: it reuses already-defined step methods (step composition, not copy-pasted fixtures).

### Pillar 3 — App as in production

Drive the SUT through production composition and the selected public port. Give each driven port its Architecture of Reference treatment under `nw-distill-port-treatment-policy`: focused acceptance scenarios use an in-memory fake for driven-internal storage and a capturing fake for driven-external dependencies; real driven-internal adapters belong to the feature's walking skeleton and declared adapter integration observations. Production composition does not mean production I/O in every scenario. Do not rebuild the business rule inside fixtures. State-machine properties may reuse a law-preserving native in-memory composition with an explicit preservation map; no particular composition class or DSL framework is required, but visible GWT/AAA domain steps are. Keep an identifiable feature E2E and distinct real storage/crash/race/protocol observations when promised.

## Mandate 16: Algebraic Analysis Before the Scenario

Do the analysis that a good bugfix would eventually force, at the moment the
scenario is authored. It is the same analysis either way; only its price
changes. Four questions, each paired with the imperative for its honest-no.

**1. What law does this scenario protect?**

> Name the property in one sentence — conservation, decomposition, a state
> transition, an oracle, a metamorphic relation. If the honest answer is "it
> checks that the feature works", **stop and name the law**: an unnamed law
> cannot tell you which observations are missing, and the scenario will drift
> into asserting whatever the implementation happens to do.

**2. What is the narrowest surface that carries that law?**

> Ask what the scenario must set up to observe it. If the answer is a whole
> subsystem — every sibling component satisfied, the unrelated ones patched out —
> **the law is being observed at the wrong altitude.** Push it down to the unit
> that owns it (a pure function over declared inputs, property-tested), and keep
> ONE example at the composition surface for the reporting/wiring claim. A
> scenario that fabricates a world to observe a small law has a failure surface
> as large as that world, and will break for reasons that have nothing to do with
> the law.

**3. Which inputs is the behaviour gated on — and does the scenario DECLARE
every one of them?**

> Walk the path from the driving port to the assertion and check it against the
> gate list in `contract:declared-inputs-not-ambient-reads`
> (`nw-cross-cutting-invariants` — one list, so it cannot drift between copies).
> For each gate, ask whether the scenario states it or inherits it. Answering
> "the fixture uses `tmp_path`, so it is hermetic" is the wrong answer:
> isolating the filesystem is not isolating the environment. **If it inherits,
> state it explicitly.**

**4. How would you know this scenario can fail?**

> Answering "it is green and the code is correct, so it is covered" is the wrong
> answer — a scenario that cannot fail is green for free, and green-for-free is
> indistinguishable from green-for-the-right-reason at the moment you read it.
> **Watch it go red for the reason it exists.** Authoring RED-first, the initial
> failure IS that evidence, provided you read WHY it failed: a collection or
> import error is not the law failing. Once it has gone green — after a refactor,
> or when the scenario predates the defect it now guards — re-inject the defect
> and watch it go red again. **Record which observations died and which
> survived**: laws that constrain shape correctly survive a content defect, and
> a suite where everything dies to everything is as uninformative as one where
> nothing does.
>
> This is a single deliberate check per scenario, at authoring time, on the
> defect the scenario names. It is NOT mutation testing, which this project
> disables as a routine gate (`CLAUDE.md` § Mutation Testing Strategy) — no
> generated mutants, no kill-rate, no scheduled run.

**Order-independence is part of the contract.** Before calling a scenario done,
run it ALONE in a fresh process. Passing only in file order is a defect of the
scenario, not a quirk of the runner: CI shards and parallel workers redistribute
tests, so a sibling's side effect is not a dependency you may rely on.

Design-time twins: the same two questions are stated for the architect and the
crafter in `nw-code-design-oo` and `nw-code-design-fp` (declared inputs at the
boundary; enumerate the outcomes before choosing the return type). Reaching
this mandate first, read those next.

Empirical anchor, 2026-08-06: three CI-only failures, three different suites, one
class — each scenario inherited host/platform state instead of declaring it, and
one of them additionally drove an entire installer to observe a single
byte-comparison. Fixing them by declaring the input took minutes; finding them
cost four refuted hypotheses each, because a scenario that reads ambient state
gives no signal about WHICH state it read.
