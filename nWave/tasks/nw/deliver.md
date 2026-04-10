---
description: "Orchestrates the full DELIVER wave end-to-end (roadmap > execute-all > finalize). Use when all prior waves are complete and the feature is ready for implementation."
argument-hint: '[feature-description] - Example: "Implement user authentication with JWT"'
---

# NW-DELIVER: Complete DELIVER Wave Orchestrator

**Wave**: DELIVER (wave 6 of 6)|**Agent**: Main Instance (orchestrator)|**Command**: `/nw-deliver "{feature-description}"`

## Overview

Orchestrates complete DELIVER wave: feature description → production-ready code with mandatory quality gates. You (main Claude instance) coordinate by delegating to specialized agents via Task tool. Final wave (DISCOVER > DISCUSS > SPIKE > DESIGN > DEVOPS > DISTILL > DELIVER).

Sub-agents cannot use Skill tool or `/nw:*` commands. You MUST:
- Read the relevant command file and embed instructions in the Task prompt
- Remind the crafter to load its skills as needed for the task (skill files are at `~/.claude/skills/nw/{agent-name}/`)

## CRITICAL BOUNDARY RULES

1. **NEVER implement steps directly.** ALL implementation MUST be delegated to the selected crafter (@nw-software-crafter or @nw-functional-software-crafter per step 1.5) via Task tool with DES markers. You are ORCHESTRATOR — coordinate, not implement.
2. **NEVER write phase entries to execution-log.json.** Only the crafter subagent that performed TDD work may append entries.
3. **Extract step context from roadmap.json ONLY for Task prompt.** Grep roadmap for step_id ~50 lines context, extract (description|acceptance_criteria|files_to_modify), pass in DES template.

**DES monitoring is non-negotiable.** Circumventing DES — faking step IDs, omitting markers, or writing log entries manually — is a **violation that invalidates the delivery**. DES detects unmonitored steps and flags them; finalize **blocks** until every flagged step is re-executed through a properly instrumented Task. There is no workaround: unverified steps cannot pass integrity verification, and the delivery cannot be finalized. Without DES monitoring, nWave cannot **verify** TDD phase compliance. For non-deliver tasks (docs, research, one-off edits): `<!-- DES-ENFORCEMENT : exempt -->`.

## Rigor Profile Integration

Before dispatching any agent, read the rigor profile from `.nwave/des-config.json` (key: `rigor`). If absent, use standard defaults.

**How rigor affects deliver phases:**

| Setting | Effect |
|---------|--------|
| `agent_model` | Pass as `model` parameter to all Task tool invocations for crafter agents. If `"inherit"`, omit `model` parameter (Task tool inherits from session). |
| `reviewer_model` | Pass as `model` parameter to reviewer Task invocations. If `"skip"`, skip Phase 4 entirely. |
| `review_enabled` | If `false`, skip Phase 4 (Adversarial Review). |
| `double_review` | If `true`, run Phase 4 twice with separate review scopes. |
| `tdd_phases` | Pass to crafter in DES template. Replace `# TDD_PHASES` section with the configured phases. If only `[RED_UNIT, GREEN]`, omit PREPARE/RED_ACCEPTANCE/COMMIT instructions. |
| `refactor_pass` | If `false`, skip Phase 3 (Complete Refactoring). |
| `mutation_enabled` | If `false`, skip Phase 5 regardless of mutation strategy in CLAUDE.md. |

**Task invocation with rigor model:**
```python
Agent(
    subagent_type="{agent}",
    model=rigor_agent_model,  # omit this line entirely if "inherit"
    max_turns=45,
    prompt=...,
)
```

## Prior Wave Consultation

Before beginning DELIVER work, read targeted prior wave artifacts. DISTILL is the major synthesis point — its acceptance tests encode all prior wave decisions into executable specifications.

1. **DISCOVER** (skip): Synthesized into DISCUSS, then into DISTILL acceptance tests.
2. **DISCUSS** (skip): Synthesized into DISTILL acceptance tests. If needed during implementation, read specific files on demand.
3. **DESIGN** (structural context): Read from `docs/feature/{feature-id}/design/`:
   - `architecture-design.md` — component structure and C4 diagrams guide implementation
   - `component-boundaries.md` — dependency-inversion boundaries
   - `wave-decisions.md` — paradigm, tech stack, upstream changes
