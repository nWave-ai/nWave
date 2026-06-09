---
description: "Creates E2E acceptance tests in Given-When-Then format from requirements and architecture. Use when preparing executable specifications before implementation."
argument-hint: "[story-id] - Optional: --test-framework=[cucumber|specflow|pytest-bdd] --integration=[real-services|mocks] --accept-pilot-scope-extension"
---

# NW-DISTILL: Acceptance Test Creation and Business Validation

**Wave**: DISTILL (wave 5 of 6) | **Agent**: Quinn (nw-acceptance-designer)

## Overview

Orchestrate acceptance test creation from prior wave artifacts, then gate the result through parallel reviews before handoff to DELIVER. You (main Claude instance) are the orchestrator. You dispatch agents and enforce gates.

Behaviour is gated by `workflow.mode` read from `.nwave/config.yaml` (default `classic`; opt-in `atdd_pure` per ADR-027 / plan v3 §4). The cohort pre-assignment gate, AT-completeness gate, MAX-PBT mandate, and Mandate-12 step-reuse metric are MANDATORY under `atdd_pure` and ADVISORY under `classic`.

## Workflow Mode Dispatch (read first)

Read `.nwave/config.yaml` key `workflow.mode`. Allowed values: `classic` | `atdd_pure`. If missing, default `classic`.

| Mode | Cohort pre-assignment gate (Phase 0) | AT-completeness gate (Phase 2.5) | MAX-PBT mandate to Quinn | Mandate-12 step-reuse |
|---|---|---|---|---|
| `classic` | skipped | advisory (warn on score) | recommended | informational |
| `atdd_pure` | **MANDATORY** (BLOCKS on cohort ∉ {M}) | **MANDATORY** (re-author < 10/15) | **MANDATORY** | **target ≥4× informational** |

Mid-feature mode switch is forbidden (per ADR-027).

## REVIEW GATE SUMMARY (read this first)

After the acceptance designer produces scenarios, you MUST dispatch 4 parallel reviewers if scenario count exceeds 3 (Eclipse + Architect + Forge + Sentinel). Sentinel (`@nw-acceptance-designer-reviewer`) is the structural-correctness reviewer — it ALWAYS dispatches even on fast-path or under `rigor.reviewer_model: "skip"` (which only skips scale-sensitive cost-driven reviewers). This is the single most important orchestration step in DISTILL. The procedure is: dispatch designer -> count scenarios -> dispatch 4 reviewers in parallel -> AND-gate results -> handoff. Details in Phase 3 below.

## Phase 0: Cohort Pre-Assignment Gate (plan v3 §4.1.bis)

Runs BEFORE author dispatch. Mechanical, deterministic, cohort-keyed. Implementation in `scripts/cli/cohort_classifier.py` (core CLI per [[feedback_target_machine_independence_2026_05_15]] — NOT a pre-commit hook).

**Trigger**: `workflow.mode == atdd_pure`. If `classic`, skip Phase 0 entirely (no event emitted).

**Procedure**:

1. Count candidate ATs in `docs/feature/{feature-id}/feature-delta.md` `## Wave: DISTILL / [REF] Test Placement` section. Sources:
   - Existing `.feature` scenarios (grep `^\s*Scenario(?: Outline)?:` in referenced files)
   - Paired unit/property tests authored or earmarked for the feature
2. Mechanical cohort rule:
   - **S**: at_count ≤ 10
   - **M**: 11 ≤ at_count ≤ 30
   - **L**: 31 ≤ at_count ≤ 80
   - **XL**: at_count > 80
3. Gate decision:
   - cohort = `M` → emit `CohortAssigned(feature, cohort=M, at_count, scope_extension=False)` and proceed
   - cohort ∈ {S, L, XL} AND `--accept-pilot-scope-extension` flag absent → BLOCK with exit code 43 `COHORT_OUT_OF_PILOT_SCOPE`. Emit `CohortAssignmentRejected(feature, cohort, at_count)`. Halt sequencer.
   - cohort ∈ {S, L, XL} AND `--accept-pilot-scope-extension` present → emit `CohortAssigned(feature, cohort, at_count, scope_extension=True, operator=<USER>)` with override entry in execution-log; proceed.

