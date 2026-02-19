---
description: "Gathers knowledge from web and files, cross-references across multiple sources, and produces cited research documents. Use when investigating technologies, patterns, or decisions that need evidence backing."
argument-hint: '[topic] - Optional: --research_depth=[overview|detailed|comprehensive|deep-dive] --skill-for=[agent-name]'
---

# NW-RESEARCH: Evidence-Driven Knowledge Research

**Wave**: CROSS_WAVE
**Agent**: Nova (nw-researcher)
**Command**: `*research`

## Overview

Execute systematic evidence-based research with source verification. Cross-wave support providing research-backed insights for any nWave phase using trusted academic, official, and industry sources.

Optional `--skill-for={agent-name}` flag distills research into a practitioner-focused skill file for a specific agent.

## Context Files Required

- ~/.claude/nWave/data/config/trusted-source-domains.yaml - Source reputation validation

## Agent Invocation

@nw-researcher

Execute \*research on {topic} [--skill-for={agent-name}].

**Context Files:**

- ~/.claude/nWave/data/config/trusted-source-domains.yaml

**Configuration:**

- research_depth: detailed # overview/detailed/comprehensive/deep-dive
- source_preferences: ["academic", "official", "technical_docs"]
- output_directory: docs/research/
- skill_for: {agent-name} # Optional: distilled skill for specified agent
- skill_output_directory: ~/.claude/nWave/skills/{agent-name}/

## Success Criteria

Refer to Nova's quality gates in ~/.claude/agents/nw/nw-researcher.md.

**Research:**

- [ ] All sources from trusted-source-domains.yaml
- [ ] Cross-reference performed (3+ sources per major claim)
- [ ] Research file created in docs/research/
- [ ] Citation coverage > 95%
- [ ] Average source reputation >= 0.80

**Distillation (if --skill-for specified):**

- [ ] Skill file created in ~/.claude/nWave/skills/{agent-name}/
- [ ] 100% essential concepts preserved
- [ ] Self-contained with no external references
- [ ] Token budget respected (<5000 tokens per skill)

## Next Wave

**Handoff To**: Invoking workflow
**Deliverables**: Research document + optional skill file

## Examples

### Example 1: Standalone research
```
/nw:research "event sourcing patterns" --research_depth=detailed
```
Nova researches event sourcing from trusted sources, cross-references 3+ sources per claim, produces a comprehensive research document.

### Example 2: Research with agent skill
```
/nw:research "mutation testing methodologies" --skill-for=software-crafter
```
Nova researches mutation testing, then distills findings into a practitioner-focused skill file at ~/.claude/nWave/skills/software-crafter/.

## Expected Outputs

```
data/research/{category}/{topic}-comprehensive-research.md
~/.claude/nWave/skills/{agent}/{topic}-methodology.md    (if --skill-for)
```
