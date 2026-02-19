---
description: "Orchestrates the full DELIVER wave end-to-end (roadmap > execute-all > finalize). Use when all prior waves are complete and the feature is ready for implementation."
disable-model-invocation: true
argument-hint: '[feature-description] - Example: "Implement user authentication with JWT"'
---

# NW-DELIVER: Complete DELIVER Wave Orchestrator

**Wave**: DELIVER (wave 6 of 6)
**Agent**: Main Instance (self -- orchestrator)
**Command**: `/nw:deliver "{feature-description}"`

## Overview

Orchestrates the complete DELIVER wave: from feature description to production-ready code with mandatory quality gates. You (the main Claude instance) coordinate by delegating to specialized agents via the Task tool. Final wave in nWave (DISCOVER > DISCUSS > DESIGN > DEVOP > DISTILL > DELIVER).

Sub-agents cannot use the Skill tool or execute `/nw:*` commands. Read the relevant command file yourself, extract instructions, and embed them in the Task prompt.

## CRITICAL BOUNDARY RULES

1. **NEVER implement roadmap steps directly.** ALL step implementation MUST be delegated to @nw-software-crafter via the Task tool with DES markers. You are the ORCHESTRATOR — you coordinate, you do not implement.

2. **NEVER write phase entries to execution-log.yaml.** Only the software-crafter subagent that performed the TDD work may append phase entries. If you write entries yourself, finalize will detect the violation and block.

3. **Extract step context from roadmap.yaml ONLY for the Task prompt.** Grep the roadmap for the step_id with ~50 lines context, extract fields (description, acceptance_criteria, files_to_modify), and pass them in the DES template. The crafter receives the full step context through the prompt.

**Circumventing DES validation for deliver steps is fraud.** Without DES monitoring, nWave cannot guarantee code quality — the entire TDD cycle, audit trail, and integrity verification exist to protect the codebase. If your Task prompt is genuinely NOT a deliver step (e.g., documentation, research, one-off edits), use the escape hatch: `<!-- DES-ENFORCEMENT : exempt -->`. That is the correct way. Faking step IDs, omitting markers, or writing execution-log entries manually to bypass validation is never acceptable.

The finalize verification gate checks that every completed step has valid DES-format execution-log entries (5 TDD phases with timestamps). Steps implemented without DES monitoring will be flagged, and finalize will block until they are re-executed properly via Task.

## Orchestration Flow

