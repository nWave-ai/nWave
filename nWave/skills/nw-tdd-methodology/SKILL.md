---
name: nw-tdd-methodology
description: Deep knowledge for Outside-In TDD - double-loop architecture, ATDD integration, port-to-port testing, walking skeletons, and test doubles policy
user-invocable: false
disable-model-invocation: true
---

# Outside-In TDD Methodology

## TDD cycle — 3-phase canonical (ADR-025, 2026-05-07)

**Current canonical**: DELIVER cycle is 3-phase: **RED → GREEN → COMMIT**.

- **RED** absorbs PREPARE + RED_ACCEPTANCE + RED_UNIT (legacy 5-phase). Writes PBT unit tests targeting production code; unskips the corresponding AT scenario authored upstream by DISTILL. Exits via the **fail-for-right-reason gate** — both PBT unit + AT must fail with a semantically-correct error (AssertionError / expected-exception-not-thrown), not a collection error / import error / skip marker. The gate preserves RED→GREEN discipline atomically without separate phase boundaries.
- **GREEN**: implement minimum production code making PBT unit + AT pass. Exit gate `all-tests-pass`.
- **COMMIT**: stage + commit with `Step-Id:` trailer. Pre-commit hooks enforce style; F-DES-COMMIT-PHASE-CRAFTER-DEAD-PATH guidance in commit.yaml addresses adapter-probe annotation requirement.

**DISTILL retains canonical AT authorship** (per `nw-distill` Mandate 7). RED phase in DELIVER does NOT write acceptance scenarios from scratch — it only unskips the scaffolds DISTILL produced.

**Legacy (5-phase v4 contract, ADR-024 era)** — PREPARE / RED_ACCEPTANCE / RED_UNIT / GREEN / COMMIT — preserved for audit-log replay of pre-2026-05-07 commits. Future features use 3-phase canon. References to RED_ACCEPTANCE / RED_UNIT below describe the legacy contract; new work treats them as merged inside RED.

## Paradigm Mandate — Property-Based + State-Delta (STANDING, 2026-05-05)

**Default test-writing paradigm for UNIT + ACCEPTANCE tests — not optional, not "when applicable".**

### Test-level applicability matrix

| Level | Default paradigm | Rationale |
|---|---|---|
| **Unit** | Property-based + state-delta — single-example is FALLBACK only | Property tests cover equivalence classes; the state-delta universe forbids hidden mutations on adjacent slots |
| **Acceptance (Gherkin)** | `Property:` framing with quantified preconditions; classic `Scenario:` is FALLBACK | Acceptance tests document system invariants; properties express the spec better than picked examples |
| **Integration** | UNCHANGED — single-example test verifies WIRING | The contract is "wires connect correctly", not "all input shapes succeed". One representative call suffices |
| **E2E** | UNCHANGED — single-example end-to-end happy path | The contract is "complete flow connects", not "all flows are equivalent". One golden walkthrough suffices |

### Mandate (unit + acceptance levels)

Every unit and acceptance test you write MUST be:

1. **Property-based by default** — use Hypothesis `@given` strategies to explore equivalence classes, NOT single-fixture examples. A property test asserting an invariant over N generated inputs replaces N example tests with stronger semantic coverage.

2. **State-delta over single-property assertion** — capture the FULL observable state surface (universe), declare the expected delta with predicates (`prepended_with`, `set_to`, `unchanged`, `containing`, `idempotent_after`, `legacy_healed`, `normalized_to`, `appended_with`), and call `assert_state_delta(before, after, universe, expected, strict=True)`. `strict=True` forbids hidden mutations on adjacent slots — this is what catches bugs that pinned-fixture asserts miss.

```python
from hypothesis import given, settings, strategies as st
from nwave_ai.state_delta import assert_state_delta, set_to, unchanged

@given(domain_input=domain_specific_strategy())
@settings(max_examples=100, deadline=None)
def test_pbt_invariant(domain_input):
    before = capture_full_state()
    perform_action(domain_input)
    after = capture_full_state()
    assert_state_delta(
        before, after,
        universe={"slot.a", "slot.b", "slot.c", "slot.d"},
        expected={"slot.a": set_to(expected_from(domain_input)), "slot.b": unchanged()},
        strict=True,
    )
```

