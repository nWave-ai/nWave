---
description: "Orchestrates the full DELIVER wave end-to-end (roadmap > execute-all > finalize). Use when all prior waves are complete and the feature is ready for implementation."
argument-hint: '[feature-description] - Example: "Implement user authentication with JWT"'
---

# NW-DELIVER: Complete DELIVER Wave Orchestrator

**Wave**: DELIVER (wave 6 of 6)|**Agent**: Main Instance (orchestrator)|**Command**: `/nw:deliver "{feature-description}"`

## Overview

Orchestrates complete DELIVER wave: feature description → production-ready code with mandatory quality gates. You (main Claude instance) coordinate by delegating to specialized agents via Task tool. Final wave (DISCOVER > DISCUSS > DESIGN > DEVOPS > DISTILL > DELIVER).

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
Task(
    subagent_type="{agent}",
    model=rigor_agent_model,  # omit this line entirely if "inherit"
    max_turns=45,
    prompt=...,
)
```

## Orchestration Flow

```
INPUT: "{feature-description}"
  |
  0. Read rigor profile from .nwave/des-config.json (default: standard)
     Store: agent_model|reviewer_model|tdd_phases|review_enabled|double_review|mutation_enabled|refactor_pass
  |
  1. Parse input|derive feature-id (kebab-case)|create docs/feature/{feature-id}/deliver/
     a. Create execution-log.json if missing: schema_version "2.0"|feature_id|events: []
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
     a. Skip if roadmap.json exists with validation.status == "approved"
     b. @nw-solution-architect creates roadmap.json (read ~/.claude/commands/nw/roadmap.md)
        Step IDs: NN-NN format (01-01, 01-02, 02-01). 01-A or 1-1 = invalid.
     c. Automated quality gate (see below)
     d. @nw-software-crafter-reviewer reviews (read ~/.claude/commands/nw/review.md)
     e. Retry once on rejection → stop for manual intervention
  |
  3. Phase 2 — Execute All Steps
     a. Extract steps from roadmap.json in dependency order
     b. Check execution-log.json for prior completion (resume)
     c. {selected-crafter} executes 5-phase TDD cycle (read ~/.claude/commands/nw/execute.md)
        Use crafter from step 1.5|@nw-functional-software-crafter → PBT default|@property tags signal PBT
        IMPORTANT: Use DES Prompt Template from execute.md|Include DES markers (DES-VALIDATION|DES-PROJECT-ID|DES-STEP-ID) + 9 mandatory sections
        OUTCOME_RECORDING: agents use DES CLI (python -m des.cli.log_phase)|CLI bypass → SubagentStop hook corrects timestamps
     d. Verify COMMIT/PASS in execution-log.json per step
     e. Missing phase → RE-DISPATCH agent. NEVER write entries yourself.
     f. Stop on first failure
     g. Timeout recovery: GREEN completed → resume (~5 turns)|GREEN partial → resume|Otherwise → restart higher max_turns
  |
  4. Phase 3 — Complete Refactoring (L1-L4) [SKIP if rigor.refactor_pass = false]
     a. Collect modified files: git diff --name-only {base-commit}..HEAD -- '*.py' | sort -u
        Split: PRODUCTION_FILES (src/) | TEST_FILES (tests/)
     b. /nw:refactor {files} --levels L1-L4 via {selected-crafter} with DES orchestrator markers:
        <!-- DES-VALIDATION : required -->|<!-- DES-PROJECT-ID : {feature-id} -->|<!-- DES-MODE : orchestrator -->
     c. All tests green after each module
  |
  5. Phase 4 — Adversarial Review [SKIP if rigor.review_enabled = false]
     a. If rigor.reviewer_model = "skip" → SKIP phase entirely
     b. /nw:review @nw-software-crafter-reviewer implementation "{execution-log-path}"
        Use model=rigor.reviewer_model for reviewer Task invocation
        Include DES orchestrator markers (same as Phase 3)
     c. If rigor.double_review = true → run review a second time with different scope focus
     d. Scope: ALL files modified during feature|includes Testing Theater 7-pattern detection
     e. One revision pass on rejection → proceed
  |
  6. Phase 5 — Mutation Testing [SKIP if rigor.mutation_enabled = false]
     If rigor.mutation_enabled = false → SKIP regardless of CLAUDE.md strategy
     Otherwise, apply CLAUDE.md strategy:
     per-feature → gate ≥80% kill rate (read ~/.claude/commands/nw/mutation-test.md)
     nightly-delta → SKIP|log "handled by CI nightly pipeline"
     pre-release → SKIP|log "handled at release boundary"
     disabled → SKIP|log "disabled per project configuration"
  |
  7. Phase 6 — Deliver Integrity Verification
     a. PYTHONPATH=$HOME/.claude/lib/python python -m des.cli.verify_deliver_integrity docs/feature/{feature-id}/deliver/
     b. Exit 0 → proceed|Exit 1 → STOP, read output
     c. No entries = not executed through DES|Partial = incomplete TDD
     d. Violations → re-execute via Task with DES markers|Only proceed after pass
  |
  8. Phase 7 — Finalize
     a. @nw-platform-architect archives to docs/evolution/ (read ~/.claude/commands/nw/finalize.md)
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

DES markers required for step execution. Without markers → unmonitored. Full DES Prompt Template (9 sections) in `~/.claude/commands/nw/execute.md`.

```python
Task(
    subagent_type="{agent}",
    model=rigor_agent_model,  # omit if "inherit"
    max_turns=45,  # 25 hotfix|45 standard|65 complex
    prompt=f'''
<!-- DES-VALIDATION : required -->
<!-- DES-PROJECT-ID : {project_id} -->
<!-- DES-STEP-ID : {step_id} -->
(step_id: NN-NN format. DES hooks require this.)

TASK BOUNDARY: {task_description}
Return control to orchestrator after completion.

Read full DES Prompt Template from ~/.claude/commands/nw/execute.md.
Fill: step_id={step_id}|project_id={project_id}|agent={agent}|task_context={instructions}

SKILL_LOADING: Read your skill files at ~/.claude/skills/nw/{agent-name}/.
At PREPARE phase, always load: tdd-methodology.md, quality-framework.md.
Then follow your Skill Loading Strategy table for phase-specific skills.
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
`/nw:deliver "Implement user authentication with JWT"` → roadmap → review → TDD all steps → mutation → finalize → report

### 2: Resume After Failure
Same command → loads .develop-progress.json → skips completed → resumes from failure

### 3: Single Step Alternative
For manual granular control, use individual commands:
```
/nw:roadmap @nw-solution-architect "goal"
/nw:execute {selected-crafter} "feature-id" "01-01"
/nw:finalize @nw-platform-architect "feature-id"
```

## Completion

DELIVER is final wave. After completion → DISCOVER for next feature or mark project complete.
