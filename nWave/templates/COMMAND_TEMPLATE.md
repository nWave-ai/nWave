# nWave Command Template

Version: 1.0 (2026-02-28)
Extracted from analysis of 22 production command files.
Replaces COMMAND_TEMPLATE.yaml (437 lines of comments) with actionable markdown.

## Frontmatter Schema

```yaml
---
description: "{What this command does. When to use it.}"           # REQUIRED. String.
argument-hint: "{usage pattern with parameters}"                    # OPTIONAL. String.
disable-model-invocation: true                                      # OPTIONAL. Boolean.
---
```

### Field Reference

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| description | string | yes | Shown in command help. Include "Use when..." |
| argument-hint | string | no | Usage pattern: `[param] - Optional: --flag=[values]` |
| disable-model-invocation | boolean | no | Set true for commands invoked only by orchestrator |

---

## Command Categories

| Category | Size Target | Structure | Examples |
|----------|-------------|-----------|----------|
| Dispatcher | 40-80 lines | Agent invocation + success criteria | forge, research, review |
| Orchestrator | 100-250 lines | Multi-phase coordination + agent invocations | deliver, discuss, design |

## Body Template: Dispatcher (40-80 lines)

```markdown
---
description: "{Description. Use when...}"
argument-hint: "[param] - Optional: --flag=[value]"
---

# NW-{NAME}: {Title}

**Wave**: {WAVE_NAME} | **Agent**: {PersonaName} (nw-{agent-id})

## Overview

{One paragraph: what this command does and when to use it.}

## Context Files Required

- {path} - {why this file is needed}
- {path} - {why this file is needed}

## Agent Invocation

@nw-{agent-id}

Execute \*{command} for {parameters}.

**Context Files:**
- {files the orchestrator reads and passes}

**Configuration:**
- {key}: {value}

## Success Criteria

- [ ] {measurable outcome}
- [ ] {quality gate}
- [ ] {deliverable exists}

## Examples

### Example 1: {Standard usage}
```
/nw:{command} "{arguments}"
```
{Brief description of what happens.}

## Next Wave

**Handoff To**: {next-wave-agent or "Invoking workflow"}
**Deliverables**: {what this command produces}

## Expected Outputs

```
{file paths produced}
```
```

## Body Template: Orchestrator (100-250 lines)

```markdown
---
description: "{Description. Use when...}"
argument-hint: "[param] - Optional: --flag=[value]"
---

# NW-{NAME}: {Title}

**Wave**: {WAVE_NAME} | **Agent**: Main Instance (orchestrator) | **Command**: `/nw:{name}`

## Overview

{One paragraph: what this command orchestrates.}

Sub-agents cannot use Skill tool or `/nw:*` commands. You MUST:
- Read the relevant command file and embed instructions in the Task prompt
- Remind the agent to load its skills at `~/.claude/skills/nw/{agent-name}/`

## Interactive Decision Points

### Decision 1: {Choice}
**Question**: {What the orchestrator asks the user}
**Options**:
1. {Option} -- {description}
2. {Option} -- {description}

## Context Files Required

- {path} - {why needed}

## Rigor Profile Integration

Before dispatching, read rigor config from `.nwave/des-config.json` (key: `rigor`). If absent, use standard defaults.

- **`agent_model`**: Pass as `model` to Task tool. If `"inherit"`, omit.
- **`reviewer_model`**: Pass to reviewer Task. If `"skip"`, skip review phase.

## Orchestration Flow

```
INPUT: "{parameters}"
  |
  1. {Phase 1 description}
  |
  2. {Phase 2 description} -- @nw-{agent} via Task
  |
  3. {Phase 3 description} -- @nw-{agent} via Task
  |
  N. Report completion
```

## Task Invocation Pattern

```python
Task(
    subagent_type="{agent}",
    model=rigor_agent_model,  # omit if "inherit"
    max_turns=45,
    prompt=f'''
TASK BOUNDARY: {description}

SKILL_LOADING: Read skills at ~/.claude/skills/nw/{agent-name}/.

{task-specific context}
''',
    description="{phase description}"
)
```

## Success Criteria

- [ ] {Phase 1 outcome}
- [ ] {Phase 2 outcome}
- [ ] {Overall outcome}

## Examples

### Example 1: {Standard execution}
`/nw:{name} "{arguments}"` -- {description of full flow}

### Example 2: {Resume after failure}
Same command -- {description of resume behavior}

## Next Wave

**Handoff To**: {next-wave or "completion"}
**Deliverables**: {final artifacts}

## Expected Outputs

```
{file paths produced}
```
```

---

## Section Reference

### Required Sections (all commands)

| Section | Purpose |
|---------|---------|
| Title (`# NW-{NAME}`) | Command identity with wave and agent |
| Overview | What the command does, one paragraph |
| Agent Invocation | Which agent, what command, configuration |
| Success Criteria | Measurable outcomes checklist |
| Next Wave | Handoff target and deliverables |

### Optional Sections (by category)

| Section | When to Include |
|---------|----------------|
| Interactive Decision Points | Orchestrators with user choices |
| Context Files Required | Commands needing file context |
| Rigor Profile Integration | Commands dispatching Task agents |
| Orchestration Flow | Orchestrators with multi-phase coordination |
| Task Invocation Pattern | Orchestrators showing Task tool usage |
| Error Handling | Commands with validation/error states |
| Examples | All commands (1-4 examples) |
| Expected Outputs | Commands producing file artifacts |

---

## Design Principles

### Commands Declare WHAT, Not HOW

**Include in command** (declarative):
- Which agent to invoke
- What context files to read and pass
- Success criteria and quality gates
- Next wave handoff

**Delegate to agent** (belongs in agent definition or skill):
- Methodology (TDD phases, review criteria, refactoring levels)
- Domain-specific templates and schemas
- Tool-specific configuration
- Quality assessment rubrics

Rule: if content describes HOW the agent does its work, it belongs in the agent
definition or skill, not in the command file.

### SKILL_LOADING Reminder

Every command dispatching a sub-agent via Task MUST include a SKILL_LOADING reminder
in the Task prompt. Sub-agents cannot use the Skill tool and the `skills:` frontmatter
is decorative only.

```
SKILL_LOADING: Read your skill files at ~/.claude/skills/nw/{agent-name}/.
At PREPARE phase, always load: {primary-skill}.md.
Then follow your Skill Loading Strategy table for phase-specific skills.
```

---

## Anti-Patterns

| Anti-Pattern | Impact | Fix |
|---|---|---|
| Embedded workflow steps | Command becomes 500+ lines | Move to agent definition |
| Duplicated agent knowledge | Same content in command and agent | Remove from command |
| Procedural overload | Step-by-step for capable agents | Declare goal + constraints |
| Aggressive language | Overtriggering in Opus 4.6 | Direct statements |
| Example overload | 50+ lines of examples | 2-4 canonical examples |
| Missing SKILL_LOADING | Sub-agent operates without domain knowledge | Add reminder in Task prompt |
| JSON state examples | 200+ lines of format examples | Show actual format, 3 examples max |

---

## Observed Size Statistics

| Category | Lines (min) | Lines (median) | Lines (max) |
|----------|-------------|----------------|-------------|
| Dispatcher | 40 | 65 | 90 |
| Orchestrator | 100 | 170 | 250 |
| All commands | 40 | 110 | 250 |