3. **Acceptance tests express PROPERTIES of the system** — Gherkin scenarios should be framed as `Property: <invariant statement>` with quantified preconditions ("a set of N tasks with arbitrary timestamps") and invariant outcomes ("monotonically descending by timestamp"), instead of single-example `Scenario:` blocks. Step definitions internally use `@given` strategies + state-delta assertions.

**OLD pattern (banned by default)**:
```gherkin
Scenario: Operator sees three tasks ordered by recency
  Given tasks A, B, C with timestamps T1 < T2 < T3
  When the operator runs `prism board`
  Then the board shows: B (T2), C (T3), A (T1) — wait, ordered descending: C, B, A
```

**NEW pattern (required default)**:
```gherkin
Property: Board column order reflects recency
  Given a set of N tasks with arbitrary timestamps
  When the operator runs `prism board`
  Then the column order is monotonically descending by timestamp
  And no task appears twice in the column
  And every input task appears exactly once in the output
```

**Fallback** — when property-framing genuinely cannot express the contract (e.g., flow-specific UI tests with puntual outcomes, golden-file diffs, error messages with exact strings):
- Write classic example-based test
- Document WHY property-framing failed in a one-line `# bypass:` comment
- Compensate by adding stronger PBT at unit/integration level

**Forbidden bypass paths** (insufficient justification):
- "Single-property is enough" — NO. Always declare the universe, even if only one slot is checked. `unchanged()` predicate covers the rest.
- "Mock-based interaction test" — NO. Mocks are still observable state; their call-recording surface is part of the universe (`mock.call_count`, `mock.last_call_args`).

**Exempt categories** (still apply paradigm where it adds value, but not mandatory):
- Pure-function tests with single output and no side effects
- Schema/AST validators with single output
- Smoke imports

### Goals

| Goal | Old paradigm | New paradigm |
|---|---|---|
| Number of tests | N example-tests per contract | 1 PBT covers N+ examples |
| Token consumption | High (N test bodies, N test names) | Low (one body, one strategy) |
| Coverage | Pinned by chosen examples | Discovered via Hypothesis shrinking |
| Bug-finding | Limited to imagined cases | Includes edge cases author didn't think of |
| Documentation value | Examples may diverge from spec | Property = invariant = living spec |
| Speed | Slower (more tests to run) | Faster (fewer tests, same coverage) |

### Empirical efficacy framework — debt-payoff curve (NOT instantaneous hit rate)

**Reframing (Ale 2026-05-05)**: paradigm efficacy is measured via the **debt-payoff curve over a surface's lifetime**, not via instantaneous hit rate snapshots.

#### Three stages

| Stage | Surface state | Expected hit rate | Meaning |
|---|---|---|---|
| **Stage 0** | New code, paradigm-from-day-zero | N/A — debt never accumulates | **Healthy by construction**. Tests catch hidden mutations as they emerge |
| **Stage 1** | Bug-prone, debt-accumulated, never-cured | 33–75% (state-delta migration) | **Debt-payoff phase**. High yield = years of single-property-asserts being unmasked |
| **Stage 2a** | Stage-1-completed surface, PBT amplification | ~0% by design | **Maintenance mode**. Debt is paid; PBT now catches in-flight regressions, not retroactive ones |
| **Stage 2b** | Bug-prone, never-migrated, PBT amplification | ~75% (per hardening empirical) | Same as Stage 1 — surface still has accumulated assumptions |

#### Empirical evidence (2026-05-05 pilot, 2 instances)

| Pilot | Stage | Surface | Hit rate | Source |
|---|---|---|---|---|
| Stage 1 state-delta migration | Stage 1 | installer plugin tests, never cured | 4/9 = 44% |
| Stage 2a PBT amplification | Stage 2a | plugin code post Stage 1 | 0/3 = 0% (post commit `29daeb102`) |

