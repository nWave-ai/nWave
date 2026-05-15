---
name: nw-execute
description: "Dispatches a single roadmap step to a specialized agent for TDD execution. Use when implementing a specific step from a roadmap.json plan."
user-invocable: true
argument-hint: '[agent] [feature-id] [step-id] - Example: @nw-software-crafter "auth-upgrade" "01-01"'
---

# NW-EXECUTE: Atomic Task Execution

**Wave**: EXECUTION_WAVE | **Agent**: Dispatched agent (specified by caller)

## Overview

Dispatch a single roadmap step to an agent. Orchestrator extracts step context from roadmap so agent never loads the full roadmap.

## Syntax

```
/nw-execute @{agent} "{feature-id}" "{step-id}"
```

## Context Files Required

- `docs/feature/{feature-id}/deliver/roadmap.json` — Orchestrator reads once, extracts step context
- `docs/feature/{feature-id}/deliver/execution-log.json` — Agent appends only (never reads)

## Rigor Profile Integration

Before dispatching the agent, read rigor config from `.nwave/des-config.json` (key: `rigor`). If absent, use standard defaults.

- **`agent_model`**: Pass as `model` parameter to Agent tool. If `"inherit"`, omit `model` (inherits from session).
- **`tdd_phases`**: Modify the TDD_PHASES section in the DES template to match the configured phases. The 3-phase canon (ADR-025) is `[RED, GREEN, COMMIT]`; the lean variant is `[RED, GREEN]`. Legacy 5-phase contract (`[PREPARE, RED_ACCEPTANCE, RED_UNIT, GREEN, COMMIT]`) and its lean variant (`[RED_UNIT, GREEN]`) remain supported for audit-log replay of pre-2026-05-07 commits. Remove omitted phases' instructions from the template.
- **`refactor_pass`**: If `false`, skip COMMIT phase refactoring instructions.

## Dispatcher Workflow

1. **Parse Parameters** — Extract agent name, feature ID, and step ID from invocation. Gate: all three parameters present and non-empty.
2. **Load Rigor Profile** — Read `.nwave/des-config.json` key `rigor` (default: standard if absent). Gate: config loaded or default applied.
3. **Validate Context Files** — Confirm `docs/feature/{feature-id}/deliver/roadmap.json` and `execution-log.json` exist. Gate: both files present; report path-not-found if missing.
4. **Extract Step Context** — Grep roadmap for `step_id: "{step-id}"` with ~50 lines context. Gate: step found; report available step IDs if missing.
5. **Invoke Agent** — Call Agent tool with DES template below, applying rigor model and phases from step 2. Gate: Agent tool called, not executed inline.

## Agent Invocation

@{agent}

Use this DES template verbatim. Fill `{placeholders}` from roadmap. Without DES markers, hooks cannot validate.

