---
name: nw-tdd-methodology-walking-skeleton
description: Building and validating a walking skeleton - the WS protocol scoped to the FEATURE (one skeleton, extended by every slice), Mandate 5 adapter port-class real-I/O treatment (resource table), and Mandate 6 adapter-integration real-I/O requirement
user-invocable: false
disable-model-invocation: true
---

# Walking Skeleton — Protocol, Adapter Strategy, Real-I/O Mandates

**Trigger**: building or validating a walking skeleton — classifying WS adapter port-class real-I/O treatment, extending the feature's skeleton with a new slice, or deciding adapter-integration real-I/O coverage.

## Walking Skeleton Protocol

Exactly ONE walking skeleton per FEATURE, not one per slice (see `nw-product-value-slicing`). When `is_walking_skeleton: true` in roadmap — i.e. this is the FIRST slice of a new feature:
- Write exactly ONE E2E/acceptance test proving end-to-end wiring with REAL adapters
- Implement thinnest possible slice — hardcoded values, minimal branching
- Unit tests are written ONLY if needed to decompose complex GREEN implementation
- Do NOT add error handling, edge cases, or validation beyond what the AT requires
- No code without a test that requires it — the AT drives ALL implementation

The WS is an acceptance test on steroids: it proves wiring AND drives implementation of adapters, domain logic, and application services. If the WS AT requires 5 functions to pass, those 5 functions are justified. Subsequent steps that find "already implemented, AT goes GREEN" confirm the WS was well-designed.

Integration tests for adapters (real filesystem, real subprocess) are naturally created during WS — the WS REQUIRES real adapters, which drives their implementation and testing.

## E2E Test Management

**Oracle path**: DISTILL compiles the executable oracle for the current value slice. Do not author speculative future scenarios and do not use `@skip` as a plan. Implement the smallest causally complete RED scope to GREEN, then extend only when the next observable requires it.

**Test-pyramid default: at most ONE `@walking_skeleton` subprocess-E2E per FEATURE, established by its first slice.** Every subsequent slice EXTENDS that same skeleton with the new observable value — it never authors a second skeleton. It proves installed wiring once; every other scenario drives in-process/in-memory through the driving port. The evidence is the union of that skeleton, the Examiner exercising charter observables through the real surface, and final whole-slice verification. An additional independently-needed subprocess E2E is a SCENARIO, not another walking skeleton — it requires an observable integration boundary the feature's skeleton cannot exercise, and does not replace or duplicate it.


## Mandate 5: Walking Skeleton Real-I/O Treatment

The DISTILL acceptance designer classifies each port per the Architecture of Reference (`nw-distill-port-treatment-policy`): driving ports run in-process; driven-internal ports default to an in-memory fake with a config-switched prod-like leg; driven-external/costly ports default to a fake with output capture. The ONE `@walking_skeleton` scenario is the exception that proves wiring: inside it, driven-internal/local-resource ports run real I/O per the table below. Every other scenario keeps the Architecture of Reference default. Treatment follows port CLASS — it is structural, not a per-feature choice, and is auto-detected with user confirmation, not a question to the user.

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

Inside the `@walking_skeleton` scenario, real adapters serve driven-internal/local resources by default. InMemory there is ONLY for costly external resources that have a separate contract test.

### Determinism Contract

Real-adapter WS tests accept non-determinism as a trade-off for environmental realism. InMemory acceptance tests remain the fast deterministic inner loop. The WS is the slow truth-checking outer loop. Both are necessary. If WS fails, triage: logic failure (fix code) or environment failure (retry, investigate infra).

### Infrastructure-Failure Handling

If a driven-internal/local-resource port's real adapter fails for infrastructure reasons (not code bugs), fall back to a fake for that step ONLY when the fake can still observe the declared law/failure; otherwise refuse the fake and escalate the infrastructure gap — never silently swap in a fake that cannot observe the promised failure.

## Mandate 6: Adapter Integration Tests Are Real I/O

Every driven adapter has at least ONE integration test with real I/O. This is not optional regardless of WS strategy.

A source-blind reviewer judges only its supplied packet: a driven-adapter real-I/O test absent from that packet is reported as an evidence gap routed to its owner — neither an in-packet rejection nor a satisfied mandate.

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
- Walking skeleton: `@walking_skeleton` + `@real-io` (when a driven port requires real I/O)

## Adapter Integration Slice RED-Phase Semantics

The RED-phase `fail-for-right-reason` gate (Mandate-7) carries different semantics for an acceptance slice vs an adapter-integration slice. Conflating the two produces false-positive convergence — an AT that "fails" because the adapter contract is not yet authored is NOT the same shape of failure as an AT that "fails" because the feature behavior is missing.

Reference: design spike v2 `docs/analysis/adapter-integration-slice-design-2026-05-27.md` §6 surface #10.

### Two RED-phase modes — distinguished by the failure source

- **acceptance RED**: the AT fails because the feature behavior is not implemented. The driving port returns the unimplemented-default response; the assertion against expected end-state fails. Implementing the feature inside the hexagon (domain + application + new wiring through existing adapters) turns the AT GREEN. Fail-for-right-reason token: `AssertionError` against expected feature outcome.
- **adapter-integration RED**: the AT fails because a declared adapter obligation is not satisfied against the still-stub-or-partial adapter. The SUT is the adapter boundary; the assertion is about a contract property such as error taxonomy, concurrency, atomicity, idempotency, recovery, observability, fail mode, resource safety or driving-port purity. Implementing that obligation turns the AT GREEN. It must fail for the declared property, not for fixture or environment setup.

The distinguishing token between the two modes is **property-matrix row contract**: an adapter-integration AT names the property it exercises (one row of the 10-property matrix), and the assertion shape verifies that the adapter satisfies the named row. The acceptance AT does NOT cite a property-matrix row — it asserts feature outcome through the driving port.

### Mandate-7 applies in both modes

The fail-for-right-reason gate is mandatory in both modes. The RED failure must be a semantic `AssertionError` (or expected-exception-not-raised), NOT a collection error, NOT an import error, NOT a skip marker, NOT a timeout — the verification owner runs the native check that observes this, per the active role boundary, not necessarily the crafter itself. The mode distinction does NOT relax the gate; it only changes the assertion subject (feature behavior vs property-matrix row contract).

### Practical implication for DELIVER crafters

When durable design authority declares an adapter-integration obligation, the crafter's GREEN target is that boundary property, not unrelated product behavior. A crafter who changes the product workflow to satisfy an adapter oracle crosses the declared boundary; return the mismatch to its owning design or DISTILL authority.