**Reading the data correctly**: the master 0% is NOT failure — it's confirmation that Stage 1 already extracted the debt. Stage 2a on a cured surface validates the surface stays healthy. Stage 2b on an uncured surface re-confirms paradigm yield on debt-accumulated code.

#### Implication for AI delegation (the deeper point)

Humans accumulate test debt (single-property-asserts, missed-universe-keys, post-state-only). Machines applying the paradigm **from day zero** (Stage 0) do NOT accumulate debt by construction. Therefore: **AI-written code under paradigm enforcement has lower debt-rate than human-written code**, given equivalent specification quality.

This is why paradigm-as-default for NEW unit tests (the mandate above) matters more than migration: migrations are one-time cleanup; the long-term value is **never accumulating debt to migrate**.

**The paradigm is the environment modification that lets machines build software with lower debt over time** (Ale 2026-05-05).

---

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
- Few Given/When/Then examples, not many | Separate requirements from tests
- Smallest subset of team with relevant skills | Value = shared understanding, not executable specs
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

## Port-to-Port Testing (ALL test levels)

ALL tests — acceptance, unit, integration — enter through a driving port and assert outcomes at driven port boundaries. No exceptions.
Internal classes (entities, value objects, domain services) exercised indirectly — never instantiated directly in test code.

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

**Walking Skeleton subset rule**: WS / `@wiring_e2e` scenarios go through real subprocess + real I/O. Use **sparingly** — 1-2 per slice. The rest of acceptance scenarios run through driving-port direct invocation with in-memory doubles for driven ports. Mandate 1 ("subprocess invocation real I/O") in `walking-skeleton.feature` is for WS only, not all acceptance.

**Universe construction rule**: derive Universe from the layer's *observable surface*, never from internal struct/field names. A Universe entry like `composition.startup_status` is correct (port-exposed); `fold._rows_cells_dict` is wrong (internal mutation detail — refactor will red the test).

**Refactoring resilience smoke check**: rename a private helper → suite stays GREEN. If red, the test was coupling to impl. Eliminate or refactor port-to-port at the right layer.

## No Code Without a Requiring Test

Every line of production code exists because a test required it. No speculative implementation.

- Acceptance test drives WHAT is needed (observable behavior)
- Unit test drives HOW to decompose (inner loop, only when GREEN is complex)
- If the acceptance test passes without a unit test, no unit test is needed
- If a step finds "already implemented from WS, just remove @skip" — that's CORRECT

The test pyramid is not a quota system. Write the minimum tests that give confidence at the right level.

## Unit of Behavior (not Unit of Code)

Test = story about the problem your code solves. Granularity related to stakeholder needs.
A unit of behavior may span multiple classes. Test from driving port to driven port boundary.
Key question: "Can you explain this test to a stakeholder?" If not, you're testing implementation details.

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

## Hexagonal Architecture Testing Strategy

### Domain Layer
Tested indirectly through driving port (application service) unit tests with real domain objects.
Domain entities, value objects, domain services are implementation details. Testing them directly couples tests to internal structure.

Pure domain functions (e.g., evaluate_gate, check_tier) ARE their own driving ports — calling them directly in tests IS port-to-port testing because the function signature IS the public interface. This is not an exception; it's the correct application of port-to-port to the domain layer.

### Application Layer
Classical TDD within layer, Mockist TDD at port boundaries.
Use real Order, Money, Customer objects in application service tests.
Mock IPaymentGateway, IEmailService ports when testing orchestration.

### Infrastructure Layer (Adapters)
Integration tests ONLY — no unit tests for adapters. Mocking infrastructure inside an adapter test is testing the mock, not the adapter.
Use real infrastructure (testcontainers, in-memory databases, real filesystem via tmp_path, real subprocess) to verify actual behavior.