```
<!-- DES-VALIDATION : required -->
<!-- DES-PROJECT-ID : {feature-id} -->
<!-- DES-STEP-ID : {step-id} -->

# DES_METADATA
Step: {step-id}
Feature: {feature-id}
Command: /nw-execute

# AGENT_IDENTITY
Agent: {agent-name}

# SKILL_LOADING
Before starting TDD phases, read your skill files for methodology guidance.
Skills path: ~/.claude/skills/nw-{skill-name}/SKILL.md
Always load before RED: tdd-methodology.md, quality-framework.md (3-phase canon, ADR-025) — legacy 5-phase logs reference loading at PREPARE.
Load on-demand per phase as specified in your Skill Loading Strategy table.

# TASK_CONTEXT
{step context from roadmap - name|criteria|test_file|scenario_name|implementation_notes|deps|files_to_modify (per nWave/templates/roadmap-schema.json)}

# DESIGN_CONTEXT
{Summary of architectural decisions relevant to this step, extracted by the orchestrator from docs/product/architecture/brief.md and wave-decisions.md. Include: component structure, dependency boundaries, technology choices, and any design constraints that affect implementation. If no design artifacts exist, write "No design artifacts available — use project conventions."}

# TDD_PHASES
3-phase canon (ADR-025, 2026-05-07). Execute in order:

1. RED - Activate the pre-authored acceptance test (PRIMARY TBU DEFENSE); write PBT unit tests ONLY if the AT cannot reach GREEN without them.
   AT activation: If TASK_CONTEXT includes test_file, locate it and remove the @skip/@ignore/@pending/xit/.skip/[Ignore] marker from the target scenario (the AT scaffold was authored by DISTILL — DELIVER does NOT re-author ATs). Run it — must fail for business logic reason (not import/syntax error). Fail-for-right-reason gate: collected ≥ 1, failures ≥ 1, no collection errors, semantic AssertionError / expected-exception-not-thrown.
   PORT-TO-PORT PRINCIPLE: The acceptance test exercises the scenario through
   the driving port (application service, orchestrator, CLI handler, API controller),
   not a decomposed helper or internal class. A correctly-written port-to-port test
   makes TBU structurally impossible — if a new function were missing or unwired,
   THIS test stays RED. That is the entire point: GREEN is unreachable without wiring.
   Litmus test: "If I delete the call-site that wires the new code, does this test fail?"
   If no → the test is at the wrong level. Stop and flag to orchestrator (DISTILL re-author needed).
   Conditional unit-test authoring: write PBT unit tests (or integration tests for adapter/infrastructure code — adapters use real infrastructure, never mocked unit tests) ONLY when the AT requires them to reach GREEN. If the AT can pass via direct minimal implementation, skip unit-test authoring inside RED.

2. GREEN - Minimal code to pass AT + any unit tests authored in RED.
   After GREEN: run FULL test suite. If all pass, proceed to COMMIT immediately.
   Smell test: if any new function is only called from test code, your acceptance
   test is at the wrong abstraction level — stop and flag.
   Never move to new task or stop without committing green code.

3. COMMIT - Stage and commit with conventional message.
   Include git trailer: `Step-ID: {step-id}` (required for DES verification)
   Example:
   ```
   feat(feature-id): implement feature X

   Step-ID: 02-01
   ```

LEGACY 5-PHASE CONTRACT (ADR-024 era, pre-2026-05-07): PREPARE → RED_ACCEPTANCE → RED_UNIT → GREEN → COMMIT. Preserved for audit-log replay only — new work uses the 3-phase canon above. Audit-log entries referencing RED_ACCEPTANCE/RED_UNIT/PREPARE represent merged sub-steps now folded into RED.

# QUALITY_GATES
- All tests pass before COMMIT
- No skipped phases without blocked_by reason
- Coverage maintained or improved

# OUTCOME_RECORDING
After ACTUALLY EXECUTING each phase, record via DES CLI:

    des-log-phase \
      --project-dir docs/feature/{feature-id}/deliver \
      --step-id {step-id} \
      --phase {PHASE_NAME} \
      --status EXECUTED \
      --data PASS

For SKIPPED phases (genuinely not applicable):

    des-log-phase \
      --project-dir docs/feature/{feature-id}/deliver \
      --step-id {step-id} \
      --phase {PHASE_NAME} \
      --status SKIPPED \
      --data "NOT_APPLICABLE: reason"

CLI enforces real UTC timestamps and validates phase names.
Do NOT manually edit execution-log.json.
Use the DES CLI to record phase outcomes and create log files.
Python resolution: `$(command -v python3 || command -v python)` — works on macOS (python3 only), Linux, and Windows.

CRITICAL: Only the executing agent calls the CLI.
Orchestrator MUST NEVER write phase entries — only the agent that performed the work. A log entry without actual execution is a **violation that DES detects and that will cause integrity verification to fail**, blocking finalize.

# RECORDING_INTEGRITY
Valid Skip Prefixes: NOT_APPLICABLE, BLOCKED_BY_DEPENDENCY, APPROVED_SKIP, CHECKPOINT_PENDING
Anti-Fraud Rules:
- NEVER write EXECUTED for phases you did not actually perform
- NEVER invent timestamps — DES CLI generates real UTC timestamps
- DES audits all entries; integrity violations block finalize

# BOUNDARY_RULES
- Only modify files listed in step's files_to_modify
- Do not load roadmap.json
- Do not modify execution-log.json structure (append only)
- NEVER write execution-log entries for phases you did not execute

# TIMEOUT_INSTRUCTION
Target: 30 turns max. If approaching limit, COMMIT current progress.
If GREEN complete (all tests pass), MUST commit before returning — even at turn limit.
```

**Configuration:**
- subagent_type: extracted agent name
- Turn limits are defined in each agent's `maxTurns` frontmatter field (not as a tool parameter)

## Error Handling

1. **Invalid Agent** — Report available agents from the agent registry. Gate: error message returned, no invocation attempted.
2. **Missing Context Files** — Report exact path not found for roadmap or execution-log. Gate: clear path reported.
3. **Step Not in Roadmap** — Report available step IDs from roadmap. Gate: list of valid IDs returned.
4. **Dependency Failure** — Explain which blocking tasks are incomplete. Gate: blocking step IDs named explicitly.

## Resume vs Restart

When subagent times out:

| Last Completed Phase (3-phase canon) | Legacy phase (5-phase) | Action | Rationale |
|--------------------------------------|------------------------|--------|-----------|
| GREEN (or later) | GREEN | Resume | Only COMMIT remains (~5 turns) |
| RED with partial GREEN | RED_UNIT with partial GREEN | Resume | Preserves implementation progress |
| RED only (pre-GREEN) | PREPARE or RED_ACCEPTANCE | Restart | Little context worth replaying |

Resume costs ~50% more tokens/call due to context replay (measured: 3.7K vs 2.5K tokens/call). For <5 remaining turns, resume is efficient. For 15+ turns, restart is cheaper.

## Examples

```bash
/nw-execute @nw-software-crafter "des-us007-boundary-rules" "02-01"
/nw-execute @nw-researcher "auth-upgrade" "01-01"
/nw-execute @nw-software-crafter "des-us007" "03-01"  # retry after failure
```

## TDD_PHASES
<!-- Schema v4.0 — canonical source: TDDPhaseValidator.MANDATORY_PHASES -->
<!-- Build system injects mandatory phases from step-tdd-cycle-schema.json -->
{{MANDATORY_PHASES}}

## Success Criteria

- [ ] Agent invoked via Agent tool (dispatcher does not execute the work)
- [ ] Step context extracted from roadmap and passed in prompt
- [ ] Agent appended phase events to execution-log.json
- [ ] Agent did not load roadmap.json

## Next Wave

**Handoff To**: /nw-review for post-execution review
**Deliverables**: Updated execution-log.json|implementation artifacts|git commits