4. **DEVOPS** (skip): Infrastructure setup is independent of implementation. Read `wave-decisions.md` only if test environment issues arise.
5. **DISTILL** (primary input): Read all files in `docs/feature/{feature-id}/distill/` — test scenarios, walking skeleton, acceptance review are the authoritative specification for implementation.

**READING ENFORCEMENT**: You MUST read every file listed in Prior Wave Consultation above using the Read tool before proceeding. After reading, output a confirmation checklist (`✓ {file}` for each read, `⊘ {file} (not found)` for missing). Do NOT skip files that exist — skipping causes implementation disconnected from architecture and acceptance tests.

Additionally, check for `upstream-changes.md` and `upstream-issues.md` in DESIGN and DISTILL directories. If unresolved issues exist, flag them to the user before starting implementation. Do not implement against contradictory specifications.

**On-demand escalation**: If during implementation a crafter encounters ambiguity not resolved by DISTILL tests or DESIGN architecture, the orchestrator reads the specific prior wave file referenced in wave-decisions.md — never re-reads entire directories.

## Document Update (Back-Propagation)

When DELIVER implementation reveals gaps or contradictions in prior waves:
1. Document findings in `docs/feature/{feature-id}/deliver/upstream-issues.md`
2. Reference the original prior-wave document and describe the issue
3. If implementation requires deviating from architecture or requirements, document the deviation and rationale
4. Resolve with user before continuing past the affected step

## Orchestration Flow

