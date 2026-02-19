---
description: "Dispatches a single roadmap step to a specialized agent for TDD execution. Use when implementing a specific step from a roadmap.yaml plan."
argument-hint: '[agent] [project-id] [step-id] - Example: @nw-software-crafter "auth-upgrade" "01-01"'
disable-model-invocation: true
---

# NW-EXECUTE: Atomic Task Execution

**Wave**: EXECUTION_WAVE
**Agent**: Dispatched agent (specified by caller)

## Overview

Dispatch a single roadmap step to an agent. The orchestrator extracts step context from the roadmap so the agent never loads the full roadmap.

## Syntax

```
/nw:execute @{agent} "{project-id}" "{step-id}"
```

## Context Files Required

- `docs/feature/{project-id}/roadmap.yaml` - Orchestrator reads once, extracts step context
- `docs/feature/{project-id}/execution-log.yaml` - Agent appends only (never reads)

## Dispatcher Workflow

1. Parse parameters: agent name, project ID, step ID
2. Validate roadmap and execution-log exist
3. Grep roadmap for `step_id: "{step-id}"` with ~50 lines context
4. Extract step fields and invoke Task tool with the DES template below

## Agent Invocation

@{agent}

Use this DES template verbatim. Fill `{placeholders}` with values extracted from the roadmap. Without the DES markers, hooks cannot validate the task.

```
<!-- DES-VALIDATION : required -->
<!-- DES-PROJECT-ID : {project-id} -->
<!-- DES-STEP-ID : {step-id} -->

# DES_METADATA
Step: {step-id}
Project: {project-id}
Command: /nw:execute

# AGENT_IDENTITY
Agent: {agent-name}

# TASK_CONTEXT
{step context extracted from roadmap - name, description, acceptance_criteria, test_file, scenario_line, acceptance_test_scenario, quality_gates, implementation_notes, dependencies, estimated_hours, deliverables}

# TDD_PHASES
Execute these phases in order:
0. PREPARE - Load context, verify prerequisites
1. RED_ACCEPTANCE - Write failing acceptance test
2. RED_UNIT - Write failing unit test
3. GREEN - Minimal code to pass tests
   After GREEN: run the FULL test suite. If all tests pass, proceed to COMMIT immediately.
   Never move to a new task or stop without committing green code.
4. COMMIT - Stage and commit with conventional message
   Include git trailer: `Step-ID: {step-id}` (required for DES verification)
   Example commit message:
   ```
   feat(project-id): implement feature X

   Step-ID: 02-01
   ```

# QUALITY_GATES
- All tests pass before COMMIT
- No skipped phases without blocked_by reason
- Coverage maintained or improved

# OUTCOME_RECORDING
After ACTUALLY EXECUTING each phase, record it using the DES CLI:

    PYTHONPATH=$HOME/.claude/lib/python python -m des.cli.log_phase \
      --project-dir docs/feature/{project-id} \
      --step-id {step-id} \
      --phase {PHASE_NAME} \
      --status EXECUTED \
      --data PASS

For SKIPPED phases (genuinely not applicable):

    PYTHONPATH=$HOME/.claude/lib/python python -m des.cli.log_phase \
      --project-dir docs/feature/{project-id} \
      --step-id {step-id} \
      --phase {PHASE_NAME} \
      --status SKIPPED \
      --data "NOT_APPLICABLE: reason"

The CLI enforces real UTC timestamps and validates phase names.
Do NOT manually edit execution-log.yaml.

CRITICAL: Only the executing agent calls the CLI.
The orchestrator MUST NEVER write phase entries — only the agent that
performed the work. A log entry without actual execution is fraud.

# BOUNDARY_RULES
- Only modify files listed in step's files_to_modify
- Do not load roadmap.yaml
- Do not modify execution-log.yaml structure (append only)
- NEVER write execution-log entries for phases you did not execute

# TIMEOUT_INSTRUCTION
Target: 30 turns maximum. If approaching limit, COMMIT current progress.
If GREEN is complete (all tests pass), you MUST commit before returning — even if at turn limit.
```

**Configuration:**
- subagent_type: extracted agent name
- max_turns by step complexity (measured data):

| Step Type | Typical Tool Calls | Recommended max_turns |
|-----------|-------------------|----------------------|
| Hotfix (1 file, known fix) | 10-12 | 25 |
| Standard TDD step (2-3 files) | 25-30 | 45 |
| Complex step (4+ files, new module) | 35-45 | 65 |

Default: 45. Heuristic: `20 + (files_to_modify count * 8)`, capped at 65.

## Error Handling

- Invalid agent: report available agents
- Missing roadmap/execution-log: report path not found
- Step not in roadmap: report available step IDs
- Dependency failure: explain blocking tasks to user

## Resume vs Restart

When a subagent times out:

| Last Completed Phase | Action | Rationale |
|---------------------|--------|-----------|
| GREEN (or later) | Resume | Only COMMIT remains (~5 turns) |
| RED_UNIT with partial GREEN | Resume | Preserves implementation progress |
| PREPARE or RED_ACCEPTANCE | Restart | Little context worth replaying |

Resume costs ~50% more tokens per tool call due to context replay (measured:
3.7K vs 2.5K tokens/call). For <5 remaining turns, resume is efficient.
For 15+ turns needed, restart with higher max_turns is cheaper.

## Examples

```bash
# Implementation step
/nw:execute @nw-software-crafter "des-us007-boundary-rules" "02-01"

# Research step
/nw:execute @nw-researcher "auth-upgrade" "01-01"

# Retry after failure (agent resumes from last completed phase)
/nw:execute @nw-software-crafter "des-us007" "03-01"
```

## TDD_PHASES
<!-- Schema v4.0 — canonical source: TDDPhaseValidator.MANDATORY_PHASES -->
<!-- Build system injects mandatory phases from step-tdd-cycle-schema.json -->
{{MANDATORY_PHASES}}

## Success Criteria

- [ ] Agent invoked via Task tool (dispatcher does not execute the work)
- [ ] Step context extracted from roadmap and passed in prompt
- [ ] Agent appended phase events to execution-log.yaml
- [ ] Agent did not load roadmap.yaml

## Next Wave

**Handoff To**: /nw:review for post-execution review
**Deliverables**: Updated execution-log.yaml, implementation artifacts, git commits
