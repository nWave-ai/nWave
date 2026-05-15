---
name: nw-distill
description: "Acceptance test creation methodology for the DISTILL wave. Domain knowledge for the acceptance designer agent: port-to-port principle, prior wave reading, wave-decision reconciliation, graceful degradation, and document back-propagation."
user-invocable: true
argument-hint: '[story-id] - Optional: --test-framework=[cucumber|specflow|pytest-bdd] --integration=[real-services|mocks]'
---

# DISTILL Methodology: Acceptance Test Creation

This skill provides the acceptance designer's methodology for creating acceptance tests. The orchestrator controls the overall flow (agent dispatch, review gate, handoff) -- this skill focuses on HOW to create good acceptance tests.

## ADR-025 (2026-05-07) — DISTILL is canonical AT author

DISTILL produces ALL acceptance tests as scaffolded RED (skip/pending markers). DELIVER's 3-phase cycle (RED / GREEN / COMMIT, per ADR-025) does NOT re-author ATs in RED — it only unskips the scaffolds and writes PBT unit tests. Wave separation: DISTILL = "what should the system do" (ATs), DELIVER = "how" (PBT unit + impl). The pre-DELIVER fail-for-right-reason gate (described in this skill) becomes the RED phase entry/exit gate in DELIVER per ADR-025 D2.

## Output Tiers (per D2)

Provenance: feature `lean-wave-documentation` — D2 (schema-typed sections), D10 (one-line expansion descriptions). Tier-1 [REF] sections (always emitted) + Tier-2 EXPANSION CATALOG items (lazy, on-demand) are the two output bands. The `.feature` file remains the SSOT for scenarios; the wave-delta sections are pointers + structured summaries. Full contract: `nWave/skills/nw-density-resolution-contract/SKILL.md`.

### Tier-1 [REF] — always emitted

Under `## Wave: DISTILL / [REF] <Section>` headings:

- Scenario list with tags — table of scenario titles + tags (`@walking_skeleton`, `@US-N`, `@real-io`, `@in-memory`, `@error`, `@property`)
- WS strategy — A/B/C/D selection per Mandate 5 with one-line justification
- Adapter coverage table — per Mandate 6, every driven adapter mapped to at least one `@real-io` scenario
- Scaffolds — list of RED-ready scaffold files created (per Mandate 7) with `__SCAFFOLD__` markers
- Test placement — `tests/{path}/` directory choice with one-line precedent justification
- Driving Adapter coverage — every CLI/endpoint/hook in DESIGN mapped to at least one subprocess/HTTP/hook scenario
- Pre-requisites — DESIGN driving ports + DEVOPS environment matrix the scenarios depend on

### Tier-2 EXPANSION CATALOG — lazy, on-demand (per D10)

Rendered under `## Wave: DISTILL / [WHY|HOW] <Section>` only when requested via `--expand <id>` (DDD-2), the wave-end menu (`expansion_prompt = "ask"`), `mode = "full"` auto-expansion, or an ad-hoc user request mid-session.

| Expansion ID | Tier label | One-line description |
|---|---|---|
| `scenario-alternatives-considered` | [WHY] | Alternative scenario phrasings weighed and rejected (Gherkin variants, tag schemes) |
| `fixture-design-discussion` | [WHY] | Why these tmp_path/conftest fixtures, why these scopes, what they cannot model |
| `edge-case-enumeration` | [WHY] | Full edge-case taxonomy: empty/null/boundary/concurrency/timeout/permission |
| `error-path-rationale` | [WHY] | Why each `@error` scenario was chosen and what failure mode it surfaces |
| `tagging-cookbook` | [HOW] | Cookbook for tag application: `@property`, `@requires_external`, `@walking_skeleton` |
| `scaffold-authoring-recipes` | [HOW] | Per-language scaffold recipes (Python, TS, Go, Rust, Java) with marker conventions |
| `pbt-strategy-notes` | [WHY] | Property-based testing strategies for invariants surfaced by the feature |
| `expansion-catalog-rationale` | [WHY] | Why this set of expansions, why these defaults, why D10 enforces one-line descriptions |
| `domain-language-fact-to-step-table` | [HOW] | Soft gate: agent proposes fact→step-name pairs for user review before committing step-method names to code |
| `policy-bootstrap-template` | [HOW] | `docs/architecture/atdd-infrastructure-policy.md` bootstrap snippet emitted on first DISTILL in a project |
| `tier-b-state-machine-template` | [HOW] | State-machine PBT skeleton for Tier B in-memory journey testing (Mandate 10) |

## Density resolution (per D12)

Call `resolve_density(global_config)` from `scripts/shared/density_config.py` after reading `~/.nwave/global-config.json` (missing/malformed = empty dict). Returns `mode` (`"lean"` | `"full"`) + `expansion_prompt` (`"ask"` | `"always-skip"` | `"always-expand"` | `"smart"`) per the D12 cascade (resolver-internal, DDD-5 — do NOT replicate locally). Branch on `density.mode` for what to emit; branch on `density.expansion_prompt` at wave end for menu behaviour. Full cascade detail, branch semantics, ad-hoc override workflow: `nWave/skills/nw-density-resolution-contract/SKILL.md`.

## Telemetry (per D4 + DDD-6)

Every expansion choice emits a `DocumentationDensityEvent` (dataclass at `src/des/domain/telemetry/documentation_density_event.py`) via `event.to_audit_event()` → `JsonlAuditLogWriter().log_event(...)`. Schema fields per D4: `feature_id`, `wave`, `expansion_id`, `choice`, `timestamp`. For this wave the schema declares `"wave": "DISTILL"`. Use helper `scripts/shared/telemetry.py:write_density_event(...)` — do NOT write JSONL directly.

Wave-specific signal: DELIVER consuming a lean DISTILL feature-delta — downstream `--expand` for fixture-design or edge-case enumeration indicates the `[REF]` baseline plus the `.feature` file was insufficient for the crafter. Full emission rules: `nWave/skills/nw-density-resolution-contract/SKILL.md`.

## Feature-Delta Schema (US-01, US-02)

Provenance: `unified-feature-delta` US-01 (scaffold command) and US-02 (E1+E2 validator rules).

Every `feature-delta.md` is a Markdown document with `## Wave: <NAME>` sections. The canonical table format must be used in every `### [REF] Inherited commitments` block.

### Scaffold command

```
nwave-ai init-scaffold --feature <feature-name>
```