```
INPUT: "{feature-description}"
  |
  0. Read rigor profile from .nwave/des-config.json (default: standard)
     Store: agent_model|reviewer_model|tdd_phases|review_enabled|double_review|mutation_enabled|refactor_pass
  |
  0.5. Prior Wave Consultation (see section above)
     Read DISTILL (all) + DESIGN (architecture + boundaries + wave-decisions)|flag contradictions|resolve before proceeding
     Summarize key design decisions into a reusable DESIGN_CONTEXT block for crafter dispatch (component structure, boundaries, tech choices, data models). This summary is injected into every crafter's DES template so sub-agents make implementation decisions aligned with the architecture.
  |
  1. Parse input|derive feature-id (kebab-case)|create docs/feature/{feature-id}/deliver/
     a. Create execution-log.json if missing via CLI:
        PYTHONPATH=$HOME/.claude/lib/python $(command -v python3 || command -v python) -m des.cli.init_log --project-dir docs/feature/{feature-id}/deliver --feature-id {feature-id}
        Do NOT create execution-log.json directly with Write — use the CLI only.
     b. Create deliver session marker: .nwave/des/deliver-session.json
  |
  1.5. Detect development paradigm
     a. Read project CLAUDE.md (project root, NOT ~/.claude/CLAUDE.md)
     b. Search "## Development Paradigm"
     c. Found → extract paradigm: "functional"/@nw-functional-software-crafter or "object-oriented"/@nw-software-crafter (default)
     d. Not found → ask user "OOP or Functional?"|offer to write to CLAUDE.md
     e. Store selected crafter for all Phase 2 dispatches
     f. Functional → property-based testing default|@property tags signal PBT|example-based = fallback
  |
  1.6. Detect mutation testing strategy
     a. Same CLAUDE.md|search "## Mutation Testing Strategy"
     b. Found → extract: per-feature|nightly-delta|pre-release|disabled
     c. Not found → default "per-feature"
     d. Log strategy for traceability
     Note: Strategy locks at deliver start. CLAUDE.md edits during delivery take effect next run.
  |
  2. Phase 1 — Roadmap Creation + Review
     a. Skip if docs/feature/{feature-id}/deliver/roadmap.json exists with validation.status == "approved"
        IMPORTANT: Only check the deliver/ subdirectory. If roadmap.json is found in design/ instead,
        MOVE it to deliver/ and log warning: "Roadmap relocated from design/ to deliver/ — was created in wrong wave."
     b. @nw-solution-architect creates roadmap.json (read ~/.claude/skills/nw-roadmap/SKILL.md)
        Step IDs: NN-NN format (01-01, 01-02, 02-01). 01-A or 1-1 = invalid.
        DISTILL LINKAGE: If docs/feature/{feature-id}/distill/ exists, the architect MUST populate
        test_file and scenario_name fields in each roadmap step from the distilled acceptance tests.
        Each step maps to one acceptance scenario (1 Step = 1 Scenario = 1 TDD Cycle).
     c. Automated quality gate (see below)
     d. @nw-software-crafter-reviewer reviews (read ~/.claude/skills/nw-review/SKILL.md)
     e. Retry once on rejection → stop for manual intervention
  |
  3. Phase 2 — Execute All Steps (ATOMIC DISPATCH)
     **INVARIANT: 1 Agent invocation = 1 roadmap step. No exceptions.**
     A single Agent MUST NEVER execute more than one step. Each step gets its own
     Agent invocation with exactly one DES-STEP-ID. Batching multiple steps into
     one Agent prompt is a VIOLATION — DES integrity verification will reject it.
     a. Extract steps from roadmap.json in dependency order (respect `depends_on` fields).
        PREREQUISITE: Phase 1 roadmap quality gate validates the dependency graph (no cycles,
        all `depends_on` references resolve to existing step IDs). Phase 2 assumes validation passed.
     b. Check execution-log.json for prior completion — skip steps with COMMIT/PASS
     c. **Dispatch loop** — for EACH pending step:
        c1. Extract step context from roadmap (grep step_id ~50 lines, extract fields)
        c2. Dispatch ONE Agent with ONE DES-STEP-ID using DES Prompt Template from execute.md
            Use crafter from step 1.5|@nw-functional-software-crafter → PBT default|@property tags signal PBT
            Include DES markers (DES-VALIDATION|DES-PROJECT-ID|DES-STEP-ID) + all mandatory sections
            OUTCOME_RECORDING: agents use DES CLI (PYTHONPATH=$HOME/.claude/lib/python $(command -v python3 || command -v python) -m des.cli.log_phase)|CLI bypass → SubagentStop hook corrects timestamps
        c3. WAIT for Agent to complete before dispatching next step
        c4. Verify COMMIT/PASS in execution-log.json for THIS step
        c5. Missing phase → RE-DISPATCH a NEW agent for the SAME step. NEVER write entries yourself.
        c6. Wiring smoke check: verify every new function defined in production files
            has at least one call site in production code (not just tests).
            Flag "function X defined but only called from tests" → re-dispatch crafter.
        c7. Acceptance test gate (two levels):
            - Step-scoped: run the acceptance test for THIS step (from `test_file` + `scenario_name` in roadmap).
              If it fails, fix before proceeding.
            - Feature-scoped regression: run ALL feature acceptance tests (tests/acceptance/{feature-id}/).
              If a test unrelated to this step fails, it means this step introduced a regression — fix before proceeding.
            Do NOT skip or defer failing tests at either level.
        c8. On failure → STOP. Do not proceed to next step.
     d. **Parallel dispatch** — BLOCKED until DES CLI implements file locking.
        The DES CLI (log_phase) uses read/modify/write on execution-log.json without serialization.
        Concurrent agents cause last-write-wins data loss. Sequential dispatch (c1-c8) is
        the ONLY safe mode. When file locking is implemented, parallel rules will be:
        d1. Steps with disjoint `depends_on` chains AND disjoint `files_to_modify` may run concurrently
        d2. Launch one Agent per step (never batch) using run_in_background=true
        d3. Wait for ALL agents in the group to complete
        d4. Run verification (c4-c7) for each step in the group
        d5. On ANY failure in the group → STOP. Do not proceed to next group.
        d6. Parallel group timeout: if ANY agent times out → wait for remaining agents to
            finish or timeout → check execution-log.json for partial progress → re-dispatch
            only timed-out steps individually. Do NOT re-run completed steps in the group.
     e. Timeout recovery: GREEN completed → resume (~5 turns)|GREEN partial → resume|Otherwise → restart higher max_turns
  |
  4. Phase 3 — Complete Refactoring (L1-L4) [SKIP if rigor.refactor_pass = false]
     a. Collect modified files: git diff --name-only {base-commit}..HEAD -- '*.py' | sort -u
        Split: PRODUCTION_FILES (src/) | TEST_FILES (tests/)
     b. /nw-refactor {files} --levels L1-L4 via {selected-crafter} with DES orchestrator markers:
        <!-- DES-VALIDATION : required -->|<!-- DES-PROJECT-ID : {feature-id} -->|<!-- DES-MODE : orchestrator -->
     c. All tests green after each module
  |
  5. Phase 4 — Adversarial Review [SKIP if rigor.review_enabled = false]
     a. If rigor.reviewer_model = "skip" → SKIP phase entirely
     b. /nw-review @nw-software-crafter-reviewer implementation "{execution-log-path}"
        Use model=rigor.reviewer_model for reviewer Task invocation
        Include DES orchestrator markers (same as Phase 3)
     c. If rigor.double_review = true → run review a second time with different scope focus
     d. Scope: ALL files modified during feature|includes Testing Theater 7-pattern detection
     e. One revision pass on rejection → proceed
  |
  6. Phase 5 — Mutation Testing [SKIP if rigor.mutation_enabled = false]
     If rigor.mutation_enabled = false → SKIP regardless of CLAUDE.md strategy
     Otherwise, apply CLAUDE.md strategy:
     per-feature → gate ≥80% kill rate (read ~/.claude/skills/nw-mutation-test/SKILL.md)
     nightly-delta → SKIP|log "handled by CI nightly pipeline"
     pre-release → SKIP|log "handled at release boundary"
     disabled → SKIP|log "disabled per project configuration"
  |
  7. Phase 6 — Deliver Integrity Verification
     a. PYTHONPATH=$HOME/.claude/lib/python $(command -v python3 || command -v python) -m des.cli.verify_deliver_integrity docs/feature/{feature-id}/deliver/
     b. Exit 0 → proceed|Exit 1 → STOP, read output
     c. No entries = not executed through DES|Partial = incomplete TDD
     d. Violations → re-execute via Task with DES markers|Only proceed after pass
  |
  8. Phase 7 — Finalize
     a. @nw-platform-architect archives to docs/evolution/ (read ~/.claude/skills/nw-finalize/SKILL.md)
     b. Commit + push|rm -f .nwave/des/deliver-session.json .nwave/des/des-task-active
  |
  9. Phase 8 — Retrospective (conditional)
     Skip if clean execution|@nw-troubleshooter 5 Whys on issues found
  |
  10. Phase 9 — Report Completion
      Display summary: phases|steps|reviews|artifacts|Return to DISCOVER for next iteration
```