Adapter integration tests are typically created to make the Walking Skeleton pass — the WS requires real adapters, which drives the implementation of the adapter AND its integration test. Additional adapter tests for specific error conditions (disk full, timeout, permission denied) are created in subsequent focused scenarios tagged `@infrastructure-failure` (see Mandate 6). Subsequent happy-path scenarios use InMemory doubles for speed; the adapter correctness is proven by the WS + infrastructure failure scenarios.

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

## Walking Skeleton Protocol

At most one walking skeleton per new feature. When `is_walking_skeleton: true` in roadmap:
- Write exactly ONE E2E/acceptance test proving end-to-end wiring with REAL adapters
- Implement thinnest possible slice — hardcoded values, minimal branching
- Unit tests are written ONLY if needed to decompose complex GREEN implementation
- Do NOT add error handling, edge cases, or validation beyond what the AT requires
- No code without a test that requires it — the AT drives ALL implementation

The WS is an acceptance test on steroids: it proves wiring AND drives implementation of adapters, domain logic, and application services. If the WS AT requires 5 functions to pass, those 5 functions are justified. Subsequent steps that find "already implemented, just remove @skip" confirms the WS was well-designed.

Integration tests for adapters (real filesystem, real subprocess) are naturally created during WS — the WS REQUIRES real adapters, which drives their implementation and testing.

## Post-GREEN Wiring Verification (MANDATORY)

After ALL tests pass in GREEN phase and BEFORE proceeding to COMMIT:

1. Run `git diff --name-only` and verify that EVERY file listed in the step's
   `files_to_modify` appears in the diff. If a production file is NOT modified
   but tests flipped from RED to GREEN, this is **Fixture Theater** — the test
   fixtures are implementing the feature, not production code. BLOCK the COMMIT.

2. **Deletion test**: Mentally (or actually) revert production changes. Would
   tests still pass? If yes, the test is exercising fixture state, not production code.

3. If `git diff --stat` shows ONLY test file changes, STOP. Go back to GREEN
   and implement the production code. Tests passing without production changes
   is a DES integrity violation.

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

## Mandate 5: Walking Skeleton E2E Strategy

The DISTILL acceptance designer determines the WS adapter strategy for each feature. This is auto-detected with user confirmation, not a question to the user.

### Decision Tree

```
Feature is pure domain (no driven ports with I/O)? → Strategy A (InMemory)
Feature has only local resources (filesystem, git, in-process)? → Strategy C (Real local)
Feature has costly external dependencies (paid APIs, LLM calls)? → Strategy B (Real local + fake costly)
Team needs CI flexibility? → Strategy D (Configurable via env var)
```

### Resource Classification Table

| Resource Type | WS Local | WS CI | Adapter Integration Test |
|--------------|----------|-------|------------------------|
| Filesystem | real (tmp_path) | real (tmp_path) | real (tmp_path) — ALWAYS |
| Git repo | real (tmp_path + git init) | real | real — ALWAYS |
| Local subprocess (pytest, ruff, grep) | real | real | real — ALWAYS |
| Costly subprocess (claude -p, LLM) | fake (mock Popen) | fake | contract smoke (@requires_external) |
| Paid external API (Stripe, Blumberg) | fake server | fake server | contract test with recorded fixtures |
| Database | real (SQLite/testcontainers) | real (testcontainers) | real — ALWAYS |
| Container services | optional (docker-compose) | testcontainers | real if available |

### Walking Skeleton Adapter Rule

Under strategies B/C/D, the WS uses real adapters for local resources. InMemory is ONLY for costly external resources that have a separate contract test.

### Determinism Contract

Real-adapter WS tests accept non-determinism as a trade-off for environmental realism. InMemory acceptance tests remain the fast deterministic inner loop. The WS is the slow truth-checking outer loop. Both are necessary. If WS fails, triage: logic failure (fix code) or environment failure (retry, investigate infra).

### Rollback Policy

If WS with Strategy C fails due to infrastructure issues (not code bugs), downgrade to Strategy B for that step. Document the downgrade in wave-decisions.md with justification.

## Mandate 6: Adapter Integration Tests Are Real I/O