Creates `docs/feature/<feature-name>/feature-delta.md` with three pre-populated wave sections (DISCUSS, DESIGN, DISTILL), each containing a ready-to-fill commitments table. The scaffold passes the E1+E2 validator immediately.

### Canonical table format

Every `### [REF] Inherited commitments` block MUST have exactly four columns in this order:

```markdown
## Wave: DISCUSS

### [REF] Inherited commitments

| Origin | Commitment | DDD | Impact |
|--------|------------|-----|--------|
| n/a | <commitment text> | n/a | <impact text> |
```

Column semantics:
- **Origin**: wave and row reference of the upstream commitment (e.g., `DISCUSS#row1`) or `n/a` for root commitments
- **Commitment**: the specific commitment inherited or newly introduced in this wave
- **DDD**: Design Decision Document reference that authorizes any change (e.g., `DDD-3`) or `n/a` / `(none)` when not applicable
- **Impact**: substantive description (>=10 words or a consequence verb from the verb list) of the commitment's effect on the system

### Validator rules (E1+E2)

- **E1 (SectionPresent)**: every `## Wave: <NAME>` heading must match the canonical pattern. Known wave names: DISCOVER, DISCUSS, DESIGN, DEVOPS, DISTILL, DELIVER. Near-misses get a did-you-mean suggestion.
- **E2 (ColumnsPresent)**: every `### [REF] Inherited commitments` block must have a header row with the four required columns (Origin, Commitment, DDD, Impact) in any order, case-insensitive.

### Incremental authoring

Sections for waves not yet authored may be omitted entirely. The validator does not require all six wave sections to be present. An incremental feature-delta with only DISCUSS is valid. Missing future-wave sections are never flagged.

## Acceptance Criteria: Port-to-Port Principle

Every AC MUST name the driving port (entry point) through which the behavior is exercised. This enables port-to-port acceptance tests that make TBU (Tested But Unwired) defects structurally impossible.

Each AC includes:
1. **Observable outcome**: what the user/system sees
2. **Driving port**: the entry point that triggers the behavior (service, handler, endpoint, CLI command)

Without the driving port, a crafter can write correct code that is never wired into the system.

**Features**: "When user {action} via {driving_port}, {observable_outcome}"
**Bug fixes**: "When {trigger}, {modified_code_path} produces {correct_outcome} instead of {current_broken_behavior}"

## Translating Gherkin to Property-Based Tests (state-delta + Universe)

**Layer constraint** (per `nw-test-design-mandates` Mandate 9): this recipe applies ONLY to layers 1-2 (unit, in-memory acceptance with in-memory doubles). For subprocess / FS acceptance and integration tests (layers 3+), use example-only with `assert_state_delta` for the universe guard (Mandate 8) — sad paths stay enumerated, never PBT-generated (Mandate 11).

Per the Paradigm Mandate (PBT + state-delta is the default for unit + in-memory acceptance), DISTILL outputs `Property:` framings, not classic `Scenario:` examples, whenever the spec is quantifiable AND the test runs at layer 1-2. Single-example `Scenario:` is FALLBACK — use when the property cannot be expressed (one-off regression repro) OR when the scenario runs at layer 3+ (real adapter, subprocess, integration, WS).

### Recipe

1. **Take the `Scenario:`**: identify pre-condition, action, post-condition.
2. **Identify the Universe** (layer-specific — see `nw-tdd-methodology` Layered test discipline matrix):
   - Acceptance: use-case observable outcomes at driving port (events emitted, state on driven-port double, error class)
   - Walking Skeleton: user-visible end-to-end output (stdout, exit code, FS side-effects)
3. **Quantify the precondition**: from "a feature task exists" → `forall task in tasks where task.type in {feature, fix}` via Hypothesis `@given(strategy)`.
4. **Express the invariant**: instead of "the row's DELIVER cell shows `[in-progress] phase: GREEN`", state "for every task entered into DELIVER GREEN phase, the row's DELIVER cell renders status=in-progress with phase name visible".
5. **Frame as `Property:`** in the `.feature` file:
   ```gherkin
   @property @driving_port @us-XX
   Property: Operator sees in-progress phase for every task entered into a wave
     Given a workflow definition with named phases
     When for every task that emits PhaseEntered with phase=P, wave=W via the driving port
     Then the operator sees a row whose W cell renders status=in-progress with phase=P
     And the cell shape is invariant across {feature, fix, spike} task types
   ```
6. **Build the step-defs** with `@given` Hypothesis strategies + `assert_state_delta(before, after, universe, expected)` — universe entries are port-exposed names, never internal fields.

### Example (good vs bad Universe)

```python
# GOOD — port-exposed observable Universe
universe = {
    "events.PhaseEntered.emitted_count",
    "board.rows[task_id].cells[wave].status",
    "board.rows[task_id].cells[wave].phase",
}

# BAD — internal-field Universe (refactor breaks)
universe = {
    "BoardProjection._rows_cells_dict",
    "BoardProjection._rows_workflow_columns",
}
```

The bad Universe couples the test to private mutation details. Renaming `_rows_cells_dict` to `_cells_by_task` reds the test for an implementation rename — a refactoring-hostile signal.

### Walking Skeleton vs general acceptance

- 1-2 `@walking_skeleton @wiring_e2e` scenarios per slice, via subprocess + real I/O, prove wiring once.
- The rest of `Property:` scenarios run via driving-port direct invocation with in-memory doubles for driven ports (~10ms each). Fast feedback for the use-case logic.

### State-machine PBT trigger (Hebert ch.11)

State machine properties are for when the **model itself** is a state machine, not the system. If you can describe the SUT's behaviour by a state machine model with command/postcondition pairs, use stateful PBT. If not, use regular `FORALL` with property-based assertions.

This sharpens the earlier heuristic ("users perceive distinct states"): the trigger is about the *model shape* you can write, not the user's perception. A circuit-breaker policy is a state-machine model (ok / tripped / blocked + transitions); a sort function is not, even if its internal state has phases.

### Negative testing workflow (Hebert ch.6)

Hebert ch.6 — to surface under-specification, deliberately RELAX assumptions in the test (e.g., remove a precondition, widen the input domain). If the property still holds, you've over-specified. If it fails on inputs you'd expect to be valid, the spec is incomplete. Apply when an existing property never fails — the property may be vacuously true.