## Orchestrator Responsibilities

Follow this flow directly. Do not delegate orchestration.

Per phase:
1. Read the relevant command file (paths listed above)
2. Extract instructions and embed them in the Task prompt
3. Include task boundary instructions to prevent workflow continuation
4. Verify output artifacts exist after each Task completes
5. Update .develop-progress.json for resume capability

## Task Invocation Pattern

DES markers required for step execution. Without markers → unmonitored. Full DES Prompt Template in `~/.claude/skills/nw-execute/SKILL.md`.

When dispatching steps via Agent tool, use the COMPLETE DES template from execute.md verbatim. Fill all `{placeholders}` from roadmap step context. The DES hook validates the prompt BEFORE the sub-agent starts — abbreviated prompts that delegate template reading to the sub-agent will be BLOCKED.

Copy the template from the code block in `~/.claude/skills/nw-execute/SKILL.md` (between ``` markers), fill placeholders, and pass as the Agent prompt. The template sections are defined in execute.md — do not hardcode the list here.

```python
Agent(
    subagent_type="{agent}",
    model=rigor_agent_model,  # omit if "inherit"
    prompt=f'''
<!-- DES-VALIDATION : required -->
<!-- DES-PROJECT-ID : {project_id} -->
<!-- DES-STEP-ID : {step_id} -->

# DES_METADATA
Step: {step_id}
Feature: {project_id}
Command: /nw-execute

# AGENT_IDENTITY
Agent: {agent}

# SKILL_LOADING
Before starting TDD phases, read your skill files for methodology guidance.
Skills path: ~/.claude/skills/nw/{agent-name}/
Always load at PREPARE: tdd-methodology.md, quality-framework.md
Load on-demand per phase as specified in your Skill Loading Strategy table.

# TASK_CONTEXT
{step context extracted from roadmap - name|description|acceptance_criteria|test_file|scenario_name|quality_gates|implementation_notes|dependencies|estimated_hours|deliverables|files_to_modify}

# DESIGN_CONTEXT
{Summarize key architectural decisions from design wave artifacts read at step 0.5.
Include: component structure, dependency-inversion boundaries, technology choices,
data models, and any design constraints relevant to this step.
Source files: architecture-design.md, component-boundaries.md, wave-decisions.md.
If no design artifacts exist, write "No design artifacts available — use project conventions."}

# TDD_PHASES
... (copy remaining sections from execute.md template verbatim)

# TIMEOUT_INSTRUCTION
Target: 30 turns max. If approaching limit, COMMIT current progress.
''',
    description="{phase description}"
)
```

## Roadmap Quality Gate (Automated, Zero Token Cost)

After roadmap creation, before reviewer:
1. AC coupling: flag AC referencing private methods (`_method()`)
2. Decomposition ratio: flag steps/files > 2.5
3. Identical patterns: flag 3+ steps with same AC structure (batch them)
4. Validation-only: flag steps with no files_to_modify
5. Step ID format: flag non-matching `^\d{2}-\d{2}$`
6. DISTILL linkage: if docs/feature/{feature-id}/distill/ exists, flag steps missing test_file/scenario_name

HIGH findings → return to architect for one revision.

## Skip and Resume

- Check `.develop-progress.json` on start for resume
- Skip if file exists with validation.status == "approved"
- Skip completed steps via execution-log.json COMMIT/PASS
- Max 2 retry per review rejection → stop for manual intervention

## Input

- `feature-description` (string, required, min 10 chars)
- feature-id: strip prefixes (implement|add|create)|remove stop words|kebab-case|max 5 words

## Output Artifacts

```
docs/feature/{feature-id}/deliver/
  roadmap.json|execution-log.json|.develop-progress.json
docs/evolution/
  {feature-id}-evolution.md
```

## Quality Gates

Roadmap review (1 review, max 2 attempts)|Per-step 5-phase TDD (PREPARE→RED_ACCEPTANCE→RED_UNIT→GREEN→COMMIT)|Paradigm-appropriate crafter|L1-L4 refactoring (Phase 3)|Adversarial review + Testing Theater detection (Phase 4)|Mutation ≥80% if per-feature (Phase 5)|Integrity verification (Phase 6)|All tests passing per phase

## Progress Tracking

The invoked agent MUST create a task list from its workflow phases at the start of execution using TaskCreate. Each phase becomes a task with the gate condition as completion criterion. Mark tasks in_progress when starting each phase and completed when the gate passes. This gives the user real-time visibility into progress.

## Success Criteria

- [ ] Roadmap created and approved
- [ ] All steps COMMIT/PASS (5-phase TDD)
- [ ] L1-L4 refactoring complete (Phase 3)
- [ ] Adversarial review passed (Phase 4)
- [ ] Mutation gate ≥80% or skipped per strategy (Phase 5)
- [ ] Integrity verification passed (Phase 6)
- [ ] Evolution archived (Phase 7)
- [ ] Retrospective or clean execution noted (Phase 8)
- [ ] Completion report (Phase 9)

## Examples

### 1: Fresh Feature
`/nw-deliver "Implement user authentication with JWT"` → roadmap → review → TDD all steps → mutation → finalize → report

### 2: Resume After Failure
Same command → loads .develop-progress.json → skips completed → resumes from failure

### 3: Single Step Alternative
For manual granular control, use individual commands:
```
/nw-roadmap @nw-solution-architect "goal"
/nw-execute {selected-crafter} "feature-id" "01-01"
/nw-finalize @nw-platform-architect "feature-id"
```

## Completion

DELIVER is final wave. After completion → DISCOVER for next feature or mark project complete.
