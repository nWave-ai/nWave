---
name: nw-command-design-patterns-classification
description: How to size and categorize a command, the declarative command template, and the WHAT-vs-HOW logic-placement rule
user-invocable: false
disable-model-invocation: true
---

# Command Classification, Sizing, and Declarative Template (KNOWLEDGE)

**Kind**: KNOWLEDGE (reference). Composed by `nw-command-design-patterns` core. Fires when: a command must be classified, sized, or restructured against the declarative template (the "what category / what size / what shape" question). No forced sequence.

## The Forge Model (Gold Standard)

`forge.md` at 40 lines is the reference dispatcher. Contains: header (wave, agent, overview) | Agent invocation (name + command + config) | Success criteria (checklist) | Next wave handoff | Expected outputs. Every dispatcher should aspire to this pattern.

## Command Categories

| Category | Description | Size Target | Examples |
|----------|-------------|-------------|----------|
| Simple | Direct action, minimal delegation | 40-80 lines | forge, start, version, git |
| Dispatcher | Delegates to one agent with context | 40-150 lines | research, review, execute |
| Orchestrator | Coordinates multiple agents/phases | 100-300 lines | develop, document |

## Declarative Command Template

Commands declare WHAT, not HOW. The agent knows how to do its job.

```markdown
# DW-{NAME}: {Title}

**Wave**: {WAVE_NAME}
**Agent**: {persona} ({agent-id})

## Overview

One paragraph: what this command does and when to use it.

## Context Files Required

- {path} - {why needed}

## Agent Invocation

@{agent-id}

Execute \*{command} for {parameters}.

**Context Files:**
- {files the orchestrator reads and passes}

**Configuration:**
- {key}: {value} # {comment}

## Success Criteria

- [ ] {measurable outcome}
- [ ] {quality gate}

## Next Wave

**Handoff To**: {next wave or workflow step}
**Deliverables**: {what this command produces}

# Expected outputs:
# - {file paths}
```

## Size Targets and Evidence

Research (Chroma Research, Anthropic context engineering): focused prompts (~300 tokens) outperform full prompts (~113k tokens) | Claude shows most pronounced performance gap | Information buried mid-prompt gets deprioritized ("Lost in the Middle") | Opus 4.6 is proactive/self-directing; verbose instructions cause overtriggering

Targets: Dispatchers 40-150 lines | Orchestrators 100-300 lines | Current average 437 lines; target under 150

## When Commands Should Contain Logic vs Delegate

**Contain in command** (declarative):

1. Which agent to invoke
2. What context files to read/pass
3. Success criteria and quality gates
4. Next wave handoff

**Delegate to agent**:

1. Methodology (TDD phases, review criteria, refactoring levels)
2. Domain-specific templates/schemas
3. Tool-specific config (cosmic-ray, pytest)
4. Quality assessment rubrics

Rule: if content describes HOW the agent does its work, it belongs in agent definition or skill, not command.