Workflow:
1. Start with a happy-path property suite (positive tests).
2. Pick one assumption the suite relies on (e.g. "prices are numeric", "items list is non-empty").
3. Write a new property that relaxes that assumption.
4. Run. A crash signals (a) a real bug, (b) an under-specified contract that should fail deliberately with a clear error, or (c) a place the spec needs tightening.
5. Repeat per assumption.

The negative-testing pattern is the property-level instrument for the "inputs validated at boundaries" mandate from the production-grade quality bar.

## Architecture of Reference (ports & adapters — project-level defaults)

Three classes of ports, each with a default test treatment. This table is PROJECT-LEVEL, decided once per project (typically during DESIGN of the first feature, or at framework adoption time). It is NOT renegotiated per feature. The agent applies these defaults; the per-feature decision is the MECHANISM (see Project Infrastructure Policy below), not the treatment.

| Port type | Examples | Default in test |
|---|---|---|
| **Driving** (entry point) | HTTP API, CLI, in-process call, hook | Real adapter (test host, CLI runner, app via DI container) |
| **Driven internal** (shared state) | Repository, read model, application cache | Real adapter via the mechanism declared in the project Infrastructure Policy |
| **Driven external / non-deterministic** | Clock, email, SMS, push, payment, LLM, third-party API | Fake/stub with output capture (so a `Then` can observe the side effect) |

This table replaces the earlier per-feature Walking Skeleton Strategy A/B/C/D choice. The decision is structural — port CLASS implies port TREATMENT — and the per-project Infrastructure Policy specializes the mechanism for each treatment.

If a port cannot be classified by the agent, ask the user with a soft prompt — do not improvise the classification.

## Project Infrastructure Policy

The Architecture of Reference fixes the **port class → test treatment** defaults. The Project Infrastructure Policy specializes those defaults with the **concrete mechanism** used in THIS codebase (Testcontainers vs dedicated env vs in-memory; which fake class). The decision is made **once per project, not per feature**.

### File location and structure

Lives at `docs/architecture/atdd-infrastructure-policy.md` (project-local). Three tables, one per port class, columns: `Port | Mechanism | Note`.

```markdown
# ATDD Infrastructure Policy

## Driving
| Port | Mechanism | Note |
|---|---|---|
| HTTP API | WebApplicationFactory<Program> | |
| CLI | subprocess from tmp_path | |

## Driven internal (real)
| Port | Mechanism | Note |
|---|---|---|
| IUserRepository (MongoDB) | Testcontainers.MongoDb, fresh db per test class | |

## Driven external / non-deterministic (fake)
| Port | Fake | Note |
|---|---|---|
| IClock | FakeClock | manual advance |
| IEmailSender | FakeEmailSender | in-memory capture |
```

The `Note` column is optional — use only when the mechanism needs a one-line clarification.

### Apply-if-exists / write-if-absent

1. **File exists** (default mode `--policy=inherit`): read the policy and apply recorded decisions. No port-by-port negotiation for ports already in the table.
2. **Port in scope is missing from the policy**: ask the user with a soft prompt (one row per missing port: `which mechanism for {port}?`), then **append the row to the policy** before generating scenarios. The policy grows by accretion.
3. **File is absent**: create an empty skeleton with the three section headers (use the `policy-bootstrap-template` expansion below), then treat every port in scope as missing (case 2).

The file is edited in place. No per-row versioning — git history is the audit trail.

### `--policy=fresh` flag

When the user passes `--policy=fresh`:
- Ignore the existing file for this run.
- Treat every port in scope as missing (soft prompt per port).
- On completion, rewrite the file from scratch with the newly agreed decisions.

Use `fresh` for major refactors (stack swap, test strategy overhaul). In all other cases, `inherit` is the default.

### Relationship to the Architecture of Reference

The Architecture of Reference answers: "what kind of treatment does this port class get?" (real vs fake).
The Project Policy answers: "and which concrete implementation does this project use for that treatment?" (Testcontainers vs dedicated env, which fake class).

The policy CANNOT override the port class defaults: a driven-internal port cannot become a fake through the policy (that requires an explicit waiver documented in `distill/wave-decisions.md`). The policy only records the **mechanism** for each default treatment.

## Wave-Decision Reconciliation HARD GATE (pre-scenario)

This is the ONLY hard gate before scenario writing. Execute it BEFORE any other DISTILL work:

1. Read all `wave-decisions.md` from prior waves: `docs/feature/{feature-id}/discuss/wave-decisions.md`, `docs/feature/{feature-id}/design/wave-decisions.md`, `docs/feature/{feature-id}/devops/wave-decisions.md`.
2. For each DISCUSS decision, check whether DESIGN or DEVOPS contradicts. Examples: DISCUSS "email notifications" but DESIGN "in-app only" = CONTRADICTION; DISCUSS "REST API" but DESIGN "gRPC" = CONTRADICTION; DISCUSS "single-tenant" but DEVOPS "multi-tenant" = CONTRADICTION.
3. If ANY contradiction → return `{CLARIFICATION_NEEDED: true, questions: [{file, contradicting-decisions, ask-which-stands}]}` and BLOCK.
4. If zero contradictions → log "Reconciliation passed — 0 contradictions" and proceed.

Do NOT silently pick one side of a contradiction. Do NOT write scenarios against ambiguous specifications. The cost of blocking is minutes; the cost of implementing the wrong behavior is hours.

## Graceful Degradation Matrix (warn vs block)

| Missing artifact | Action | Reason |
|---|---|---|
| `docs/feature/{id}/devops/` directory | **WARN**, use project default infra (from Project Infrastructure Policy or sensible defaults) | tests can proceed without env spec |
| `docs/feature/{id}/discuss/` directory | **WARN**, derive ACs from DESIGN, skip story-to-scenario traceability | story traceability lost, scenarios still coherent |
| `docs/feature/{id}/design/` directory | **BLOCK** — ask user to identify driving ports before writing any scenario | driving ports unknown, hexagonal boundary unverifiable |

Missing artifacts trigger warnings, not failures — EXCEPT when the missing artifact makes a design mandate unverifiable (DESIGN for hexagonal boundary). In that case, BLOCK.

## Two-Tier Acceptance Composition (Mandate 10 expanded for DISTILL)

Per `nw-test-design-mandates` Mandate 10, acceptance tests come in two tiers. DISTILL decides which tiers apply per feature.

**Default — Tier A only**: most features need only Tier A (Gojko-style, production composition root, 1-2 scenarios per journey).