**Dispatcher contract**: call CLI rather than embedding logic:

```bash
python scripts/cli/cohort_classifier.py \
    --feature {feature-id} \
    --workflow-mode atdd_pure \
    ${accept_pilot_scope_extension:+--accept-pilot-scope-extension} \
    --emit-event CohortAssigned
```

Exit code 0 → proceed. Exit code 43 → BLOCK + propagate `COHORT_OUT_OF_PILOT_SCOPE` to operator. Anti-pattern: silently re-labelling an S-cohort feature as M to expand the pilot pool — invalidates falsifier-gate per plan v3 §4.5 (forbidden).

## Phase 1: Decisions and Context

### Interactive Decision Points

#### Decision 1: Feature Scope
**Question**: What is the scope of this feature?
**Options**:
1. Core feature -- primary application functionality
2. Extension -- modular add-on or integration
3. Bug fix -- regression tests for a known defect

#### Decision 2: Test Framework
**Question**: Which test framework to use?
**Options**:
1. pytest-bdd -- Python BDD framework
2. Cucumber -- Ruby/JS BDD framework
3. SpecFlow -- .NET BDD framework
4. Custom -- user provides details

#### Decision 3: Integration Approach
**Question**: How should integration tests connect to services?
**Options**:
1. Real services -- test against actual running services
2. Test containers -- ephemeral containers for dependencies
3. Mocks for external only -- real internal, mocked external services

#### Decision 4: Infrastructure Testing
**Question**: Should acceptance tests cover infrastructure concerns?
**Options**:
1. Yes -- include CI/CD validation, deployment smoke tests
2. No -- functional acceptance tests only

### Prior Wave Consultation

DISTILL is the conjunction point — it reads all three SSOT dimensions plus the feature delta.

**SSOT (all three dimensions):**
1. **Journeys** (behavior): Read `docs/product/journeys/{name}.yaml` — extract embedded Gherkin as starting scenarios, identify integration checkpoints and failure_modes
2. **Architecture** (structure): Read `docs/product/architecture/brief.md` — identify driving ports (from `## For Acceptance Designer` section) for port-entry test scenarios
3. **KPI contracts** (observability): Read `docs/product/kpi-contracts.yaml` — identify which behaviors need `@kpi` tagged scenarios (soft gate — warn if missing, proceed)