Every driven adapter has at least ONE integration test with real I/O. This is not optional regardless of WS strategy.

### Adapter Type Minimum Real I/O Test

| Adapter Type | Minimum Real I/O Test |
|-------------|----------------------|
| Filesystem adapter | tmp_path fixture, real read/write/delete |
| Subprocess adapter (local) | real subprocess call, real exit codes |
| Subprocess adapter (costly) | contract smoke test with @requires_external marker |
| Config/env adapter | real env vars or real config file on tmp_path |
| Git adapter | real temp git repo (tmp_path + git init + git commit) |
| Database adapter | real DB (SQLite in-memory or testcontainers) |
| Network/HTTP adapter | contract test against recorded fixture or fake server |

"Real" means: the test would FAIL if the adapter's actual system dependency is absent or broken.

### Tagging Convention for Enforcement

- Scenarios using real adapters: `@real-io`
- Scenarios using InMemory: `@in-memory`
- Walking skeleton: `@walking_skeleton` + `@real-io` (for strategies B/C/D)

## Delta-First Test Paradigm (state-mutating code)

**Scope**: ~28% of the test suite (419 test files audited). Applies to installer-class, sync-class, and hook-registration code that mutates user-observable state. NOT universal. Pure-function tests, schema validators, and interaction tests retain standard assertion style.

### Trigger — apply delta-first when ALL of these hold

1. The test mutates user-observable state in **2 or more** distinct slots (e.g. filesystem path + config key + env setting).
2. OR the test implicitly asserts "preserve X" semantics — i.e., the correctness claim is partly about what did NOT change.
3. The code under test is in `scripts/install/`, `scripts/sync/`, or any hook-registration path.

### Bypass — do NOT apply delta-first when

- Pure-function tests with a single return value (no side effects).
- Single-property assertion (`assert result.returncode == 0`).
- `validate_prerequisites()` failure paths (returncode / boolean / exception only).
- Interaction tests (`mock.assert_called_with(...)`) — no universe to declare.
- AST / schema / YAML validators.
- Adding 3-5× ceremony for zero additional detection gain vs. a direct `assert`.

### Pattern

```python
from nwave_ai.state_delta import (
    assert_state_delta,
    prepended_with,
    unchanged,
    set_to,
    containing,
)

def test_des_plugin_installs_hook(tmp_path):
    before = capture_state(tmp_path)   # snapshot before action

    plugin.install(context_for(tmp_path))

    after = capture_state(tmp_path)    # snapshot after action

    assert_state_delta(
        before,
        after,
        universe={
            "hooks.pre_tool_use",      # every slot that COULD change
            "hooks.post_tool_use",
            "config.rigor",
        },
        expected={
            "hooks.pre_tool_use": prepended_with("des_hook.py"),
            "hooks.post_tool_use": unchanged(),
            "config.rigor": set_to("standard"),
        },
        # implicit-unchanged: any universe slot NOT in expected must be identical
    )
```

Full API: `assert_state_delta(before, after, universe, expected, *, strict=False)`.

Available predicate factories: `prepended_with`, `appended_with`, `unchanged`, `set_to`, `containing`, `normalized_to`, `idempotent_after`, `legacy_healed`.

Import: `from nwave_ai.state_delta import assert_state_delta, <predicates>`.

### Empirical justification

Migration of 7 installer test files: **4/7 (57%) exposed previously-untracked mutations** that post-state-property assertions had missed.

Hidden mutations caught:
- `attribution.trailer` written silently (`test_attribution_plugin`) — post-state test only checked `returncode`.
- `content.full` transitioned `None → str` (`test_opencode_des_plugin`) — old assertion never declared `content.full` in universe.

### Reusable helpers that emerged from migration

- `_flatten_config(path)` — flattens a JSON/YAML config into dotted key paths.
- `_skill_filesystem_state(target_dir, track=)` — snapshots skills directory into slot dict.
- `_*_content_state(target_dir, name)` — snapshots a named agent/command content file.

### References