**Add Tier B when both conditions hold**:
- Feature has a journey of ≥3 chained scenarios (Pillar 2 active — the `Given` of N reuses N-1's `Given + When`), AND
- Input space is domain-rich (emails, dates, payloads, free-text, IDs from a large set).

**Skip Tier B when**:
- Feature is config-shaped (single-shot installer config, schema validation, one-off CLI), OR
- Journey has 1-2 scenarios (Tier A example covers the space), OR
- The only observable is "did it crash" (no state mutation to model).

### File layout when both tiers are emitted

```
tests/{test-type-path}/{feature-id}/acceptance/
  {feature}.feature                       # Tier A — Gherkin scenarios (production DI)
  steps/
    conftest.py
    steps_{feature}.py                    # Tier A step-methods (production composition root)
  tier_b/
    test_{feature}_state_machine.py       # Tier B — RuleBasedStateMachine
    in_memory_composition.py              # InMemoryComposition (same interfaces, in-memory doubles)
```

### Shared vocabulary contract

Both tiers invoke the same step-method names (`Given_<precondition>`, `When_<action>`, `Then_<outcome>`). Tier A wires them through the production composition root; Tier B wires them through `InMemoryComposition`. The step-method NAMES are the contract — DRY across tiers.

When DISTILL emits Tier B, it MUST verify each `@rule`-decorated method invokes a step-method that already exists in the Tier A `steps_{feature}.py`. New step-method names introduced only in Tier B are a smell — they hint the journey was modeled differently for in-memory exploration than for production wiring.

## Wave: DISTILL / [HOW] Expansion Templates (lazy)

These templates are inline so the skill ships with the bootstrap snippets. They are emitted into the wave's `feature-delta.md` only when rendered as Tier-2 expansions (per the Density Resolution + Expansion Catalog above).

### Expansion `policy-bootstrap-template`

Emitted on first DISTILL in a project (file absent at `docs/architecture/atdd-infrastructure-policy.md`):

```markdown
# ATDD Infrastructure Policy

Per `nw-distill` § Project Infrastructure Policy. One file per project. Apply-if-exists; write-if-absent; rewrite with `--policy=fresh`. Git history is the audit trail.

## Driving
| Port | Mechanism | Note |
|---|---|---|

## Driven internal (real)
| Port | Mechanism | Note |
|---|---|---|

## Driven external / non-deterministic (fake)
| Port | Fake | Note |
|---|---|---|
```

### Expansion `tier-b-state-machine-template` (Python pilot)

Reference shape for `tests/{feature-id}/acceptance/tier_b/test_{feature}_state_machine.py`. Other host languages add their own template lazily.

```python
# tests/<path>/tier_b/test_<feature>_state_machine.py
import hypothesis.strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, precondition, invariant, initialize

from nwave_ai.state_delta import assert_state_delta, set_to, unchanged, appended_with

# Import shared step-method vocabulary (same as Tier A .feature steps)
from tests.<path>.acceptance.steps.steps_<feature> import (
    Given_<precondition>,
    When_<action>,
    Then_<outcome>,
    # ...
)

# In-memory composition root (Tier B difference from Tier A's production DI)
from tests.<path>.acceptance.tier_b.in_memory_composition import InMemoryComposition


class <Feature>Journey(RuleBasedStateMachine):
    @initialize()
    def setup(self):
        self.composition = InMemoryComposition()
        Given_<precondition>(self.composition)
        # ... initial state flags as instance attributes for @precondition use

    @rule(<input_strategies>)
    def <action>(self, ...):
        before = self.composition.capture_universe()
        When_<action>(self.composition, ...)  # SAME step-method as Tier A
        after = self.composition.capture_universe()
        assert_state_delta(
            before=before,
            after=after,
            universe={
                "<port_exposed_name_1>",
                "<port_exposed_name_2>",
            },
            expected={
                "<port_exposed_name_1>": set_to(<value>),
                "<port_exposed_name_2>": unchanged(),
            },
        )

    @invariant()
    def <invariant_name>(self):
        # universe-bound cross-rule invariant
        Then_<outcome>(self.composition)


Test<Feature>Journey = <Feature>Journey.TestCase
```

`InMemoryComposition.capture_universe()` returns a dict whose keys are the port-exposed observable names declared in the `universe` set. Tier A `steps_*.py` and Tier B `@rule` methods agree on these names — they are the shared contract.

### Expansion `domain-language-fact-to-step-table`

Soft-gate table proposed to the user BEFORE step-methods are generated. One row per Given/When/Then surface used in the planned scenarios. User approval is a quick exchange, not a formal blocking gate — but renaming an established step-method is expensive, so the agent surfaces the names early.

| Fact / observation | Step name (snake_case for Python; PascalCase per host language) |
|---|---|
| no user is registered | `Given_no_user_is_registered` |
| user signs up with a valid email | `When_the_user_signs_up_with_a_valid_email` |
| user receives magic link | `Then_the_user_should_have_received_a_magic_link` |
| order is rejected | `Then_the_order_is_rejected` |

The table is emitted into `feature-delta.md` under `## Wave: DISTILL / [HOW] Domain language` when the user requests this expansion (or when `density.mode = "full"`).

## Pre-DELIVER fail-for-the-right-reason gate

Before handing acceptance scenarios to DELIVER, run them once and verify each scenario fails for the **right reason** — the implementation is missing — not for setup error, fixture bug, import error, or test infrastructure problem.

### Procedure

1. Run the suite: `pytest tests/{feature}/acceptance/`. Capture failure output per scenario.
2. For each FAIL, classify the failure mode:
   - `MISSING_FUNCTIONALITY`: the assertion fires because behaviour is unimplemented (✅ correct RED)
   - `IMPORT_ERROR` / `FIXTURE_BROKEN` / `SETUP_FAILURE`: the test never reaches the assertion (❌ wrong RED — test bug)
   - `WRONG_ASSERTION` / `OBSERVABLE_NOT_AT_PORT`: assertion couples to internal struct (❌ wrong shape — fix Universe)
3. If any scenario is in category 2 or 3 → BLOCK handoff to DELIVER. Fix the test before crafter starts.

### Why this gate matters

A scenario that fails for the wrong reason gives a false signal at GREEN: the crafter "fixes" the import error and the test goes green, but the feature was never tested. We have observed this class on 2026-05-06 (`feedback_fixture_only_acceptance_hides_wiring_2026_05_06.md` + `feedback_layered_test_discipline_universe_per_layer_2026_05_06.md`): a fixture-shape acceptance scenario passes against a wired-but-broken bridge because it never exercises the seam.

The gate output is a one-line classification per failing scenario, written to `docs/feature/{feature-id}/distill/red-classification.md`. DELIVER reads this file at PREPARE phase to confirm RED is genuine.

## Prior Wave Reading

Before writing any scenario, read SSOT and feature delta artifacts.

**READING ENFORCEMENT**: You MUST read every file listed in steps 1-6 below using the Read tool before proceeding. After reading, output a confirmation checklist (`+ {file}` for each read, `- {file} (not found)` for missing). Do NOT skip files that exist.

1. **Read Journeys** — Read `docs/product/journeys/{name}.yaml`. Extract embedded Gherkin as starting scenarios, identify integration checkpoints and `failure_modes` per step. Gate: file read or marked missing.
2. **Read Architecture Brief** — Read `docs/product/architecture/brief.md`. Identify driving ports (from `## For Acceptance Designer` section) for `@driving_port` tagged scenarios. Gate: file read or marked missing.
3. **Read KPI Contracts** — Read `docs/product/kpi-contracts.yaml`. Identify behaviors needing `@kpi` tagged scenarios (soft gate — warn if missing, proceed). Gate: file read or marked missing.
4. **Read DISCUSS Artifacts** — Read `docs/feature/{feature-id}/discuss/user-stories.md` (scope boundary and embedded acceptance criteria), `story-map.md` (walking skeleton priority and release slicing), and `wave-decisions.md` (quick check for upstream changes). Gate: files read or marked missing.
5. **Read SPIKE Findings** (if spike was run) — Read `docs/feature/{feature-id}/spike/findings.md` and `docs/feature/{feature-id}/spike/wave-decisions.md`. Check what assumptions were validated, what failed, performance measurements, and the **promotion decision** (PROMOTE / DISCARD / PIVOT). Update acceptance criteria if spike findings contradict DISCUSS. Gate: files read if present, marked as not found if absent.
5b. **Read Walking Skeleton** (only if SPIKE promoted a walking skeleton) — Read the existing `tests/{test-type-path}/{feature-id}/acceptance/walking-skeleton.feature` and the `src/` modules it exercises. The walking skeleton is **already committed and green** — your job in DISTILL is to build **additional** scenarios and integration tests on top of it, not to rewrite it. Identify the driving adapter it uses, the e2e path it exercises, and the scenarios it does NOT yet cover (happy-path variants, error paths, adapter integration). Gate: walking-skeleton.feature read, scenario tagged `@walking_skeleton` confirmed green, or marked as not found.
6. **Read DEVOPS Artifacts** — Read `docs/feature/{feature-id}/devops/wave-decisions.md`. Check for infrastructure constraints affecting tests. Gate: file read or marked missing.
7. **Check Migration Gate** — If `docs/product/` does not exist but `docs/feature/` has existing features, STOP. Guide the user to `docs/guides/migrating-to-ssot-model/README.md`. If greenfield, prior waves should have bootstrapped `docs/product/` already. Gate: migration confirmed or greenfield confirmed.
8. **Reconcile Assumptions** — Check whether any acceptance test assumptions contradict prior wave decisions or SPIKE findings. Use `wave-decisions.md` and `spike/findings.md` files to detect upstream changes. Gate: zero contradictions or contradictions listed for user resolution.

DISTILL is the conjunction point — it reads all three SSOT dimensions plus the feature delta to translate prior wave knowledge into executable acceptance tests.

## Wave-Decision Reconciliation (Pre-Scenario Gate)

BEFORE writing any scenario, execute this reconciliation procedure:

1. **Read All Wave Decisions** — Read ALL wave-decisions.md files from prior waves: `docs/feature/{feature-id}/discuss/wave-decisions.md`, `docs/feature/{feature-id}/design/wave-decisions.md`, `docs/feature/{feature-id}/devops/wave-decisions.md`. Gate: all files read or marked missing.
2. **Check Each DISCUSS Decision** — For EACH decision in DISCUSS, check whether DESIGN or DEVOPS contradicts it. Examples: DISCUSS says "email notifications" but DESIGN says "in-app only" = CONTRADICTION; DISCUSS says "REST API" but DESIGN says "gRPC" = CONTRADICTION; DISCUSS says "single-tenant" but DEVOPS says "multi-tenant" = CONTRADICTION. Gate: all decisions checked.
3. **Handle Contradictions** — If ANY contradiction is found: (a) list ALL contradictions with exact file paths and decision text, (b) BLOCK scenario writing until the user resolves each contradiction, (c) return `{CLARIFICATION_NEEDED: true, questions: [{contradiction details}]}`. Gate: zero contradictions, or user resolution received.
4. **Log Reconciliation Result** — If zero contradictions: log "Reconciliation passed -- 0 contradictions" and proceed. Gate: log entry written.

Do NOT silently pick one side of a contradiction. Do NOT write scenarios against ambiguous specifications. The cost of blocking is minutes; the cost of implementing the wrong behavior is hours.

## Graceful Degradation for Missing Upstream Artifacts

**DEVOPS missing** (no `docs/feature/{feature-id}/devops/` directory):
1. **Log Warning** — Log: "DEVOPS artifacts missing -- using default environment matrix". Gate: warning logged.
2. **Apply Default Matrix** — Use default environment matrix: clean | with-pre-commit | with-stale-config. Gate: matrix applied.
3. **Proceed** — Continue with scenario writing. Do NOT block.

**DISCUSS missing** (no `docs/feature/{feature-id}/discuss/` directory):
1. **Log Warning** — Log: "DISCUSS artifacts missing -- using DESIGN only". Gate: warning logged.
2. **Derive from DESIGN** — Derive acceptance criteria from DESIGN architecture documents. Gate: criteria derived.
3. **Skip Traceability** — Skip story-to-scenario traceability -- no stories to trace. Gate: traceability skipped.
4. **Proceed** — Continue with scenario writing. Do NOT block.

**DESIGN missing** (no `docs/feature/{feature-id}/design/` directory):
1. **Log Warning** — Log: "DESIGN artifacts missing -- driving ports unknown". Gate: warning logged.
2. **BLOCK for Driving Ports** — Ask user to identify driving ports before writing any scenario. BLOCK until driving ports are identified -- without them, hexagonal boundary is unverifiable. Gate: user provides driving ports.

Missing artifacts trigger warnings, not failures -- EXCEPT when the missing artifact makes a design mandate unverifiable (DESIGN for hexagonal boundary). In that case, BLOCK.

## Document Update (Back-Propagation)

When DISTILL work reveals gaps or contradictions in prior waves:

1. **Document Findings** — Write findings in `docs/feature/{feature-id}/distill/upstream-issues.md`. Reference the original prior-wave document and describe the gap. Gate: file written.
2. **Flag Untestable Criteria** — If acceptance criteria from DISCUSS are untestable as written, note the specific criteria and explain why. Gate: all untestable criteria flagged.
3. **Resolve Before Writing** — Resolve contradictions with user before writing tests against ambiguous or contradictory requirements. Gate: user resolution received.

## Walking Skeleton Strategy (RETIRED — see Architecture of Reference + Project Infrastructure Policy)

**Retired**: the 4-way per-feature choice (Strategy A Full InMemory / B Real local + fake costly / C Real local / D Configurable) is REPLACED by two structural decisions made elsewhere:

1. **Architecture of Reference** (see section above) decides — once per project — what KIND of treatment each port class gets (real adapter for driving and driven-internal; fake for driven-external/non-deterministic).
2. **Project Infrastructure Policy** (see section above) decides — once per project — the CONCRETE MECHANISM for each port (Testcontainers vs in-memory vs Fake<X>).

Per-feature, DISTILL no longer negotiates strategies. It reads the policy (`--policy=inherit`, default), appends missing rows by asking the user, or rewrites from scratch (`--policy=fresh`).

What survives from the old section:

- **The walking-skeleton SCENARIO**: still required. One scenario per feature, tagged `@walking_skeleton @driving_port`, that closes the end-to-end loop through the production composition root. Litmus test: a non-technical stakeholder confirms "yes, that is what users need." This is the demo proof — independent of which mechanism each port uses.
- **Tagging convention** (unchanged):
  - `@real-io` — scenario uses real adapters (driving + driven-internal per Architecture of Reference)
  - `@in-memory` — scenario uses in-memory doubles (Tier B state-machine PBT, or in-memory acceptance per Mandate 10)
  - `@requires_external` — scenario needs an external system not in the project policy; skip if absent
  - Walking-skeleton scenarios MUST carry `@walking_skeleton @driving_port` and use the production composition root.

**Migration note**: existing features with a `wave-decisions.md` entry naming Strategy A/B/C/D continue to validate — the strategy named there is treated as historical record. NEW features express the same intent via the Architecture of Reference defaults + the project policy entry per port.

## Register Outcomes (per DISCUSS#D-5 grain)

Provenance: feature `outcomes-registry` — DISCUSS#D-2 (lean Tier-1 + Tier-2 default), D-5 (per-typed-contract grain), D-6 (gate-scoping: code-feature pipelines only).

**Trigger**: feature has a new typed contract surface — a rule module, CLI subcommand, public service operation, or system-wide invariant. Each such surface is one OUT-N row in the registry.

**Skip when**: the feature is methodology-only (skill propagation, prose changes, documentation updates, no new typed contract). Per D-6 gate-scoping, the registry tracks code-feature pipelines only; methodology features are explicitly OUT of scope.

**Procedure** — for every new contract surface introduced by the scenarios in this DISTILL session:

1. **Determine `kind`**: one of
   - `specification` — a rule (e.g. a guard, a validation predicate, a policy)
   - `operation` — a function/method exposed at a driving port (CLI subcommand, service method, endpoint)
   - `invariant` — a system-wide constraint that must always hold
2. **Run** `nwave-ai outcomes register --id OUT-N --kind {kind} --input-shape "..." --output-shape "..." --keywords "k1,k2,k3"`
3. **Handle exit codes**: exit `0` on successful registration; exit `2` on duplicate id (re-id the candidate and retry — typically because the OUT-N number is already taken).

The registry at `docs/product/outcomes/registry.yaml` becomes the SSOT for "what we promise the system does." Subsequent waves (DESIGN of later features) consult it to detect outcome collisions before introducing duplicate contracts.

Gate: every new typed contract introduced in the scenarios is registered with one OUT-N row, OR the feature is documented as methodology-only and registration is correctly skipped.

## Driving Adapter Verification (Mandatory — RCA fix P1, 2026-04-10)

If the DESIGN document specifies a CLI entry point, HTTP endpoint, or hook adapter:

1. **At least ONE walking skeleton scenario MUST invoke it via its protocol** — subprocess for CLI, HTTP request for API, hook JSON payload for hooks. Tag: `@driving_adapter @walking_skeleton`. Gate: scenario exists and exercises the user's actual invocation path.
2. **The scenario MUST verify**: exit code (or HTTP status), output format (stdout/response body), and basic argument handling. Gate: all three verified.
3. **Pipeline/service-level tests do NOT replace driving adapter tests.** A test that calls `generate_matrix()` directly proves the pipeline works but NOT that the CLI parses arguments, resolves PYTHONPATH, wires adapters, and produces correct exit codes. Both are needed.
4. **Scan DESIGN for entry points**: grep design docs for `python -m`, `cli`, `endpoint`, `hook adapter`. Each match needs at least one subprocess/HTTP/hook scenario. Gate: zero uncovered entry points.

This section exists because of a systematic pattern (RCA `docs/analysis/rca-user-port-gap.md`): acceptance tests entered from application services instead of user-facing CLIs, shipping features with working pipelines but broken entry points.

## Adapter Scenario Coverage (Mandate 6 Enforcement)

When designing adapter acceptance scenarios, EVERY driven adapter has at least one scenario with real I/O (or contract smoke for costly externals). This is not optional regardless of WS strategy. Tag adapter real-I/O scenarios with `@real-io @adapter-integration`.

1. **Inventory Adapters** — List all driven adapters in the feature. Gate: adapter list complete.
2. **Map Scenarios to Adapters** — For each adapter, identify existing scenarios that exercise it with real I/O. Gate: mapping complete.
3. **Produce Coverage Table** — Output the adapter coverage table before completing Phase 2:

```
| Adapter | @real-io scenario | Covered by |
|---------|-------------------|------------|
| YamlWorkflowLoader | YES | WS (real YAML from tmp_path) |
| FilesystemSkillReader | YES | WS (real skill files from tmp_path) |
| SubprocessGitVerifier | NO — MISSING | Add: "Git verifier reads real git log" |
| RuffLintRunner | NO — MISSING | Add: "Lint runner checks real ruff output" |
```

4. **Add Missing Scenarios** — Every row with "NO — MISSING" MUST have a scenario added. If the adapter is for a costly external (claude -p), a `@requires_external` contract smoke test is acceptable instead. Gate: zero "NO — MISSING" rows remain.

Cross-references: nw-tdd-methodology Mandate 5 (Walking Skeleton) and Mandate 6 (Real I/O), nw-quality-framework Dimension 9 (Walking Skeleton Integrity).

## Self-Review Checklist (Dimension 9 + Mandate 7)

Before handing off to reviewers, self-check each item:

- [ ] 1. WS strategy declared in wave-decisions.md
- [ ] 2. WS scenarios tagged correctly (@real-io / @in-memory per strategy)
- [ ] 3. Every driven adapter has at least one @real-io scenario
- [ ] 4. For InMemory doubles: documented what they CANNOT model
- [ ] 5. Container preference documented if applicable
- [ ] 6. **Mandate 7**: All production modules imported by tests have scaffold files
- [ ] 10. **Driving Adapter**: Every CLI/endpoint/hook in DESIGN has at least one WS scenario exercising it via subprocess/HTTP/hook protocol (not just calling the service function)
- [ ] 7. **Mandate 7**: All scaffolds include `__SCAFFOLD__` marker (or language equivalent)
- [ ] 8. **Mandate 7**: All scaffold methods raise assertion error (not NotImplementedError)
- [ ] 9. **Mandate 7**: Tests are RED (not BROKEN) when run against scaffolds
- [ ] 11. **F-001**: At least one `@real-io @adapter-integration` scenario per driven adapter (synthetic data misses format mismatches)
- [ ] 12. **F-002**: `capsys` used in `@when` step, NOT in `@then` step (capsys is step-scoped in pytest-bdd)
- [ ] 13. **F-005**: `@when` steps import ONLY from `des.application.*` or `des.domain.*` — NEVER from `des.adapters.driven.*`. Run `python scripts/hooks/check_driving_port_boundary.py` to verify.
- [ ] 14. **F-004**: Timing assertions in `.feature` files use budget >= 200ms (flaky under parallel load)
- [ ] 15. **F-003**: BDD imports after `sys.path` manipulation have `# noqa` markers (ruff strips them otherwise)

## Scenario Writing Guidelines

### Walking Skeleton First (or inherited from SPIKE)

If SPIKE ran and **PROMOTED** a walking skeleton, DISTILL inherits it: do NOT rewrite it, do NOT add duplicate scenarios, do NOT change its `@walking_skeleton` tag. Your job is to add the next layer of scenarios (additional happy paths, error paths, adapter integration) that build on the skeleton's established driving adapter and e2e path.

If SPIKE was skipped or did not promote, DISTILL creates the walking skeleton scenarios itself, before milestone features. Walking skeleton scenarios exercise the end-to-end path through driving adapters (real user-facing entry → real driven adapters → real user-visible output) with minimal business logic. Features only; optional for bugs.

Either way, there is exactly ONE walking skeleton scenario per feature marked `@walking_skeleton`, and it must be green before DISTILL hand-off.

### One-at-a-Time Strategy
Tag non-skeleton scenarios with @skip/@pending for one-at-a-time implementation. Each scenario maps to one TDD cycle in DELIVER. The crafter enables one scenario at a time.

### Business Language Purity
Feature files use business language only. No technical terms (API, database, endpoint, schema) in scenario names or Given/When/Then steps. Technical details live in step definitions, not feature files.

### Error Path Coverage
Target at least 40% error/edge case scenarios. Pure happy-path test suites miss the most common production failures. For every happy path, ask: "What happens when this input is invalid? When the dependency is unavailable? When the user cancels midway?"

### Environment-Aware Scenarios
When DEVOPS provides environment inventory, create at least one walking skeleton scenario per environment. Each environment has different preconditions (clean install vs. upgrade vs. stale config) that affect behavior.

## Mandate 7: RED-Ready Scaffolding

**Every acceptance test MUST be RED, not BROKEN, when first created.**

When DISTILL writes acceptance tests that import production modules not yet implemented, it MUST also create minimal stub files so that:
1. All imports succeed (no ImportError -- no BROKEN classification)
2. Method calls raise AssertionError (-- RED classification)
3. The Red Gate Snapshot classifies the test as RED, enabling the DELIVER TDD cycle

### What to scaffold

For each production module imported in step definitions:
1. **Create Module File** — Create the module file at the correct path (e.g., `src/app/plugin/installer.py`). Gate: file created.
2. **Add Scaffold Marker** — Include the scaffold marker (`__SCAFFOLD__ = True` or language equivalent) for machine detection. Gate: marker present.
3. **Define Signatures** — Define the class/function with the correct parameter signature. Gate: signatures match what step definitions expect.
4. **Raise Assertion Error** — Method bodies MUST raise an assertion error with the scaffold marker message. Gate: all methods raise AssertionError (not NotImplementedError).
5. **Verify RED Classification** — Confirm the test runner classifies tests as RED, not BROKEN. Gate: RED confirmed.

### Language-specific scaffolding

The principle is universal: **raise an exception classified as assertion failure (RED), not infrastructure error (BROKEN).**

**Python**:
```python
# src/app/plugin/installer.py
"""Plugin installer -- RED scaffold (created by DISTILL)."""
__SCAFFOLD__ = True

class PluginInstaller:
    def __init__(self, **kwargs):
        pass

    def install(self, ctx):
        raise AssertionError("Not yet implemented -- RED scaffold")
```

**Rust**:
```rust
// src/plugin/installer.rs
// SCAFFOLD: true
pub struct PluginInstaller;

impl PluginInstaller {
    pub fn install(&self) -> Result<(), Box<dyn std::error::Error>> {
        panic!("Not yet implemented -- RED scaffold")
    }
}
```

**Go**:
```go
// plugin/installer.go
// SCAFFOLD: true
package plugin

func Install() error {
    panic("not yet implemented -- RED scaffold")
}
```

**TypeScript/JavaScript**:
```typescript
// src/plugin/installer.ts
export const __SCAFFOLD__ = true;

export class PluginInstaller {
    install(): never {
        throw new Error("Not yet implemented -- RED scaffold");
    }
}
```

**Java**:
```java
// src/plugin/PluginInstaller.java
// SCAFFOLD: true
public class PluginInstaller {
    public void install() {
        throw new AssertionError("Not yet implemented -- RED scaffold");
    }
}
```

### Scaffold detection

DELIVER uses the scaffold marker to track progress:
- `grep -r "__SCAFFOLD__" src/` (Python, TypeScript)
- `grep -r "SCAFFOLD: true" src/` (Rust, Go, Java)

After all DELIVER steps complete, zero scaffold markers should remain.

### Why assertion errors (not NotImplementedError)

The Red Gate Snapshot (`src/des/application/red_gate_snapshot.py`) classifies failures by error type:
- `AssertionError` / `panic!` / `throw Error` -- **RED** (implementation missing, test correct)
- `NotImplementedError` -- **BROKEN** (infrastructure issue)
- `ImportError` / `ModuleNotFoundError` -- **BROKEN** (module missing)

Only RED tests proceed to the DELIVER TDD cycle. BROKEN tests block the upstream gate.

### Scaffolding lifecycle

1. **DISTILL** creates the scaffold (RED-ready stubs)
2. **Snapshot** classifies the test as RED
3. **DELIVER** replaces the scaffold with real implementation (GREEN)

The scaffold is never committed to production -- it exists only between DISTILL approval and DELIVER completion for each step.

## Final Wave Review Gate (Mandatory — covers DISCUSS+DESIGN+DEVOPS+DISTILL)

AFTER all DISTILL Tier-1 [REF] sections are appended to `feature-delta.md` and acceptance scenarios + scaffolds are written, dispatch FOUR reviewers in parallel against the full `feature-delta.md`. This is the consolidated mandatory review that replaces per-wave reviews (per-wave is now opt-in only — see DISCUSS/DESIGN/DEVOPS skills). All four reviewers see the entire 4-wave chain in one file, enabling cross-wave consistency checks that per-wave review misses.

1. **Dispatch four reviewers in parallel** (single message, multiple Agent tool uses, all on Haiku for cost efficiency):
   - `@nw-product-owner-reviewer` (Eclipse) — reviews DISCUSS sections (lines 1 to first `## Wave: DESIGN` heading)
   - `@nw-solution-architect-reviewer` (Architect) — reviews DESIGN sections (between `## Wave: DESIGN` and `## Wave: DEVOPS`)
   - `@nw-platform-architect-reviewer` (Forge) — reviews DEVOPS sections (between `## Wave: DEVOPS` and `## Wave: DISTILL`)
   - `@nw-acceptance-designer-reviewer` (Sentinel) — reviews DISTILL sections + executable `.feature` files + scaffolds
   Gate: all four reviewers dispatched concurrently.

2. **Each reviewer outputs YAML verdict** with: `approval_status` ∈ {approved, conditionally_approved, needs_revision, rejected}, `blocker_count`, `high_count`, `low_count`, `findings_list`. Gate: structured verdict received from each.

3. **Cross-wave consistency check** — if Eclipse APPROVES DISCUSS but Architect's findings reveal DISCUSS contradictions (e.g. story claims X, ADR assumes Y), surface as cross-wave blocker. Gate: contradictions flagged.

4. **Blocker handling** — for each NEEDS_REVISION verdict: dispatch fix to the corresponding wave's primary agent (Luna for DISCUSS, Morgan for DESIGN, platform-architect for DEVOPS, acceptance-designer for DISTILL). Re-run only the affected reviewer after fix. Gate: 2 revision cycles max per wave; escalate to user if not resolved.

5. **Block DELIVER handoff** — do not hand off to DELIVER until all four verdicts are APPROVED or CONDITIONALLY_APPROVED with documented action items in DELIVER scope. Gate: zero blockers, zero high (or accepted-with-conditions).

**Cost**: 4 Haiku reviewers in parallel ≈ $0.05-0.20 per feature. Trades small cost for late-feedback-blast-radius reduction (full chain visible).

**Per-wave review trigger override**: even with this final gate, a wave-skill may have triggered its own per-wave review (DoR ambiguity, contested ADR, novel deployment target, etc.). Per-wave reviewer outputs are PR-ephemeral, not committed; they inform the wave's primary agent in real time but don't substitute for this final gate.

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

### Polyglot bootstrap (apply-if-absent)

On first DISTILL invocation in a project, the agent:
1. Detects target language via the canonical project marker file (Phase 0 of nw-acceptance-designer).
2. Looks up the matrix row.
3. Checks for `tests/common/state_delta.<ext>` in the project.
4. If absent: applies the per-lang Tier-2 expansion template (lazy load) and commits.
5. If present: inherits (no re-bootstrap).

The template applies once per project. Subsequent DISTILL runs inherit the existing port.

## Outputs

**Single narrative file**: `docs/feature/{feature-id}/feature-delta.md` — scenario list with tags, WS strategy, adapter coverage table, scaffolds list, test placement, driving adapter coverage, pre-requisites all become `## Wave: DISTILL / [REF|WHY|HOW] <Section>` headings. The `.feature` file (below) remains the SSOT for executable scenarios; the wave-delta sections are pointers + structured summaries.

**Machine artifacts** (declared, parseable by downstream — the `.feature` files ARE the scenario SSOT, executable by pytest-bdd):
- `tests/{test-type-path}/{feature-id}/acceptance/walking-skeleton.feature`
- `tests/{test-type-path}/{feature-id}/acceptance/milestone-{N}-{description}.feature`
- `tests/{test-type-path}/{feature-id}/acceptance/integration-checkpoints.feature`
- `tests/{test-type-path}/{feature-id}/acceptance/steps/conftest.py` + `{domain}_steps.py`
- `src/{production-path}/{module}.py` — RED scaffold stubs (Mandate 7)

For bug fix regression tests: `tests/regression/{component-or-module}/bug-{ticket-or-description}.feature` + matching `tests/unit/{component-or-module}/test_{module}_bug_{ticket-or-description}.py`.

**SSOT updates** (per Recommendation 3 / back-propagation contract):
- `docs/product/kpi-contracts.yaml` — refine acceptance metrics: per-KPI scenario tag (`@kpi`) link, expected measurement window, soft-vs-hard gate classification. DISTILL inherits the contract from DEVOPS and tightens it as scenarios are written.

Legacy multi-file outputs (`walking-skeleton.md`, `wave-decisions.md`, `test-scenarios.md`, `acceptance-review.md` as separate files in `docs/feature/{id}/distill/`) are NOT produced — that content lives in `feature-delta.md`, and the executable `.feature` files are the scenario SSOT. Reviewer output is ephemeral (PR comments / retrospective, not committed). Validator: `scripts/validation/validate_feature_layout.py`.