**Feature delta:**
4. **DISCUSS**: Read from `docs/feature/{feature-id}/discuss/`:
   - `user-stories.md` (scope boundary — generate tests for THIS feature's stories only) | `story-map.md` | `wave-decisions.md`
5. **DEVOPS** (test environment): Read from `docs/feature/{feature-id}/devops/`:
   - `platform-architecture.md` | `ci-cd-pipeline.md` | `wave-decisions.md`

**Scope rule**: DISTILL generates tests for the behaviors described in `user-stories.md`, not for the entire SSOT. The SSOT provides context (which port to enter through, which KPI to verify) but the scope is bounded by the feature delta.

**READING ENFORCEMENT**: Read every file above using the Read tool. Output confirmation checklist (`+ {file}` for each read, `- {file} (not found)` for missing). Do NOT skip files that exist.

**Fallback**: If `docs/product/` does not exist, fall back to `docs/feature/{feature-id}/` for all inputs (old model).

### Graceful Degradation

- **KPI contracts missing**: Log warning: "KPI contracts missing — acceptance tests cover behavior only, not observability." Proceed without `@kpi` scenarios.
- **DEVOPS missing**: Log warning, use default environment matrix (clean, with-pre-commit, with-stale-config). Proceed.
- **DISCUSS missing**: Log warning, derive AC from architecture. Skip story-to-scenario traceability. Proceed.
- **Architecture SSOT missing**: BLOCK. Ask user to identify driving ports. Without them, hexagonal boundary is unverifiable.

### Rigor Profile

Read rigor config from `.nwave/des-config.json` (key: `rigor`). If absent, use standard defaults.
- `agent_model`: Pass as `model` to acceptance designer. If `"inherit"`, omit.
- `reviewer_model`: Pass as `model` to scale-sensitive cost-driven reviewers (Eclipse / Architect / Forge). If `"skip"`, skip those three only — **Sentinel (`@nw-acceptance-designer-reviewer`) ALWAYS dispatches** because it is the structural-correctness reviewer (Gherkin antipatterns, hexagonal boundary, contract drift); silent skip masks the bug class issue #52 was filed for.

### Wave-Decision Reconciliation

BEFORE dispatching the acceptance designer:
1. Read ALL `wave-decisions.md` files from prior waves
2. Check for contradictions between DISCUSS, DESIGN, and DEVOPS decisions
3. If ANY contradiction: list them all, BLOCK until user resolves each one
4. If zero contradictions: log "Reconciliation passed" and proceed

## Phase 2: Dispatch Acceptance Designer

@nw-acceptance-designer

Execute \*create-acceptance-tests for {feature-id}.

**Prompt must include:**
- All prior wave context read in Phase 1
- Decisions 1-4 configuration
- Instruction to load skills at `~/.claude/skills/nw-{skill-name}/SKILL.md` — explicitly include `nw-acceptance-designer` skills, `nw-bdd-methodology`, `nw-test-design-mandates`, and (under `atdd_pure`) `nw-at-completeness-check`
- **MAX-PBT + parametrize density mandate** (per [[feedback_ats_max_pbt_parametrize_density_2026_05_19]] + plan v3 §6.4):
  - Default = `parametrize`-collapse for shared-shape scenarios
  - PBT (`@given`) for unbounded / edge-distribution domains
  - Example-based ATs ONLY for unique invariants OR walking-skeleton (real-adapter wiring proof)
  - State-delta universe `strict=True` mandatory (per [[feedback_atdd_ssot_via_types_services_dsl_2026_05_18]] Mandate-12)
  - Density ≠ count. Limit AT count, maximise per-test behavioural coverage.
- **Mandate-12 step-reuse target**: domain types in `tests/{path}/acceptance/steps/domain_types.py`, logic in composition-root services (SSOT), step methods delegate. Target `step_reuse_ratio = total_step_invocations / unique_step_decorators ≥ 4×` (informational under both modes — not a hard block, per [[feedback_mandate12_refinement_2026_05_18]]).

**Configuration:**
- model: rigor.agent_model (omit if "inherit")
- workflow_mode: `{classic | atdd_pure}` (from Workflow Mode Dispatch above)
- test_type: {Decision 1} | test_framework: {Decision 2}
- integration_approach: {Decision 3} | infrastructure_testing: {Decision 4}
- interactive: moderate | output_format: gherkin

**After the agent returns**: Count the total scenarios produced. Store this number. You need it for Phase 2.5 and Phase 3.

## Phase 2.5: AT-Completeness Gate (plan v3 §6 + skill `nw-at-completeness-check`)

Runs AFTER Quinn returns initial AT set, BEFORE Phase 3 review gate. Mechanical 15-item checklist scored against the canonical 7-category taxonomy (C1-C7) defined in `nWave/skills/nw-at-completeness-check/SKILL.md`.

**Trigger**: `workflow.mode == atdd_pure` → MANDATORY (BLOCKS on score < 10). `workflow.mode == classic` → ADVISORY (emit warning on score < 13, do not block).

**Procedure**:

1. Load skill at `~/.claude/skills/nw-at-completeness-check/SKILL.md`. Apply 15-item checklist (C1a, C1b, C2a, C2b, C3, C4a, C4b, C5a, C5b, C6a, C6b, C6c, C7a, C7b, C7c) against produced AT set.
2. Compute score (count of checked items, 0-15) and step-reuse-ratio across produced step files.
3. Verdict thresholds:
   - **< 10/15 INCOMPLETE** → under `atdd_pure` re-dispatch Quinn with gap findings (max 2 cycles, then escalate). Under `classic` emit warning + proceed.
   - **10-12/15 ACCEPTABLE_WITH_DOCUMENTED_GAPS** → proceed; record gaps in `docs/feature/{feature-id}/distill/at-completeness-gap-log.md`.
   - **13+/15 COMPLETE** → proceed clean.
4. Emit `ATCompletenessVerdict(feature, score_15, threshold_band, gaps[])`.
5. Emit `StepReuseRatio(feature, ratio, target=4.0, met=<bool>)` (informational under both modes).

**Upstream-wave routing on `SPECIFICATION_AMBIGUITY`** (plan v3 §6.7): if reviewer flags a gap of kind `SPECIFICATION_AMBIGUITY` (categories C2 / C5 / C7), the gap does NOT route back to DISTILL — it routes back to the upstream wave that should own the missing artefact:

| Category | Upstream owner | Missing artefact |
|---|---|---|
| C2 State & Transition | DISCUSS | state machine in user-stories Elevator Pitch + DoD |
| C5 Mode-Flag / Decision-Table | DESIGN | component manifest (mode-flag inventory) |
| C7 Configuration / Environment / Interruption | DEVOPS | env matrix + interruption / concurrency contract |

DELIVER's Phase D routing logic handles the actual hand-back; DISTILL annotates the gap with `routes_to: <wave>` and surfaces in `wave-decisions.md` upstream-issues section.

## Phase 3: FINAL WAVE REVIEW GATE (mandatory orchestrator action)

This phase determines whether the acceptance tests are ready for DELIVER handoff. You MUST execute this phase. There is no path to Phase 5 (Handoff) that bypasses this gate.

Per `nw-distill/SKILL.md` "Final Wave Review Gate (Mandatory)", the gate dispatches FOUR reviewers in parallel: Eclipse (PO) + Architect (SA) + Forge (PA) + Sentinel (acceptance-designer-reviewer). Sentinel is the structural-correctness reviewer and ALWAYS dispatches — `rigor.reviewer_model: "skip"` only skips Eclipse/Architect/Forge.

### Step 3.1: Count scenarios

Count total scenarios across all `.feature` files produced by the acceptance designer. Store the count.

### Step 3.2: Fast-path (3 or fewer scenarios)

If total scenarios <= 3:
1. Skip Eclipse/Architect/Forge (the three scale-sensitive cost-driven reviewers). Run ONE Sentinel review pass — Sentinel always dispatches regardless of scenario count or rigor:
   ```
   Agent(
       subagent_type="nw-acceptance-designer-reviewer",
       prompt="""
       Review the acceptance tests for feature {feature-id}.

       TASK: Verify Gherkin structural correctness (no multi-When, no implementation
       leakage, no ambiguous outcomes), hexagonal boundary compliance at driving
       port, scaffold integrity (@skip markers present, fail-for-right-reason).

       Acceptance test files: tests/{test-type-path}/{feature-id}/acceptance/
       Feature delta: docs/feature/{feature-id}/feature-delta.md

       Load your skills from ~/.claude/skills/nw-{skill-name}/SKILL.md before starting.

       Return structured YAML with approval_status: approved | conditionally_approved | needs_revision | rejected
       """,
       description="Sentinel review: Gherkin structural correctness for {feature-id}"
   )
   ```
2. Run behavioral smoke test:
   ```bash
   pipenv run pytest tests/acceptance/{feature-id}/ -v --tb=short -x
   ```
   First scenario MUST fail for a business logic reason (not import error, not missing fixture).
3. Proceed to Phase 4.

### Step 3.3: Full review (more than 3 scenarios)

If total scenarios > 3, DISPATCH ALL FOUR REVIEWERS IN PARALLEL. Use the Agent tool four times in a single response — do not wait for one to finish before dispatching the next.

**Reviewer 1 — Product Owner (@nw-product-owner-reviewer)**:
```
Agent(
    subagent_type="nw-product-owner-reviewer",
    model=rigor.reviewer_model,  # omit if "inherit"
    prompt="""
    Review the acceptance tests for feature {feature-id}.

    TASK: Verify story-to-scenario traceability.
    For EACH user story in docs/feature/{feature-id}/discuss/user-stories.md,
    confirm at least one scenario in tests/acceptance/{feature-id}/ covers it.

    OUTPUT: mapping table [story_id -> scenario_name].
    Flag unmapped stories as BLOCKER.

    Acceptance test files: tests/{test-type-path}/{feature-id}/acceptance/
    Story files: docs/feature/{feature-id}/discuss/user-stories.md

    Load your skills from ~/.claude/skills/nw-{skill-name}/SKILL.md before starting.

    Return structured YAML with approval_status: approved | rejected_pending_revisions
    """,
    description="PO review: story-to-scenario traceability for {feature-id}"
)
```

**Reviewer 2 — Solution Architect (@nw-solution-architect-reviewer)**:
```
Agent(
    subagent_type="nw-solution-architect-reviewer",
    model=rigor.reviewer_model,  # omit if "inherit"
    prompt="""
    Review the acceptance tests for feature {feature-id}.

    TASK: Verify hexagonal boundary compliance.
    For EACH scenario in tests/{test-type-path}/{feature-id}/acceptance/,
    confirm Then steps assert observable outcomes through driving ports -- not internal state.
    Cross-reference with docs/feature/{feature-id}/design/architecture-design.md for port definitions.

    Flag scenarios that assert internal state, mock calls, or private fields as BLOCKER.

    Acceptance test files: tests/{test-type-path}/{feature-id}/acceptance/
    Architecture: docs/feature/{feature-id}/design/architecture-design.md

    Load your skills from ~/.claude/skills/nw-{skill-name}/SKILL.md before starting.

    Return structured YAML with approval_status: approved | rejected_pending_revisions
    """,
    description="SA review: hexagonal boundary compliance for {feature-id}"
)
```

**Reviewer 3 — Platform Architect (@nw-platform-architect-reviewer)**:
```
Agent(
    subagent_type="nw-platform-architect-reviewer",
    model=rigor.reviewer_model,  # omit if "inherit"
    prompt="""
    Review the acceptance tests for feature {feature-id}.

    TASK: Verify environment coverage.
    For EACH target environment in docs/feature/{feature-id}/devops/ inventory,
    confirm at least one walking skeleton scenario includes that environment's preconditions.
    If DEVOPS artifacts are missing, check against defaults: clean, with-pre-commit, with-stale-config.

    Flag uncovered environments as HIGH.

    Acceptance test files: tests/{test-type-path}/{feature-id}/acceptance/
    DEVOPS artifacts: docs/feature/{feature-id}/devops/

    Load your skills from ~/.claude/skills/nw-{skill-name}/SKILL.md before starting.

    Return structured YAML with approval_status: approved | rejected_pending_revisions
    """,
    description="PA review: environment coverage for {feature-id}"
)
```

**Reviewer 4 — Acceptance Designer Reviewer / Sentinel (@nw-acceptance-designer-reviewer)** — STRUCTURAL CORRECTNESS, ALWAYS DISPATCHES (ignore `rigor.reviewer_model: "skip"`):
```
Agent(
    subagent_type="nw-acceptance-designer-reviewer",
    # NOTE: do NOT pass rigor.reviewer_model here — Sentinel always runs
    prompt="""
    Review the acceptance tests for feature {feature-id}.

    TASK: Verify Gherkin structural correctness (no multi-When, no implementation
    leakage in step text, no ambiguous outcomes), hexagonal boundary compliance
    at driving port (Then steps assert through driving ports, not internal state),
    scaffold integrity (@skip markers correct, fail-for-right-reason gate ready),
    and that DISTILL sections of feature-delta.md match the .feature files.

    Acceptance test files: tests/{test-type-path}/{feature-id}/acceptance/
    Feature delta: docs/feature/{feature-id}/feature-delta.md

    Load your skills from ~/.claude/skills/nw-{skill-name}/SKILL.md before starting.

    Return structured YAML with approval_status: approved | conditionally_approved | needs_revision | rejected
    """,
    description="Sentinel review: Gherkin structural correctness for {feature-id}"
)
```

### Step 3.4: AND-Gate (all four must approve)

After all four reviewers return:
1. Check each reviewer's `approval_status`
2. ANY `rejected_pending_revisions` / `needs_revision` / `rejected` BLOCKS the DISTILL handoff
3. On rejection:
   - Collect specific findings from rejecting reviewer(s)
   - Re-dispatch `@nw-acceptance-designer` with reviewer findings attached
   - After revision, re-submit ONLY to the rejecting reviewer(s) — do not re-run approving reviewers
4. On ALL APPROVE (or CONDITIONALLY_APPROVED with documented action items): proceed to Phase 4

Max 2 revision cycles. If still rejected after 2 cycles, STOP and escalate to user.

## Phase 4: Produce Wave Decisions

Before completing DISTILL, produce `docs/feature/{feature-id}/distill/wave-decisions.md`:

```markdown
# DISTILL Decisions -- {feature-id}

## Key Decisions
- [D1] {decision}: {rationale} (see: {source-file})

## Test Coverage Summary
- Total scenarios: {N}
- Walking skeleton scenarios: {N}
- Milestone features: {list}
- Test framework: {framework}
- Integration approach: {approach}
- Workflow mode: {classic | atdd_pure}
- Cohort: {S | M | L | XL} (at_count={N}, scope_extension={bool})
- AT-completeness score: {N}/15 ({COMPLETE | ACCEPTABLE_WITH_DOCUMENTED_GAPS | INCOMPLETE})
- Step-reuse ratio: {ratio} (target 4.0×, met={bool})

## Review Gate Result
- Review type: {full-review (4 reviewers) | fast-path (Sentinel only) | cost-skip (Sentinel only, reviewer_model=skip)}
- Eclipse / PO reviewer: {approved | rejected -> revised -> approved | skipped (cost)}
- Architect / SA reviewer: {approved | rejected -> revised -> approved | skipped (cost)}
- Forge / PA reviewer: {approved | rejected -> revised -> approved | skipped (cost)}
- Sentinel / AD reviewer: {approved | rejected -> revised -> approved}  # ALWAYS dispatches

## Upstream Issues
- {any gaps found in prior wave artifacts}
- {AT-completeness gaps of kind SPECIFICATION_AMBIGUITY routed to: DISCUSS (C2) | DESIGN (C5) | DEVOPS (C7)}
```

## Phase 5: Handoff to DELIVER

Deliver these artifacts to the next wave:

```
tests/{test-type-path}/{feature-id}/acceptance/
  walking-skeleton.feature
  milestone-{N}-{description}.feature
  integration-checkpoints.feature
  steps/
    conftest.py
    {domain}_steps.py

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
```

**Handoff To**: nw-software-crafter (DELIVER wave)
**Deliverables**: Feature files | step definitions | test-scenarios.md | walking-skeleton.md

## Progress Tracking

The invoked agent MUST create a task list from its workflow phases at the start of execution using TaskCreate. Each phase becomes a task with the gate condition as completion criterion. Mark tasks in_progress when starting each phase and completed when the gate passes. This gives the user real-time visibility into progress.

## Success Criteria

- [ ] Workflow mode resolved from `.nwave/config.yaml` (classic | atdd_pure)
- [ ] Cohort pre-assignment gate executed (atdd_pure only) — exit 0 or operator override recorded
- [ ] All user stories have corresponding acceptance tests
- [ ] Step methods call real production services (no mocks at acceptance level)
- [ ] One-at-a-time implementation strategy established (@skip/@pending tags)
- [ ] Tests exercise driving ports, not internal components (hexagonal boundary)
- [ ] Walking skeleton created first with user-centric scenarios (features only; optional for bugs)
- [ ] Infrastructure test scenarios included (if Decision 4 = Yes)
- [ ] AT-completeness gate executed — score recorded; under atdd_pure, score ≥ 10/15 or re-author cycle completed
- [ ] MAX-PBT + parametrize density mandate honoured (PBT/parametrize default; example-based only for unique invariants or walking-skeleton)
- [ ] Mandate-12 step-reuse ratio computed and recorded (target ≥ 4× informational)
- [ ] Final Wave Review Gate passed (4 reviewers: Eclipse + Architect + Forge + Sentinel; fast-path runs Sentinel only; Sentinel always dispatches)
- [ ] Handoff package ready for nw-software-crafter (DELIVER wave)

## Examples

### Example 1: Core feature with full review
```
/nw-distill payment-webhook --test-framework=pytest-bdd --integration=real-services
```
Orchestrator reads prior waves -> dispatches Quinn -> Quinn produces 12 scenarios -> orchestrator dispatches Eclipse + Architect + Forge + Sentinel reviewers in parallel -> Architect rejects (internal state assertion in scenario 7) -> Quinn revises -> Architect re-reviews -> approved -> handoff to DELIVER.

### Example 2: Small bug fix with fast-path
```
/nw-distill fix-timeout-bug --test-framework=pytest-bdd
```
Orchestrator reads prior waves -> dispatches Quinn -> Quinn produces 2 regression scenarios -> fast-path (<=3) -> Sentinel review pass (Eclipse/Architect/Forge skipped on count) -> smoke test fails for business reason -> handoff to DELIVER.

### Example 3: Reviewer model skip (cost-driven)
`.nwave/des-config.json` has `rigor.reviewer_model: "skip"`. Orchestrator dispatches Quinn -> scenarios produced -> Eclipse/Architect/Forge skipped on cost -> **Sentinel STILL dispatches** (structural-correctness reviewer never skips; silent skip masks Gherkin antipatterns) -> handoff to DELIVER on Sentinel approval.

### Example 4: ATDD-pure M-cohort feature
`.nwave/config.yaml` has `workflow.mode: atdd_pure`. Orchestrator runs cohort classifier on `codex-empirical-e2e-support` (at_count=18) -> cohort=M -> emit `CohortAssigned` -> dispatch Quinn with MAX-PBT mandate -> Quinn produces 6 parametrize-collapsed + 4 PBT + 2 example-based scenarios -> AT-completeness gate scores 11/15 (ACCEPTABLE_WITH_DOCUMENTED_GAPS: C2b + C7c gaps) -> C7c routes upstream (DEVOPS owns interruption contract) -> Phase 3 full review gate -> handoff to DELIVER with gap log.

### Example 5: ATDD-pure S-cohort BLOCK
`workflow.mode: atdd_pure`, feature has 7 ATs. Cohort classifier returns S, no `--accept-pilot-scope-extension` flag. Gate emits `CohortAssignmentRejected(feature, cohort=S, at_count=7)`, halts with exit 43 `COHORT_OUT_OF_PILOT_SCOPE`. Operator either reruns with `--accept-pilot-scope-extension` (recorded override) or switches feature to `classic` mode.

DISTILL is the major synthesis point. DELIVER reads DISTILL output as its authoritative specification.
