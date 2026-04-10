---
name: nw-deliver
description: "Orchestrates the full DELIVER wave end-to-end (roadmap > execute-all > finalize). Use when all prior waves are complete and the feature is ready for implementation."
user-invocable: true
argument-hint: '[feature-description] - Example: "Implement user authentication with JWT"'
---

# NW-DELIVER: Complete DELIVER Wave Orchestrator

**Wave**: DELIVER (wave 6 of 6)|**Agent**: Main Instance (orchestrator)|**Command**: `/nw-deliver "{feature-description}"`

## Overview

Orchestrates complete DELIVER wave: feature description → production-ready code with mandatory quality gates. You (main Claude instance) coordinate by delegating to specialized agents via Task tool. Final wave (DISCOVER > DISCUSS > SPIKE > DESIGN > DEVOPS > DISTILL > DELIVER).

Sub-agents cannot use Skill tool or `/nw-*` commands. You MUST:
- Read the relevant command file and embed instructions in the Task prompt
- Remind the crafter to load its skills as needed for the task (skill files are at `~/.claude/skills/nw-{skill-name}/SKILL.md`)

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
Task(
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
3. **DESIGN** (structural context): Read `docs/product/architecture/brief.md` — component boundaries, driving ports, C4 diagrams, and key architectural decisions. Also read `docs/feature/{feature-id}/design/wave-decisions.md` — paradigm, tech stack, upstream changes.
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

At the start of execution, create these tasks using TaskCreate and follow them in order:

0. **Read Rigor Profile** — Read `.nwave/des-config.json` key `rigor`. Store: `agent_model`, `reviewer_model`, `tdd_phases`, `review_enabled`, `double_review`, `mutation_enabled`, `refactor_pass`. Use standard defaults if absent. Gate: rigor profile loaded or defaults set.

0.5. **Prior Wave Consultation** — Read DISTILL (all files in `docs/feature/{feature-id}/distill/`) + DESIGN (`docs/product/architecture/brief.md`, `wave-decisions.md`). Flag contradictions, resolve before proceeding. Summarize key design decisions into a reusable DESIGN_CONTEXT block for crafter dispatch (component structure, boundaries, tech choices, data models). Gate: all required files read, confirmation checklist output, no unresolved contradictions.

1. **Setup** — Parse input, derive `feature-id` (kebab-case), create `docs/feature/{feature-id}/deliver/`.
   - a. Create `execution-log.json` via CLI: `PYTHONPATH=$HOME/.claude/lib/python $(command -v python3 || command -v python) -m des.cli.init_log --project-dir docs/feature/{feature-id}/deliver --feature-id {feature-id}`. Do NOT use Write tool directly.
   - b. Create deliver session marker: `.nwave/des/deliver-session.json`.
   - Gate: directory exists, `execution-log.json` created via CLI, session marker written.

1.5. **Detect Development Paradigm** — Read project `CLAUDE.md` (project root, NOT `~/.claude/CLAUDE.md`). Search "## Development Paradigm".
   - Found → extract paradigm: `"functional"` → `@nw-functional-software-crafter` or `"object-oriented"` → `@nw-software-crafter` (default).
   - Not found → ask user "OOP or Functional?", offer to write to `CLAUDE.md`.
   - Store selected crafter for all Phase 2 dispatches.
   - Functional → property-based testing default; `@property` tags signal PBT; example-based = fallback.
   - Gate: crafter selected and stored.

1.6. **Detect Mutation Testing Strategy** — Read same `CLAUDE.md`, search "## Mutation Testing Strategy".
   - Found → extract: `per-feature` | `nightly-delta` | `pre-release` | `disabled`.
   - Not found → default `"per-feature"`.
   - Log strategy for traceability. Note: strategy locks at deliver start; `CLAUDE.md` edits during delivery take effect next run.
   - Gate: strategy recorded.

2. **Phase 1 — Roadmap Creation + Review** — Gate: roadmap created, integrity verified, reviewer approved.
   - a. Skip if `docs/feature/{feature-id}/deliver/roadmap.json` exists with `validation.status == "approved"`. If found in `design/` instead, move to `deliver/` and log warning.
   - b. Dispatch `@nw-solution-architect` to create `roadmap.json` (load `~/.claude/skills/nw-roadmap/SKILL.md`). Step IDs MUST match `NN-NN` format (01-01, 01-02). If `distill/` exists, architect MUST populate `test_file` and `scenario_name` per step.
   - c. Run automated quality gate (see Roadmap Quality Gate section below).
   - c2. Run roadmap integrity verification (HARD GATE): `PYTHONPATH=$HOME/.claude/lib/python $(command -v python3 || command -v python) -m des.cli.verify_deliver_integrity docs/feature/{feature-id}/deliver/ --roadmap-only`. BLOCK on any format error; fix before dispatching any crafter.
   - d. Dispatch `@nw-acceptance-designer-reviewer` to review roadmap (load `~/.claude/skills/nw-review/SKILL.md`): verify every DISTILL scenario has a step, flag orphan scenarios as BLOCKER; flag steps covering 8+ scenarios as `@sizing-review-needed`; verify walking skeleton scenarios map to Phase 1 steps.
   - e. Retry once on rejection → stop for manual intervention.

3. **Phase 2 — Execute All Steps** — Gate: all steps reach COMMIT/PASS in `execution-log.json`.
   - a. Extract steps from `roadmap.json` in dependency order.
   - b. Check `execution-log.json` for prior completion (resume mode).
   - c. Dispatch selected crafter (from step 1.5) with full DES Prompt Template from `execute.md` (load `~/.claude/skills/nw-execute/SKILL.md`). Include DES markers (`DES-VALIDATION`, `DES-PROJECT-ID`, `DES-STEP-ID`) + all mandatory sections. Functional crafter → PBT default; `@property` tags signal PBT.
   - d. Verify COMMIT/PASS in `execution-log.json` per step.
   - e. Missing phase → RE-DISPATCH agent. NEVER write entries directly.
   - f. Stop on first failure.
   - g. Timeout recovery: GREEN completed → resume (~5 turns); GREEN partial → resume; otherwise → restart with higher `max_turns`.
   - h. Wiring smoke check: verify every new function defined in production files has at least one call site in production code (not just tests). Flag "function X defined but only called from tests" → re-dispatch crafter.
   - i. Acceptance test gate: after each step's COMMIT/PASS, run `tests/acceptance/{feature-id}/`. Fix failures before proceeding to next step. No deferral.

3.5. **Post-Merge Integration Gate (Hard Gate)** — AFTER all steps reach COMMIT/PASS, BEFORE Phase 3. Gate: full acceptance suite passes in all environments.
   - a. Run `pipenv run pytest tests/acceptance/{feature-id}/ -v --tb=short`.
   - b. Run acceptance tests against EVERY environment in `docs/feature/{feature-id}/devops/environments.yaml`. If missing, use defaults: `clean`, `with-pre-commit`, `with-stale-config`.
   - c. BLOCK if ANY test fails in ANY environment.
   - d. On failure: identify failing environment + test, re-dispatch crafter for new TDD cycle, re-run full gate after fix. If same test fails in 2+ environments after one fix attempt, STOP and report to user.
   - e. On success: record gate passage in `execution-log.json`: `{"gate": "post-merge-integration", "status": "PASS", "environments_tested": [...], "timestamp": "ISO-8601"}`.

4. **Phase 3 — Complete Refactoring (L1-L4)** — [SKIP if `rigor.refactor_pass = false`]. Gate: all tests green after each module refactored.
   - a. Collect modified files: `git diff --name-only {base-commit}..HEAD -- '*.py' | sort -u`. Split into PRODUCTION_FILES (`src/`) and TEST_FILES (`tests/`).
   - b. Run `/nw-refactor {files} --levels L1-L4` via selected crafter with DES orchestrator markers: `<!-- DES-VALIDATION : required -->`, `<!-- DES-PROJECT-ID : {feature-id} -->`, `<!-- DES-MODE : orchestrator -->`.

5. **Phase 4 — Adversarial Review** — [SKIP if `rigor.review_enabled = false` or `rigor.reviewer_model = "skip"`]. Gate: review passed or one revision complete.
   - a. Dispatch `/nw-review @nw-software-crafter-reviewer implementation "{execution-log-path}"` with `model=rigor.reviewer_model` and DES orchestrator markers.
   - b. If `rigor.double_review = true` → run review a second time with different scope focus.
   - c. Scope: ALL files modified during feature; includes Testing Theater 7-pattern detection.
   - d. One revision pass on rejection → proceed.

6. **Phase 5 — Mutation Testing** — [SKIP if `rigor.mutation_enabled = false`]. Gate: ≥80% kill rate or strategy skip logged.
   - `per-feature` → gate ≥80% kill rate (load `~/.claude/skills/nw-mutation-test/SKILL.md`).
   - `nightly-delta` → SKIP; log "handled by CI nightly pipeline".
   - `pre-release` → SKIP; log "handled at release boundary".
   - `disabled` → SKIP; log "disabled per project configuration".

7. **Phase 6 — Deliver Integrity Verification** — Gate: `verify_deliver_integrity` exits 0.
   - a. Run: `PYTHONPATH=$HOME/.claude/lib/python $(command -v python3 || command -v python) -m des.cli.verify_deliver_integrity docs/feature/{feature-id}/deliver/`.
   - b. Exit 0 → proceed. Exit 1 → STOP, read output.
   - c. No entries = not executed through DES. Partial = incomplete TDD.
   - d. Violations → re-execute via Task with DES markers. Proceed only after pass.

8. **Phase 7 — Finalize** — Gate: evolution archived, session markers removed, commit pushed.
   - a. Dispatch `@nw-platform-architect` to archive to `docs/evolution/` (load `~/.claude/skills/nw-finalize/SKILL.md`).
   - b. Commit + push. Run: `rm -f .nwave/des/deliver-session.json .nwave/des/des-task-active`.

9. **Phase 8 — Retrospective (conditional)** — Skip if clean execution. Gate: 5 Whys documented or clean-run noted.
   - On issues found → dispatch `@nw-troubleshooter` for 5 Whys analysis.

10. **Phase 9 — Report Completion** — Display summary: phases, steps, reviews, artifacts. Gate: report output, return to DISCOVER for next iteration.

## Orchestrator Responsibilities

Follow this flow directly. Do not delegate orchestration.

Per phase:
1. **Read command file** — Read the relevant command file (paths listed in each phase above).
2. **Embed instructions** — Extract instructions and embed them in the Task prompt.
3. **Add task boundary** — Include task boundary instructions to prevent workflow continuation.
4. **Verify artifacts** — Verify output artifacts exist after each Task completes.
5. **Update progress** — Update `.develop-progress.json` for resume capability.

## Task Invocation Pattern

DES markers required for step execution. Without markers → unmonitored. Full DES Prompt Template in `~/.claude/skills/nw-execute/SKILL.md`.

When dispatching steps via Agent tool, use the COMPLETE DES template from execute.md verbatim. Fill all `{placeholders}` from roadmap step context. The DES hook validates the prompt BEFORE the sub-agent starts — abbreviated prompts that delegate template reading to the sub-agent will be BLOCKED.

Copy the template from the code block in `~/.claude/skills/nw-execute/SKILL.md` (between ``` markers), fill placeholders, and pass as the Agent prompt. The template sections are defined in execute.md — do not hardcode the list here.

```python
Task(
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
Skills path: ~/.claude/skills/nw-{skill-name}/SKILL.md
Always load at PREPARE: tdd-methodology.md, quality-framework.md
Load on-demand per phase as specified in your Skill Loading Strategy table.

# TASK_CONTEXT
{step context extracted from roadmap - name|description|acceptance_criteria|test_file|scenario_name|quality_gates|implementation_notes|dependencies|estimated_hours|deliverables|files_to_modify}

# DESIGN_CONTEXT
{Summarize key architectural decisions from design wave artifacts read at step 0.5.
Include: component structure, dependency-inversion boundaries, technology choices,
data models, and any design constraints relevant to this step.
Source files: docs/product/architecture/brief.md, wave-decisions.md.
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

After roadmap creation, before reviewer, run these checks:

1. **AC coupling** — Flag AC referencing private methods (`_method()`). HIGH → return to architect.
2. **Decomposition ratio** — Flag steps/files > 2.5. HIGH → return to architect.
3. **Identical patterns** — Flag 3+ steps with same AC structure (batch them). HIGH → return to architect.
4. **Validation-only** — Flag steps with no `files_to_modify`. HIGH → return to architect.
5. **Step ID format** — Flag non-matching `^\d{2}-\d{2}$`. HIGH → return to architect.
6. **DISTILL linkage** — If `docs/feature/{feature-id}/distill/` exists, flag steps missing `test_file`/`scenario_name`. HIGH → return to architect.

## Skip and Resume

1. **Check progress** — Read `.develop-progress.json` on start for resume state.
2. **Skip approved roadmap** — Skip Phase 1 if `roadmap.json` exists with `validation.status == "approved"`.
3. **Skip completed steps** — Skip steps already showing COMMIT/PASS in `execution-log.json`.
4. **Cap retries** — Max 2 retries per review rejection → stop for manual intervention.

## Input

- `feature-description` (string, required, min 10 chars)
- `feature-id`: strip prefixes (implement|add|create), remove stop words, kebab-case, max 5 words

## Output Artifacts

```
docs/feature/{feature-id}/deliver/
  roadmap.json|execution-log.json|.develop-progress.json
docs/evolution/
  {feature-id}-evolution.md
```

## Quality Gates

Roadmap review (1 review, max 2 attempts)|Per-step 5-phase TDD (PREPARE→RED_ACCEPTANCE→RED_UNIT→GREEN→COMMIT)|Paradigm-appropriate crafter|L1-L4 refactoring (Phase 3)|Adversarial review + Testing Theater detection (Phase 4)|Mutation ≥80% if per-feature (Phase 5)|Integrity verification (Phase 6)|All tests passing per phase

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
Same command → loads `.develop-progress.json` → skips completed → resumes from failure

### 3: Single Step Alternative
For manual granular control, use individual commands:
```
/nw-roadmap @nw-solution-architect "goal"
/nw-execute {selected-crafter} "feature-id" "01-01"
/nw-finalize @nw-platform-architect "feature-id"
```

## Completion

DELIVER is final wave. After completion → DISCOVER for next feature or mark project complete.
