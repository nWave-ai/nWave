---
name: nw-command-design-patterns
description: Best practices for command definition files - size targets, declarative template, anti-patterns, and canonical examples based on research evidence
user-invocable: false
disable-model-invocation: true
---

# Command Design Patterns (composing core)

**Kind**: KNOWLEDGE (lean composing core). The command-design knowledge is decomposed into three one-trigger modules; this core holds the canonical examples and composes the modules by trigger. Load the module(s) for the question in play.

## Composition

| Module | Load when the question is | Path |
|--------|---------------------------|------|
| `nw-command-design-patterns-classification` | what CATEGORY / what SIZE / what SHAPE (declarative template, WHAT-vs-HOW logic placement) | `~/.claude/skills/nw-command-design-patterns-classification/SKILL.md` |
| `nw-command-design-patterns-reduction` | what is REDUCIBLE / what to REMOVE / how far to COMPRESS (duplication triangle, anti-patterns, compression rules) | `~/.claude/skills/nw-command-design-patterns-reduction/SKILL.md` |
| `nw-command-design-patterns-authoring` | I am creating a NEW command — which FILES / what FORMAT (v2.8+ three-file install contract) | `~/.claude/skills/nw-command-design-patterns-authoring/SKILL.md` |

The three triggers partition the space: classification (size an existing command), reduction (trim a bloated one), authoring (lay out a new one). No overlap, no gap.

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
- [ ] Every `nw-ab-validation-checklist` item passes
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