- Source: `nwave_ai/state_delta/matcher.py`
- Canonical migrated example: `tests/installer/unit/plugins/test_attribution_plugin.py`
- D-12 hard gate examples: `tests/state_delta/integration/test_pilot_bug48.py`

## PBT Anti-Patterns

- **A13: Stateful PBT without command-precondition encoding** — when generating commands for state-machine PBT, encode constraints as `precondition/2` callbacks, NOT just inside the generator. PropEr/Hypothesis shrinking REQUIRES preconditions to drop invalid commands during shrinking; without them, shrunk counter-examples point at ghost bugs (Hebert ch.10 bookstore case study spent half a chapter chasing this exact symptom).

## PBT Priorities

- **P6: Stateful command preconditions** — When the SUT is a state machine (per Hebert ch.11 framing: model-shape-is-state-machine, not user-perceived states), encode all command validity constraints in `precondition/2` callbacks. Required for shrinking correctness. Without P6, A13 fires.

## PBT Thinking — Property-Finding Strategies

### Hebert's four strategies (ch.3)

When you don't know what property to write, walk Hebert's ch.3 catalogue first. These are the **Tier 1 (Hebert ch.3 core)** strategies:

- **Modeling** — SUT vs simpler-but-obviously-correct reference (maps to skill's "Oracle" pattern). Build a simpler reference implementation, compare outputs.
- **Generalizing example tests** — parameterizing existing example tests with strategies; take a known correct answer, embed it in the input, predict where it should appear in the output.
- **Invariants** — output property holds regardless of input (maps to skill's "Invariant" pattern). Combine multiple — a single invariant is rarely enough.
- **Symmetric properties** — reversible sequence of actions: applying both yields the original input (maps to skill's "Roundtrip" pattern, e.g., encode/decode, push/pop).

Other patterns commonly cited (Commutativity, Idempotence, Hard-to-compute-easy-to-verify, Induction, Metamorphic relation, Test oracle as standalone) are **Tier 2 (Link extension)**, not Hebert. Keep them as a supplemental pattern library; Tier 1 is the minimum.

## Shrinking — Hebert's Two Mechanisms (ch.7)

Hebert ch.7 documents only TWO shrinking mechanisms:

- `?SHRINK(Generator, FallbackGenerators)` — re-center on a smaller value. Provides simpler-but-domain-relevant alternative generators used during shrinking. Hypothesis equivalent: explicit `min_value=`, `min_size=`, or `st.from_regex` constraining to the domain's natural range.
- `?LETSHRINK([Generators])` — divide-and-shrink each independently. Use to enable structural pruning of recursive generators; `?LET` shrinks contents but not structure.

Any other shrinking mechanism mentioned elsewhere (e.g., adaptive shrinking, integrated shrinkers as a separate concept) is **community-extension, not core Hebert**.

## Targeted PBT (Hebert ch.8)

Search-based PBT replaces random search with simulated annealing: report a *utility value* per test case, and the framework biases the next input toward inputs that improved the utility.

- `?USERNF(Generator, Next)` custom-neighbor function — controls how the search moves between samples. Hebert ch.8 sidebar "Considering Temperature" reports temperature-scaled custom neighbors are *"almost fifty times more effective"* than the same neighbor without temperature on tree-skewing search. The 50× claim is conditional on temperature usage, not on raw custom neighbors.
- `?EXISTS(Vars, Generator, Property)` and `?NOT_EXISTS(Vars, Generator, Property)` — search-macro family underlying `?FORALL_TARGETED`.

**Two hard limitations** (Hebert ch.8):

1. No recursive generators with `?LAZY` under targeted (infinite loops).
2. No `collect/2` / `aggregate/2` statistics under targeted (instrumentation incompatible with the search loop).

**Tuning parameter** (not a limitation): default search budget for targeted properties is 1000 steps (vs 100 for regular `?FORALL`); configurable via `-s` / `--search_steps`.

Hypothesis equivalent: `target()` registers a quantity; the engine biases toward maximising it. Same limitations apply in spirit (recursive strategies + statistics interplay poorly with `target()`).
