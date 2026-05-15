---
name: nw-test-design-mandates
description: Design mandates for acceptance tests - hexagonal boundary, business language abstraction, user journey completeness, pure function extraction, 3 Pillars (domain language / chained narrative / production composition), and the layered ATD discipline (Universe-bound assertion, layer-dependent PBT mode, two-tier acceptance, example-based sad paths)
user-invocable: false
disable-model-invocation: true
---

# Acceptance Test Design Mandates

Four mandates enforced during peer review. All must pass before handoff to software-crafter.

## Mandate 1: Hexagonal Boundary Enforcement

Tests invoke through driving ports (entry points), never internal components.

### Driving Ports (Test Through These)
Application services/orchestrators | API controllers/CLI handlers | Message consumers/event handlers | Public API facade classes

### Not Entry Points (Never Test Directly)
Internal validators, parsers, formatters | Domain entities/value objects | Repository implementations | Internal service components

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

**Layer 1 - Gherkin**: Pure business language, all stakeholders. Domain terms from ubiquitous language | Zero technical jargon | Describe WHAT user does, not HOW system does it

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

## Mandate 3: User Journey Completeness

Tests validate complete user journeys with business value, not isolated technical operations.

### Complete Journey Structure
Every scenario includes: **User trigger** (Given/When) | **Business logic** (When - system processes rules) | **Observable outcome** (Then - user sees result) | **Business value** (Then - value delivered)

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

Balance user-centric E2E integration tests with focused boundary tests.

### Walking Skeletons (2-5 per feature)
Trace thin vertical slice delivering observable user value E2E | Each answers: "Can a user accomplish this goal and see the result?" | Express simplest complete user journey | Validate system delivers demo-able stakeholder value | Touch all layers as consequence of journey, not as design goal

### Walking Skeleton Litmus Test
1. Title describes user goal ("Customer purchases a product") not technical flow ("Order passes through all layers")
2. Given/When describe user actions/context, not system state setup
3. Then describe user observations (confirmation, email, receipt), not internal side effects (DB row, message queued)
4. Non-technical stakeholder can confirm "yes, that is what users need"

### Focused Scenarios (15-20 per feature, majority)
Test specific business rules at driving port boundary | Test doubles for external dependencies (faster, isolated) | Cover business rule variations and edge cases | Invoke through entry point (OrderService, Orchestrator)

### Recommended Ratio
For typical feature with 20 scenarios: 2-3 walking skeletons (user value E2E) | 17-18 focused scenarios (boundary tests with test doubles). Walking skeletons prove users achieve goals. Focused scenarios run fast, cover breadth. Both use business language and invoke through entry points.

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
   - Acceptance tests use real adapters; unit tests use fakes
5. Parametrize fixtures ONLY for the thin adapter layer that connects to real environments

**Rationale**: Parametrizing fixtures across environments is expensive. Pure functions need zero environment setup. Extract first, parametrize the minimum.

### Violation Pattern

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

Scenarios speak the domain, not the code. A domain expert reads them without seeing a single line of implementation. Step names are semantic (`User_signs_up`, NOT `Call_signup_endpoint`). Technical jargon (HTTP, JSON, schema, endpoint, database) is forbidden in scenario titles, Gherkin steps, and step-method names. Technical detail lives inside step bodies only.

### Pillar 2 — Chained narrative

Within a story line, scenarios read as a sequence of state transitions: **the `Given` of scenario N equals the `Given + When` of scenario N-1**. Read in order, the tests tell the feature. The `Given` of scenario N never duplicates the setup of N-1: it reuses already-defined step methods (step composition, not copy-pasted fixtures).

### Pillar 3 — App as in production

The SUT is built via the production composition root (style `WebApplicationFactory` or equivalent). Only **external / non-deterministic ports** (clock, email, SMS, push, payment, LLM, third-party APIs) are substituted by fakes/stubs. The app is never rebuilt by hand replicating the wiring. Tier B (state-machine PBT, Mandate 10) uses an `InMemoryComposition` root that honors the same interfaces — same vocabulary, different composition root.

## Mandate 8 — Universe-bound assertion at layers 1-3

Every test at layers 1-3 (unit, in-memory acceptance, subprocess/FS acceptance) that mutates observable state MUST assert via `assert_state_delta(before, after, universe={...}, expected={...})` (Python reference: `nwave_ai/state_delta/__init__.py`; other-language equivalents are added as the matrix grows).