```
INPUT: "{feature-description}"
  |
  1. Parse input, derive project-id (kebab-case), create docs/feature/{project-id}/
     a. Create execution-log.yaml if it doesn't exist:
        ```yaml
        schema_version: "2.0"
        project_id: "{project-id}"
        events: []
        ```
     b. This ensures the execute command can append from step 1
     c. Create deliver session marker for Write/Edit guard:
        ```bash
        mkdir -p .nwave/des && echo '{"project_id":"{project-id}","started_at":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > .nwave/des/deliver-session.json
        ```
  |
  2. Phase 1 — Roadmap Creation + Review
     a. Skip if roadmap.yaml exists with validation.status == "approved"
     b. @nw-solution-architect creates roadmap.yaml (read ~/.claude/commands/nw/roadmap.md)
        Step IDs MUST use NN-NN format (two digits, dash, two digits).
        First pair = phase number, second pair = step number within phase.
        Example: 01-01, 01-02, 02-01. Formats like 01-A or 1-1 are invalid.
     c. Automated quality gate (see below)
     d. @nw-software-crafter-reviewer reviews roadmap (read ~/.claude/commands/nw/review.md)
     e. Retry once on rejection, then stop for manual intervention
  |
  3. Phase 2 — Execute All Steps
     a. Extract steps from roadmap.yaml in dependency order
     b. For each step, check execution-log.yaml for prior completion (resume)
     c. @nw-software-crafter executes 5-phase TDD cycle (read ~/.claude/commands/nw/execute.md)
        IMPORTANT: Use the DES Prompt Template from execute.md. Include all 4 DES
        markers (DES-VALIDATION, DES-PROJECT-ID, DES-STEP-ID) and all 9 mandatory
        sections in the Task prompt. Without these, DES validation is bypassed.
        NOTE: The OUTCOME_RECORDING section instructs agents to use the DES CLI
        (`python -m des.cli.log_phase`) for recording phases with real timestamps.
        If an agent bypasses the CLI and edits execution-log.yaml directly,
        the SubagentStop hook corrects fabricated timestamps automatically.
     d. Verify COMMIT/PASS in execution-log.yaml after each step
     e. If a phase is missing: RE-DISPATCH the agent to execute it.
        NEVER write execution-log entries yourself — only the agent
        that actually performed the work may write to the log.
     f. Stop on first failure
     g. On timeout: check last completed phase in execution-log.yaml.
        If GREEN completed → resume (just COMMIT remains, ~5 turns).
        If stuck in GREEN with partial progress → resume.
        Otherwise → restart with higher max_turns (resume costs ~50% more tokens/call).
  |
  4. Phase 3 — Complete Refactoring (L1-L4, code + tests)
     a. Orchestrator collects modified files:
        git diff --name-only {base-commit}..HEAD -- '*.py' | sort -u
        Split into PRODUCTION_FILES (src/) and TEST_FILES (tests/)
     b. Orchestrator invokes /nw:refactor to apply systematic refactoring:
        /nw:refactor {production-files} {test-files} --levels L1-L4
        The refactor command dispatches @nw-software-crafter via Task tool
        with DES orchestrator markers to enable source file writes:
        ```
        <!-- DES-VALIDATION : required -->
        <!-- DES-PROJECT-ID : {project-id} -->
        <!-- DES-MODE : orchestrator -->
        ```
        Include the explicit file list and refactoring levels (L1-L4).
        All tests must stay green after each module.
  |
  5. Phase 4 — Adversarial Review
     a. Orchestrator invokes /nw:review for the full feature implementation:
        /nw:review @nw-software-crafter-reviewer implementation "{execution-log-path}"
        The review command dispatches @nw-software-crafter-reviewer (Haiku)
        to critique code quality, test quality, and Testing Theater detection.
        Include DES orchestrator markers in the Task prompt to enable source file writes:
        ```
        <!-- DES-VALIDATION : required -->
        <!-- DES-PROJECT-ID : {project-id} -->
        <!-- DES-MODE : orchestrator -->
        ```
     b. Review scope: ALL files modified during the feature (not just refactoring).
        Includes Testing Theater 7-pattern detection as enforcement layer.
     c. One revision pass on rejection (orchestrator re-dispatches refactoring
        on flagged files with same orchestrator markers), then proceed.
  |
  6. Phase 5 — Mutation Testing
     a. Mutation testing gate >= 80% kill rate (read ~/.claude/commands/nw/mutation-test.md)
     b. Must pass before proceeding
  |
  7. Phase 6 — Deliver Integrity Verification
     a. Run via Bash tool:
        PYTHONPATH=$HOME/.claude/lib/python python -m des.cli.verify_deliver_integrity docs/feature/{project-id}/
     b. Exit 0 = all steps verified, proceed to finalize
     c. Exit 1 = violations found, STOP. Read output for details.
     d. Steps with NO entries were NOT executed through DES
     e. Steps with partial entries have incomplete TDD cycles
     f. If violations exist, re-execute affected steps via Task with DES markers
     g. Only proceed after verification passes
  |
  8. Phase 7 — Finalize + Cleanup
     a. @nw-platform-architect archives to docs/evolution/ (read ~/.claude/commands/nw/finalize.md)
     b. Commit evolution document, push when ready
     c. Remove deliver session marker: `rm -f .nwave/des/deliver-session.json .nwave/des/des-task-active`
  |
  9. Phase 8 — Retrospective (conditional)
     a. Skip if clean execution (no failures, no retries, no warnings)
     b. @nw-troubleshooter performs 5 Whys analysis on issues found
  |
  10. Phase 9 — Report Completion
      a. Display summary: phases, steps, reviews, artifacts
      b. Workflow complete. Return to DISCOVER for next feature iteration.
```

## Orchestrator Responsibilities

You follow this flow directly. Do not delegate orchestration to another agent.

For each phase:
1. Read the relevant command file (paths listed above)
2. Extract instructions and embed them in the Task prompt
3. Include task boundary instructions to prevent workflow continuation
4. Verify output artifacts exist after each Task completes
5. Update .develop-progress.json for resume capability

## Task Invocation Pattern

All Task prompts for step execution include DES markers for validation. Without these markers, the DES hooks cannot validate the task and it passes through unmonitored. The DES hooks REQUIRE step-id patterns with DES markers -- they do not block them. Proper NN-NN format is what enables DES tracking.

