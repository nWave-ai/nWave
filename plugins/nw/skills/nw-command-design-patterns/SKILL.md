---
name: nw-command-design-patterns
description: Best practices for command definition files - size targets, declarative template, anti-patterns, and canonical examples based on research evidence
disable-model-invocation: true
---

# Command Design Patterns

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

## The Duplication Triangle

Commands duplicate content in three directions, all waste tokens:

1. **Command-to-Command**: Orchestrator briefings, agent registries, parameter parsing repeated in 5-12 files (~620 lines waste)
2. **Command-to-Agent**: Domain knowledge belonging in agents (~1,300 lines waste). Examples: TDD phases in execute.md, DIVIO templates in document.md, refactoring hierarchies in refactor.md
3. **Command-to-Self**: develop.md embeds other commands inline (~1,000 lines)

Fix: Extract shared content to preamble skill. Move domain knowledge to agents. Have orchestrators reference sub-commands.

## Anti-Patterns

| Anti-pattern | Impact | Fix |
|---|---|---|
| Procedural overload | Step-by-step for capable agents wastes tokens, "lost in the middle" | Declare goal + constraints, let agent apply methodology |
| Duplicated briefings | Same orchestrator constraints in every command (30-80 lines each) | Extract to shared preamble, reference once |
| Embedded domain knowledge | Refactoring hierarchies, review criteria, TDD cycles in commands | Move to agent definitions or skills |
| Aggressive language | "CRITICAL/MANDATORY/MUST" causes overtriggering in Opus 4.6 | Direct statements without emphasis markers |
| Example overload | 50+ lines of JSON examples | 2-3 canonical examples suffice |
| Inline validation logic | Prompt template validation in command text | Platform/hook responsibility |
| Dead code | Deprecated formats, aspirational metrics, old signatures | Remove; version control preserves history |
| Verbose JSON state examples | 200+ lines of unused JSON | Show actual format (pipe-delimited), 3 examples max |

## When Commands Should Contain Logic vs Delegate

**Contain in command** (declarative): Which agent to invoke | What context files to read/pass | Success criteria and quality gates | Next wave handoff

**Delegate to agent**: Methodology (TDD phases, review criteria, refactoring levels) | Domain-specific templates/schemas | Tool-specific config (cosmic-ray, pytest) | Quality assessment rubrics

Rule: if content describes HOW the agent does its work, it belongs in agent definition or skill, not command.

## Canonical Examples

### Example 1: Minimal Dispatcher (forge.md pattern, ~40 lines)

```markdown
# DW-FORGE: Create Agent (V2)

**Wave**: CROSS_WAVE
**Agent**: Zeus (nw-agent-builder)

## Overview

Create a new agent using the research-validated v2 approach.

## Agent Invocation

@nw-agent-builder

Execute \*forge to create {agent-name} agent.

**Configuration:**
- agent_type: specialist | reviewer | orchestrator

## Success Criteria

- [ ] Agent definition under 400 lines
- [ ] 11-point validation checklist passes
- [ ] 3-5 canonical examples included

## Next Wave

**Handoff To**: Agent installation and deployment
**Deliverables**: Agent specification file + Skill files
```

### Example 2: Medium Dispatcher with Context (~80 lines)

```markdown
# DW-RESEARCH: Evidence-Driven Research

**Wave**: CROSS_WAVE
**Agent**: Nova (nw-researcher)

## Overview

Execute systematic evidence-based research with source verification.

## Orchestration: Trusted Source Config

Read .nwave/trusted-source-domains.yaml at orchestration time, embed inline in prompt.

## Agent Invocation

@nw-researcher

Execute \*research on {topic} [--embed-for={agent-name}].

**Configuration:**
- research_depth: detailed
- output_directory: docs/research/

## Success Criteria

- [ ] All sources from trusted domains
- [ ] Cross-reference performed (3+ sources per major claim)
- [ ] Research file created in docs/research/

## Next Wave

**Handoff To**: Invoking workflow
**Deliverables**: Research document + optional embed file
```

### Example 3: Orchestrator (~200 lines)

Coordinates multiple phases without embedding agent knowledge:

```markdown
# DW-DOCUMENT: Documentation Creation

**Wave**: CROSS_WAVE
**Agent**: Orchestrator (self)

## Overview

Create DIVIO-compliant documentation through research and writing phases.

## Phases

1. Research phase: @nw-researcher gathers domain knowledge
2. Writing phase: @nw-documentarist creates documentation
3. Review phase: @nw-reviewer validates quality

## Phase 1: Research

@nw-researcher - Execute \*research on {topic}
[Orchestrator reads and passes relevant context files]

## Phase 2: Writing

@nw-documentarist - Create {doc-type} documentation
[Orchestrator passes research output as context]

## Phase 3: Review

@nw-reviewer - Review documentation against DIVIO standards
[Orchestrator passes documentation for review]

## Success Criteria
[Per-phase and overall criteria]
```

The orchestrator describes WHAT each phase does and WHO does it. The agents know HOW.

## Compression Guidelines

When optimizing command files for token efficiency:

**Safe to compress**: Prose descriptions → pipe-delimited | Verbose explanations → imperative voice | Filler words ("in order to", "it is important to") → remove | Related bullet items → single line with `|` separators

**Never compress**: `### Example N:` section headers — keep verbatim (eval tools and agents depend on these) | AskUserQuestion decision tree options — these are runtime menu items, not documentation | `**Question**:` lines in decision points — runtime behavior | Code blocks and YAML — preserve verbatim | YAML frontmatter — preserve exactly

**Compression evidence**: Pipe-delimited compression achieves 15-30% token reduction on prose-heavy files. Code-heavy files (PBT skills, code examples) yield <5%. Average across framework: ~7.4% overall.

**Orchestrator skill loading section**: Commands dispatching sub-agents must include `SKILL_LOADING` in the Task prompt reminding the agent to read its skills at `~/.claude/skills/nw/{agent-name}/`. Without this, sub-agents operate without domain knowledge (the `skills:` frontmatter is decorative).
