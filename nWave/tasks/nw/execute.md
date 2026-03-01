---
description: "Dispatches a single roadmap step to a specialized agent for TDD execution. Use when implementing a specific step from a roadmap.json plan."
argument-hint: '[agent] [feature-id] [step-id] - Example: @nw-software-crafter "auth-upgrade" "01-01"'
---

# NW-EXECUTE: Atomic Task Execution

**Wave**: EXECUTION_WAVE | **Agent**: Dispatched agent (specified by caller)

## Overview

Dispatch a single roadmap step to an agent. Orchestrator extracts step context from roadmap so agent never loads the full roadmap.

## Syntax

```
/nw:execute @{agent} "{feature-id}" "{step-id}"
```

## Context Files Required

- `docs/feature/{feature-id}/deliver/roadmap.json` — Orchestrator reads once, extracts step context
- `docs/feature/{feature-id}/deliver/execution-log.json` — Agent appends only (never reads)

## Rigor Profile Integration

Before dispatching the agent, read rigor config from `.nwave/des-config.json` (key: `rigor`). If absent, use standard defaults.

- **`agent_model`**: Pass as `model` parameter to Task tool. If `"inherit"`, omit `model` (inherits from session).
- **`tdd_phases`**: If `["RED_UNIT", "GREEN"]` (lean), modify the TDD_PHASES section in the DES template to only include those 2 phases. Remove PREPARE/RED_ACCEPTANCE/COMMIT instructions.
- **`refactor_pass`**: If `false`, skip COMMIT phase refactoring instructions.

## Dispatcher Workflow

1. Parse parameters: agent name|feature ID|step ID
2. Read rigor profile from `.nwave/des-config.json` (default: standard)
3. Validate roadmap and execution-log exist
4. Grep roadmap for `step_id: "{step-id}"` with ~50 lines context
5. Extract step fields and invoke Task tool with DES template below, applying rigor model and phases

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
Command: /nw:execute

# AGENT_IDENTITY
Agent: {agent-name}

# SKILL_LOADING
Before starting TDD phases, read your skill files for methodology guidance.
Skills path: ~/.claude/skills/nw/{agent-name}/
Always load at PREPARE: tdd-methodology.md, quality-framework.md
Load on-demand per phase as specified in your Skill Loading Strategy table.

# TASK_CONTEXT
{step context from roadmap - name|description|acceptance_criteria|test_file|scenario_line|acceptance_test_scenario|quality_gates|implementation_notes|dependencies|estimated_hours|deliverables}

# TDD_PHASES
Execute in order:
0. PREPARE - Load context, verify prerequisites
1. RED_ACCEPTANCE - Write failing acceptance test
2. RED_UNIT - Write failing unit test
3. GREEN - Minimal code to pass tests
   After GREEN: run FULL test suite. If all pass, proceed to COMMIT immediately.
   Never move to new task or stop without committing green code.
4. COMMIT - Stage and commit with conventional message
   Include git trailer: `Step-ID: {step-id}` (required for DES verification)
   Example:
   ```
   feat(feature-id): implement feature X

   Step-ID: 02-01
   ```

# QUALITY_GATES
- All tests pass before COMMIT
- No skipped phases without blocked_by reason
- Coverage maintained or improved

# OUTCOME_RECORDING
After ACTUALLY EXECUTING each phase, record via DES CLI:

    PYTHONPATH=$HOME/.claude/lib/python python -m des.cli.log_phase \
      --project-dir docs/feature/{feature-id}/deliver \
      --step-id {step-id} \
      --phase {PHASE_NAME} \
      --status EXECUTED \
      --data PASS

For SKIPPED phases (genuinely not applicable):

    PYTHONPATH=$HOME/.claude/lib/python python -m des.cli.log_phase \
      --project-dir docs/feature/{feature-id}/deliver \
      --step-id {step-id} \
      --phase {PHASE_NAME} \
      --status SKIPPED \
      --data "NOT_APPLICABLE: reason"

CLI enforces real UTC timestamps and validates phase names.
Do NOT manually edit execution-log.json.

CRITICAL: Only the executing agent calls the CLI.
Orchestrator MUST NEVER write phase entries — only the agent that performed the work. A log entry without actual execution is a **violation that DES detects and that will cause integrity verification to fail**, blocking finalize.

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
- max_turns by step complexity:

| Step Type | Typical Tool Calls | Recommended max_turns |
|-----------|-------------------|----------------------|
| Hotfix (1 file) | 10-12 | 25 |
| Standard TDD (2-3 files) | 25-30 | 45 |
| Complex (4+ files, new module) | 35-45 | 65 |

Default: 45. Heuristic: `20 + (files_to_modify count * 8)`, capped at 65.

## Error Handling

- Invalid agent: report available agents
- Missing roadmap/execution-log: report path not found
- Step not in roadmap: report available step IDs
- Dependency failure: explain blocking tasks

## Resume vs Restart

When subagent times out:

| Last Completed Phase | Action | Rationale |
|---------------------|--------|-----------|
| GREEN (or later) | Resume | Only COMMIT remains (~5 turns) |
| RED_UNIT with partial GREEN | Resume | Preserves implementation progress |
| PREPARE or RED_ACCEPTANCE | Restart | Little context worth replaying |

Resume costs ~50% more tokens/call due to context replay (measured: 3.7K vs 2.5K tokens/call). For <5 remaining turns, resume is efficient. For 15+ turns, restart with higher max_turns is cheaper.

## Examples

```bash
/nw:execute @nw-software-crafter "des-us007-boundary-rules" "02-01"
/nw:execute @nw-researcher "auth-upgrade" "01-01"
/nw:execute @nw-software-crafter "des-us007" "03-01"  # retry after failure
```

## TDD_PHASES
<!-- Schema v4.0 — canonical source: TDDPhaseValidator.MANDATORY_PHASES -->
<!-- Build system injects mandatory phases from step-tdd-cycle-schema.json -->
{{MANDATORY_PHASES}}

## Success Criteria

- [ ] Agent invoked via Task tool (dispatcher does not execute the work)
- [ ] Step context extracted from roadmap and passed in prompt
- [ ] Agent appended phase events to execution-log.json
- [ ] Agent did not load roadmap.json

## Next Wave

**Handoff To**: /nw:review for post-execution review
**Deliverables**: Updated execution-log.json|implementation artifacts|git commits