The full DES Prompt Template (all 9 mandatory sections) is defined in `~/.claude/commands/nw/execute.md`. Read that file and embed all 9 sections (DES_METADATA, AGENT_IDENTITY, TASK_CONTEXT, TDD_PHASES, QUALITY_GATES, OUTCOME_RECORDING, RECORDING_INTEGRITY, BOUNDARY_RULES, TIMEOUT_INSTRUCTION) in each Task prompt.

```python
Task(
    subagent_type="{agent}",
    max_turns=45,  # Adjust per step: 25 hotfix, 45 standard, 65 complex (see execute.md)
    prompt=f'''
<!-- DES-VALIDATION : required -->
<!-- DES-PROJECT-ID : {project_id} -->
<!-- DES-STEP-ID : {step_id} -->
(step_id must match NN-NN format, e.g. 01-01, 02-03. DES hooks require this pattern.)

TASK BOUNDARY: {task_description}
Return control to orchestrator after completion.

Read the full DES Prompt Template from ~/.claude/commands/nw/execute.md and embed all 9 mandatory sections below.
Fill placeholders with: step_id={step_id}, project_id={project_id}, agent={agent},
task_context={instructions_extracted_from_command_file}
''',
    description="{phase description}"
)
```

## Roadmap Quality Gate (Automated, Zero Token Cost)

After roadmap creation, before reviewer, run these checks in your own context:
1. AC implementation coupling: flag acceptance criteria referencing private methods (`_method()`)
2. Step decomposition ratio: flag if steps/files ratio exceeds 2.5
3. Identical pattern detection: flag 3+ steps with identical AC structure (should be batched)
4. Validation-only steps: flag steps with no files_to_modify
5. Step ID format: flag any step_id not matching `^\d{2}-\d{2}$` (e.g. 01-A, 1-1 are invalid)

If HIGH findings exist, return roadmap to architect for one revision pass.

## Skip and Resume Logic

- Check `.develop-progress.json` on start to resume from last failure
- Skip artifact creation if file exists with `validation.status == "approved"`
- Skip completed steps by checking execution-log.yaml for COMMIT/PASS
- Max 2 retry attempts per review rejection, then stop for manual intervention

## Input

- `feature-description` (string, required): natural language, minimum 10 characters
- Derive project-id: strip common prefixes (implement, add, create), remove stop words, kebab-case, max 5 words

## Output Artifacts

```
docs/feature/{project-id}/
  roadmap.yaml              # Phase 1
  execution-log.yaml        # Phase 2 (append-only state)
  .develop-progress.json    # Resume tracking
docs/evolution/
  {project-id}-evolution.md # Phase 3
```

## Quality Gates

- Roadmap review (1 review, max 2 attempts)
- Per-step 5-phase TDD cycle (PREPARE → RED_ACCEPTANCE → RED_UNIT → GREEN → COMMIT)
- Deliver-level Complete Refactoring (Phase 3) — L1-L4 on all modified files
- Deliver-level Adversarial Review (Phase 4) — Testing Theater detection + code quality
- Mutation testing >= 80% kill rate (Phase 5)
- Deliver integrity verification (Phase 6)
- All tests passing after each phase

## Success Criteria

- [ ] Roadmap created and approved
- [ ] All steps executed with COMMIT/PASS (5-phase TDD cycle)
- [ ] L1-L4 refactoring complete on code and tests (Phase 3)
- [ ] Adversarial review passed (Phase 4)
- [ ] Mutation testing gate passed >= 80% (Phase 5)
- [ ] Deliver integrity verification passed (Phase 6)
- [ ] Evolution document archived (Phase 7)
- [ ] Retrospective completed or clean execution noted (Phase 8)
- [ ] Completion report displayed (Phase 9)

## Examples

### Example 1: Fresh Feature

```bash
/nw:deliver "Implement user authentication with JWT tokens"
```

Creates roadmap, reviews it, executes all steps with TDD, runs mutation testing, finalizes to docs/evolution/, reports completion.

### Example 2: Resume After Failure

```bash
/nw:deliver "Implement user authentication with JWT tokens"
```

Same command. Loads .develop-progress.json, skips completed phases, resumes from failure point.

### Example 3: Single Step Alternative

For manual granular control, use individual commands instead:
```bash
/nw:roadmap @nw-solution-architect "goal description"
/nw:execute @nw-software-crafter "project-id" "01-01"
/nw:finalize @nw-platform-architect "project-id"
```

## Completion

DELIVER is the final wave. After completion, return to DISCOVER for the next feature iteration or mark the project as complete.
