---
name: nw-distill
description: "Acceptance test creation methodology for the DISTILL wave. Domain knowledge for the acceptance designer agent: port-to-port principle, prior wave reading, wave-decision reconciliation, graceful degradation, and document back-propagation."
user-invocable: true
argument-hint: '[story-id] - Optional: --test-framework=[cucumber|specflow|pytest-bdd] --integration=[real-services|mocks]'
---

# DISTILL Methodology: Acceptance Test Creation

This skill provides the acceptance designer's methodology for creating acceptance tests. The orchestrator controls the overall flow (agent dispatch, review gate, handoff) -- this skill focuses on HOW to create good acceptance tests.

## Acceptance Criteria: Port-to-Port Principle

Every AC MUST name the driving port (entry point) through which the behavior is exercised. This enables port-to-port acceptance tests that make TBU (Tested But Unwired) defects structurally impossible.

Each AC includes:
1. **Observable outcome**: what the user/system sees
2. **Driving port**: the entry point that triggers the behavior (service, handler, endpoint, CLI command)

Without the driving port, a crafter can write correct code that is never wired into the system.

**Features**: "When user {action} via {driving_port}, {observable_outcome}"
**Bug fixes**: "When {trigger}, {modified_code_path} produces {correct_outcome} instead of {current_broken_behavior}"

## Prior Wave Reading

Before writing any scenario, read SSOT and feature delta artifacts.

**READING ENFORCEMENT**: You MUST read every file listed in steps 1-6 below using the Read tool before proceeding. After reading, output a confirmation checklist (`+ {file}` for each read, `- {file} (not found)` for missing). Do NOT skip files that exist.

1. **Read Journeys** — Read `docs/product/journeys/{name}.yaml`. Extract embedded Gherkin as starting scenarios, identify integration checkpoints and `failure_modes` per step. Gate: file read or marked missing.
2. **Read Architecture Brief** — Read `docs/product/architecture/brief.md`. Identify driving ports (from `## For Acceptance Designer` section) for `@driving_port` tagged scenarios. Gate: file read or marked missing.
3. **Read KPI Contracts** — Read `docs/product/kpi-contracts.yaml`. Identify behaviors needing `@kpi` tagged scenarios (soft gate — warn if missing, proceed). Gate: file read or marked missing.
4. **Read DISCUSS Artifacts** — Read `docs/feature/{feature-id}/discuss/user-stories.md` (scope boundary and embedded acceptance criteria), `story-map.md` (walking skeleton priority and release slicing), and `wave-decisions.md` (quick check for upstream changes). Gate: files read or marked missing.
5. **Read SPIKE Findings** (if spike was run) — Read `docs/feature/{feature-id}/spike/findings.md`. Check what assumptions were validated, what failed, performance measurements. Update acceptance criteria if spike findings contradict DISCUSS. Gate: file read if present, marked as not found if absent.
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

## Walking Skeleton Strategy Decision (INTERACTIVE)

Before writing walking skeleton scenarios, determine the WS adapter strategy. Auto-detect from the feature's component types, then confirm with the user.

**Decision Tree (auto-detect then user confirms):**

```
Feature is pure domain (no driven ports with I/O)?
  -> Strategy A (Full InMemory) -- WS uses InMemory doubles only

Feature has only local resources (filesystem, git, in-process subprocess)?
  -> Strategy C (Real local) -- WS uses real adapters for all local resources

Feature has costly external dependencies (paid APIs, LLM calls, rate-limited services)?
  -> Strategy B (Real local + fake costly) -- real for local, fake for expensive

Team needs different behavior in CI vs local development?
  -> Strategy D (Configurable) -- env var switches InMemory <-> Real
```

**Resource Classification:**

| Resource Type | WS Behavior | Adapter Integration Test |
|--------------|-------------|------------------------|
| Filesystem | real (tmp_path) | real (tmp_path) -- ALWAYS |
| Git repo | real (tmp_path + git init) | real -- ALWAYS |
| Local subprocess (pytest, ruff) | real | real -- ALWAYS |
| Costly subprocess (claude -p, LLM) | fake (mock) | contract smoke (@requires_external) |
| Paid external API | fake server | contract test with recorded fixtures |
| Database | real (SQLite/testcontainers) | real -- ALWAYS |
| Container services | per user preference | real if available |

**Container option:** Ask the user if they want containerized environments for WS and integration tests:
- No container (real adapters on host)
- Docker Compose (local services)
- Testcontainers (programmatic, lifecycle managed by test)

1. **Auto-Detect Strategy** — Classify feature components against the decision tree. Gate: strategy candidate identified.
2. **Confirm with User** — Present the auto-detected strategy and ask user to confirm or override. Gate: strategy confirmed.
3. **Record Decision** — Write the confirmed strategy in `distill/wave-decisions.md` as a numbered decision (e.g., DWD-XX: Walking Skeleton Strategy). Gate: decision recorded.
4. **Apply Strategy to Scenarios** — Tag WS scenarios per the confirmed strategy: Strategy A uses `@in-memory`, Strategy B/D uses `@real-io` for local and `@in-memory` for costly externals, Strategy C uses `@real-io` for ALL resources. Gate: scenarios tagged correctly.

**Tagging convention:**
- `@real-io` -- scenario uses real adapters
- `@in-memory` -- scenario uses InMemory doubles
- `@requires_external` -- scenario needs external system (skip if absent)
- Walking skeleton under B/C/D: MUST have `@walking_skeleton @real-io`

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

## Scenario Writing Guidelines

### Walking Skeleton First
Create user-centric walking skeleton scenarios before milestone features. Walking skeleton scenarios exercise the end-to-end path through driving ports with minimal business logic. Features only; optional for bugs.

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

## Expected Outputs

```
tests/{test-type-path}/{feature-id}/acceptance/
  walking-skeleton.feature
  milestone-{N}-{description}.feature
  integration-checkpoints.feature
  steps/
    conftest.py
    {domain}_steps.py

src/{production-path}/
  {module}.py               # RED scaffold stubs (Mandate 7)

docs/feature/{feature-id}/distill/
  test-scenarios.md
  walking-skeleton.md
  acceptance-review.md
  wave-decisions.md
```

Bug fix regression tests:
```
tests/regression/{component-or-module}/
  bug-{ticket-or-description}.feature
  steps/
    conftest.py
    {domain}_steps.py

tests/unit/{component-or-module}/
  test_{module}_bug_{ticket-or-description}.py
```
