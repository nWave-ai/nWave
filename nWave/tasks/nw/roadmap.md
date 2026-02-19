---
description: "Creates a phased roadmap.yaml for a feature goal with acceptance criteria and TDD steps. Use when planning implementation steps before execution."
disable-model-invocation: true
argument-hint: '[agent] [goal-description] - Example: @solution-architect "Migrate to microservices"'
---

# NW-ROADMAP: Goal Planning

**Wave**: CROSS_WAVE
**Agent**: Architect (nw-solution-architect) or domain-appropriate agent

## Overview

Dispatches an expert agent to fill in a pre-scaffolded YAML roadmap skeleton. The CLI tools handle structure; the agent handles content.

Output: `docs/feature/{project-id}/roadmap.yaml`

## Usage

```bash
/nw:roadmap @nw-solution-architect "Migrate monolith to microservices"
/nw:roadmap @nw-software-crafter "Replace legacy authentication system"
/nw:roadmap @nw-product-owner "Implement multi-tenant support"
```

## Execution Steps

You MUST execute these 3 steps in order. Do NOT skip any step.

**Step 1 — Parse parameters:**
1. Agent name (after @, validated against agent registry)
2. Goal description (quoted string)
3. Derive project-id from goal (kebab-case, e.g., "Migrate to OAuth2" → "migrate-to-oauth2")

**Step 2 — Scaffold skeleton via CLI (mandatory, do this BEFORE invoking the agent):**

Run this Bash command now:
```bash
PYTHONPATH=~/.claude/lib/python python3 -m des.cli.roadmap init \
  --project-id {project-id} \
  --goal "{goal-description}" \
  --output docs/feature/{project-id}/roadmap.yaml
```
For complex projects add: `--phases 3 --steps "01:3,02:2,03:1"`

If exit code is non-zero, stop and report the error. Do NOT write the file manually.

**Step 3 — Invoke agent to fill the skeleton:**

The skeleton file now exists with TODO placeholders. Invoke the agent via Task tool:
```
@{agent-name}

Fill in the roadmap skeleton at docs/feature/{project-id}/roadmap.yaml.
Replace every TODO with real content. Do NOT change the YAML structure
(phases, steps, keys). Fill in: names, descriptions, acceptance criteria,
time estimates, dependencies, and implementation_scope paths.

Goal: {goal-description}
```

Context to pass (if available): measurement baseline, mikado-graph.md, existing docs.

**Step 4 — Validate via CLI (hard gate, mandatory):**

Run this Bash command now:
```bash
PYTHONPATH=~/.claude/lib/python python3 -m des.cli.roadmap validate docs/feature/{project-id}/roadmap.yaml
```
- Exit 0 → report success, roadmap is ready
- Exit 1 → print errors, STOP, do NOT proceed to execution
- Exit 2 → usage error, STOP

## Invocation Principles

Keep the agent prompt minimal. The agent knows roadmap structure and planning methodology.

Pass: skeleton file path + goal description + measurement context (if available).
Do not pass: YAML templates, phase guidance, step decomposition rules.

For performance roadmaps, include measurement context inline so the agent can validate targets against baselines.

## Success Criteria

### Dispatcher (you) — all 4 must be checked
- [ ] Parameters parsed (agent name, goal, project-id)
- [ ] `des.cli.roadmap init` executed via Bash (exit 0)
- [ ] Agent invoked via Task tool to fill TODO placeholders
- [ ] `des.cli.roadmap validate` executed via Bash (exit 0)

### Agent output (reference)
- [ ] All TODO placeholders replaced with real content
- [ ] Steps are self-contained and atomic
- [ ] Acceptance criteria are behavioral and measurable
- [ ] Step decomposition ratio <= 2.5 (steps / production files)
- [ ] Dependencies mapped, time estimates provided

## Error Handling

- Invalid agent: report valid agents and stop
- Missing goal: show usage syntax and stop
- Scaffold failure (exit 2): report CLI error and stop
- Validation failure (exit 1): print errors, do not proceed to execution

## Examples

### Example 1: Standard architecture roadmap
```
/nw:roadmap @nw-solution-architect "Migrate authentication to OAuth2"
```
Dispatcher derives project-id="migrate-auth-to-oauth2", scaffolds skeleton, invokes agent to fill TODOs, validates output. Agent produces docs/feature/migrate-auth-to-oauth2/roadmap.yaml.

### Example 2: Performance roadmap with measurement context
```
/nw:roadmap @nw-solution-architect "Optimize test suite execution"
```
Orchestrator passes measurement data inline. Agent fills skeleton, validates targets against baseline, prioritizes largest bottleneck first.

### Example 3: Mikado refactoring
```
/nw:roadmap @nw-software-crafter "Extract payment module from monolith"
```
Agent fills skeleton with methodology: mikado, references mikado-graph.md, maps leaf nodes to steps.

## Workflow Context

```bash
/nw:roadmap @agent "goal"           # 1. Plan (init → agent fills → validate)
/nw:execute @agent "project" "01-01" # 2. Execute steps
/nw:finalize @agent "project"        # 3. Finalize
```
