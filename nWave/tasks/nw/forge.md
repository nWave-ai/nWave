---
description: "Creates new specialized agents using the 5-phase workflow (ANALYZE > DESIGN > CREATE > VALIDATE > REFINE). Use when building a new AI agent or validating an existing agent specification."
argument-hint: '[agent-name] - Optional: --type=[specialist|reviewer|orchestrator] --pattern=[react|reflection|router]'
---

# NW-FORGE: Create Agent (V2)

**Wave**: CROSS_WAVE
**Agent**: Zeus (nw-agent-builder)

## Overview

Create a new agent using the research-validated v2 approach: focused core (200-400 lines) with Skills for domain knowledge. Follows the 5-phase workflow: ANALYZE > DESIGN > CREATE > VALIDATE > REFINE.

## Agent Invocation

@nw-agent-builder

Execute \*forge to create {agent-name} agent.

**Configuration:**

- agent_type: specialist | reviewer | orchestrator
- design_pattern: react | reflection | router | planning | sequential | parallel | hierarchical

## Success Criteria

- [ ] Agent definition under 400 lines (`wc -l`)
- [ ] Official YAML frontmatter format (name, description, tools, maxTurns)
- [ ] 11-point validation checklist passes
- [ ] Only divergent behaviors specified (no Claude defaults)
- [ ] 3-5 canonical examples included
- [ ] Domain knowledge extracted to Skills if >50 lines
- [ ] No aggressive language (no CRITICAL/MANDATORY/ABSOLUTE)
- [ ] Safety via platform features (frontmatter/hooks), not prose

## Next Wave

**Handoff To**: Agent installation and deployment
**Deliverables**: Agent specification file + Skill files (if any)

## Expected Outputs

```
~/.claude/agents/nw/nw-{agent-name}.md
~/.claude/skills/nw/{agent-name}/*.md    (if Skills needed)
```