- `universe` declares the SET of port-exposed observable names the test promises to track. Names are always port-exposed (event types, public read-model fields, exit codes, captured outputs) — never internal struct fields.
- `expected` declares which universe entries change and how (predicate per entry: `set_to`, `unchanged`, `appended_with`, `prepended_with`, `containing`, ...).
- Anything in `universe` that changes UNEXPECTEDLY (mutates with no `expected` entry) → violation. Fail-closed.
- Layers 4+ (integration, walking-skeleton, E2E) MAY use traditional assertions — at that layer the test cost is dominated by subprocess / network / real I/O and the universe-guard payoff is smaller.

Bad universe entries couple the test to private mutation details (`BoardProjection._rows_cells_dict`) — a refactor rename reds the test for no functional reason. Good universe entries are port names (`events.PhaseEntered.emitted_count`, `board.rows[task_id].cells[wave].status`).

## Mandate 9 — PBT input mode is layer-dependent

Property-based test machinery (Hypothesis `@given`, `RuleBasedStateMachine`, equivalent in other languages) is constrained by layer:

- **Layers 1-2** (unit, in-memory acceptance with in-memory doubles): PBT full. Hypothesis explores the generative input space (100+ examples per property by default). Pinned `@example(...)` preserves a domain-readable canonical case for reviewers.
- **Layers 3-6** (subprocess/FS acceptance, integration, walking-skeleton, E2E): example-only. Sad paths are enumerated explicitly, never PBT-generated. PBT runtime cost is incompatible with real-I/O tests where each example is 100ms–seconds.

Rationale: layer 3+ tests serve wiring proof and contract verification; coverage exploration happens at layers 1-2 where iteration is cheap.

## Mandate 10 — Two-tier acceptance for rich journeys

Acceptance tests come in two tiers. Tier A is mandatory. Tier B is optional and applied only to rich journeys.

- **Tier A — Gojko-style**: production composition root, real DI, example-only, 1-2 scenarios per journey. Lives in `.feature` files (Gherkin) + `steps_*.py` (or host-language equivalent) invoking the production composition root. Purpose: prove wiring end-to-end, demonstrate the feature works for the canonical example.
- **Tier B — state-machine PBT** (optional): in-memory doubles composition root, generative inputs, `RuleBasedStateMachine` with `@rule` / `@precondition` / `@invariant`. Lives in `test_<feature>_state_machine.py` (or host-language equivalent), separate file from the `.feature`. Purpose: explore the journey state space and surface contract gaps that example tests miss.

**Vocabulary shared**: the same step-methods (`Given_/When_/Then_` named in the domain language) are invoked from both tiers. Step-methods are the contract; the two tiers are two composition roots over the same vocabulary.

**Composition root contract**:
- Tier A uses real DI (e.g. `WebApplicationFactory` in C#, real installer entry-point in Python, real router in Go).
- Tier B uses an `InMemoryComposition` class that wires the same interfaces with in-memory doubles. The `InMemoryComposition` exposes a `capture_universe()` method returning the universe snapshot used by `assert_state_delta`.

**When to add Tier B**:
- Journey has ≥3 chained scenarios (Pillar 2 active), AND
- Input space is domain-rich (emails, dates, payloads, free-text, IDs from a large set).

**When Tier B is NOT worth it**:
- Config-shaped features (single-shot installer config, schema validation, one-off CLI).
- Journeys with 1-2 scenarios (Tier A example covers the space).
- Features where the only observable is "did it crash" (no state mutation to model).

## Mandate 11 — Integration sad paths stay example-based

Sad-path coverage at layers 3+ (subprocess / real adapter / integration / WS / E2E) uses traditional example-based tests, one example per failure mode.

- No PBT explosion on slow tests. The wall-clock cost of generating sad inputs against a real adapter dwarfs the gain.
- `assert_state_delta` is OPTIONAL at layer 3+ (universe-guard is a Mandate 8 layer 1-3 requirement; layers 4+ may use traditional assertions per Mandate 8).
- Each sad path is named explicitly: `Bug_<symptom>` or `Sad_<scenario>` test, with explicit input that triggers the failure.
- Coverage requirement: every failure mode enumerated in DEVOPS environment matrix and every `failure_modes` entry from `docs/product/journeys/<name>.yaml` gets at least one named sad-path test.

## Layered Test Discipline

The four mandates above (Universe, PBT mode, two-tier acceptance, sad-path treatment) compose into this layered discipline. The table below is the single source of truth for "what does this layer look like."

| Layer | Speed | Real adapter? | Input mode | Assertion mode |
|---|---|---|---|---|
| Unit | <1ms | no | PBT full (`@given` 100+ examples) | state-delta + Universe |
| In-memory acceptance | ~10ms | no (in-memory doubles) | PBT example-pinned if AC tagged `@property`; example-only otherwise | state-delta + Universe |
| Subprocess / FS acceptance | ~100ms | yes (real adapter) | example-only — sad paths enumerated | state-delta + Universe |
| Integration | ~100ms | yes | example-only, sad-path coverage | traditional OK; state-delta optional |
| WS `@wiring_e2e` | 1-3s | yes (real stack) | example-only (1-2 representative) | traditional |
| E2E | seconds | full real | example-only | traditional |

**Polyglot note**: the Universe / state-delta contract is language-agnostic — the prose is the contract, the Python imports (`nwave_ai.state_delta`) are illustrative. Other host languages add their own matrix row + template lazily (Python is the current pilot).

## Polyglot Adapter Matrix

Contract layer (3 Pillars + Mandates 8-11) is language-agnostic. Implementation
bindings per language are documented in the matrix below. Python ships ready;
other languages are bootstrap-on-demand templates (Epic 3+).

| Lang | PBT lib | xunit equiv | Skip marker | Step composition idiom |
|---|---|---|---|---|
| Python | hypothesis | pytest | `pytest.mark.skip(reason="pending")` | pytest-bdd `.feature` + `steps_*.py` |
| TypeScript | fast-check | Vitest/Jest | `it.skip(...)` | `*.scenarios.ts` + `*.specifications.ts` |
| C# | FsCheck | xUnit | `[Fact(Skip="pending")]` | partial class `*Scenarios.cs` + `*Specifications.cs` |
| Java | jqwik | JUnit | `@Disabled("pending")` | companion test class |
| Kotlin | kotest-property | Kotest | `@Disabled` | extension functions split |
| Rust | proptest | std `#[test]` | `#[ignore]` | `<feature>_scenarios.rs` + `<feature>_specifications.rs` (same module) |
| Go | rapid o gopter | testing | `t.Skip("pending")` | `*_scenarios_test.go` + `*_specifications_test.go` |

**State-delta port** per language lives at the project-local path
`tests/common/state_delta.<ext>` (apply-if-absent on first DISTILL in the
project). Python port is canonical at `nwave_ai/state_delta/`. Other-language
ports are templated bootstraps from the per-lang Tier-2 expansion catalogs.

**Universe assertion contract** is identical across languages: every
state-mutating test at layers 1-3 calls `assert_state_delta(before, after,
universe, expected)` (Python signature; idiomatic translations preserve the
same four parameters). Universe declares observable port-exposed names;
expected maps each declared key to a predicate. Anything in universe not in
expected MUST remain unchanged — fail-closed.

**Per-lang predicate library** mirrors the Python set: `set_to`, `unchanged`,
`appended_with`, `containing`, `normalized_to`, `idempotent_after`,
`legacy_healed`, `prepended_with`. Each language port implements all eight
with the same semantic contract.

## Mandate Compliance Verification

Handoff to software-crafter includes proof all mandates pass:

- **CM-A** (Mandate 1): All test files import entry points (driving ports), zero internal component imports
- **CM-B** (Mandate 2): Gherkin uses business terms only, step methods delegate to services
- **CM-C** (Mandate 3): Scenarios validate complete user journeys with business value
- **CM-D** (Mandate 4): Business logic extracted to pure functions. Impure code isolated behind adapters. Fixture parametrization applies only to adapter layer.
- **CM-E** (Mandate 8): Every step-method at layers 1-3 uses `assert_state_delta(before, after, universe, expected)` with port-exposed universe entries
- **CM-F** (Mandate 9): PBT decorators (`@given`, `RuleBasedStateMachine`) appear only on layer 1-2 tests; layer 3+ tests are example-only
- **CM-G** (Mandate 10): If journey is ≥3 chained scenarios with rich input space → Tier B `test_<feature>_state_machine.py` exists alongside Tier A `.feature`
- **CM-H** (Mandate 11): Layer 3+ sad paths are named example-based tests; no PBT machinery imported

Evidence: import listings, grep for technical terms, walking skeleton identification, focused scenario count, pure function extraction inventory, universe-entry audit (grep for `_` prefix in universe names → flag internal-field leakage), tier-B file presence check.
