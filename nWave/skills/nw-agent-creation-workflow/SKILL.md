---
name: nw-agent-creation-workflow
description: "Guides agent creation through 5 phases: analyze, design, create, validate, refine. Use when building new Claude Code agents or restructuring existing agent definitions."
user-invocable: false
disable-model-invocation: true
---

# Agent Creation Workflow

## Overview

Create agents through 5 phases: ANALYZE -> DESIGN -> CREATE -> VALIDATE -> REFINE. Each phase has clear inputs, outputs, and quality gates. Follow "start minimal, add based on failure."

## Phase 1: ANALYZE

**Goal**: Understand requirements and determine agent architecture.

**Inputs**: User requirements, use case description, existing codebase context.

**Steps**:
1. Identify single clear responsibility
2. Determine new agent or modification of existing
3. Check overlap with existing agents (avoid duplication)
4. Classify agent type:
   - **Specialist**: Single-domain expert (most common)
   - **Reviewer**: Validates outputs from another agent (Reflection pattern)
   - **Orchestrator**: Coordinates multiple agents
5. Identify required tools (start with Read, Glob, Grep -- add only what's needed)
6. Determine if Skills needed (domain knowledge > 50 lines)

**Gate**: Single responsibility identified. Agent type classified. No overlap.

**Output**: Requirements summary with agent type, tools list, skill needs.

## Phase 2: DESIGN

**Goal**: Design agent architecture and structure.

**Inputs**: Requirements summary from Phase 1.

**Steps**:
1. Select design pattern (load `design-patterns` skill)
2. Define role and goal (1-2 sentences each)
3. Identify core principles that DIVERGE from Claude defaults:
   - What must this agent do differently than Claude naturally would?
   - Domain-specific methodology steps
   - Non-obvious constraints | Project-specific conventions
4. Design workflow (3-7 phases)
5. Plan Skills extraction: domain knowledge -> separate Skill | Testing/validation -> separate Skill | Keep workflow and principles in core agent
6. Design Skill Loading Strategy (required for 3+ skills):
   - Map each skill to the workflow phase where it's needed
   - Create a loading table: Phase → Skill → Trigger condition
   - Add explicit `Load: skill-name` directives in each workflow phase
   - Document path: `~/.claude/skills/nw-{skill-name}/SKILL.md` (installed) or `nWave/skills/nw-{skill-name}/SKILL.md` (repo)
   - Note: `skills:` in frontmatter is declarative only — Claude Code does NOT auto-load skill files. The agent must use Read tool to load them, triggered by `Load:` directives in workflow text.
7. Draft frontmatter:
   ```yaml
   ---
   name: {kebab-case-id}
   description: Use for {domain}. {When to delegate.}
   model: inherit
   tools: [{minimum tools needed}]
   maxTurns: 30
   skills:
     - nw-{skill-name}
   ---
   ```

**Gate**: Design fits ~200-300 lines (core) + Skills. Pattern selected. Frontmatter drafted.

**Output**: Agent architecture document (working notes, not deliverable).

## Phase 3: CREATE

**Goal**: Write agent definition file and Skills.

**Inputs**: Design from Phase 2.

**Steps**:
1. Create agent `.md` file:
   - YAML frontmatter (name, description, tools, model, maxTurns, skills)
   - Role + Goal paragraph
   - Core Principles (divergences only, 3-8 items)
   - Workflow phases
   - Critical Rules (3-5, where violation causes real harm)
   - Examples (3-5 canonical cases)
   - Subagent mode instructions
   - Constraints (what agent does NOT do)
2. Create Skill files if needed: each in `nWave/skills/{agent-name}/` | YAML frontmatter with `name` and `description` | Focused content, 100-250 lines each
3. Measure: `wc -l`. Target: under 300 lines.

4. Add Skill Loading Strategy section (required for agents with 3+ skills):
   ```markdown
   ## Skill Loading Strategy

   Load on-demand by phase, not all at once:

   | Phase | Load | Trigger |
   |-------|------|---------|
   | 1 Phase Name | `skill-name` | Always — core methodology |
   | 2 Phase Name | `other-skill` | When condition is met |

   Skills path: `~/.claude/skills/nw-{skill-name}/SKILL.md` (installed) or `nWave/skills/nw-{skill-name}/SKILL.md` (repo)
   ```
5. Add `Load:` directives at the start of each workflow phase referencing the applicable skills
6. Verify: every skill in frontmatter `skills:` has at least one `Load:` directive in the workflow text. Orphan skills (declared but never loaded) are a bug.

**Gate**: Agent file created. Under 300 lines. Skills created if needed. Skill Loading Strategy present for 3+ skills.

**Output**: Agent `.md` file + Skill files.

## Phase 4: VALIDATE

**Goal**: Verify agent meets quality standards.

**Steps**:
1. Run 14-point validation checklist:
   - [ ] Uses official YAML frontmatter format
   - [ ] Total definition under 400 lines (domain knowledge in Skills)
   - [ ] Only specifies behaviors diverging from Claude defaults
   - [ ] No aggressive signaling language
   - [ ] 3-5 canonical examples for critical behaviors
   - [ ] Tools restricted to minimum needed
   - [ ] maxTurns set in frontmatter
   - [ ] Safety via platform features, not prose
   - [ ] Instructions phrased affirmatively
   - [ ] Consistent terminology throughout
   - [ ] Description clearly states delegation criteria
2. Check anti-patterns: no monolithic sections (>50 lines without structure) | No duplicated Claude defaults | No embedded safety frameworks | No aggressive language
3. Test with representative inputs (Layer 1 testing)

**Gate**: All 14 items pass. No anti-patterns.

**Output**: Validation report (pass/fail per item).

## Phase 5: REFINE

**Goal**: Iteratively improve based on testing feedback.

**Steps**:
1. Address validation failures
2. Test with edge cases
3. Add instructions ONLY for observed failure modes: wrong decision -> add rule/example | Missed step -> clarify workflow | Over-generated -> add constraint
4. Re-measure: `wc -l`. If approaching 400 lines, extract to Skills.
5. Re-validate with 14-point checklist.

**Gate**: All validation passes. Line count within target. Edge cases handled.

**Output**: Final agent definition, ready for installation.

## Quality Gates Summary

| Phase | Gate | Blocks |
|-------|------|--------|
| ANALYZE | Single responsibility, no overlap | DESIGN |
| DESIGN | Architecture fits size target | CREATE |
| CREATE | File created, under 300 lines | VALIDATE |
| VALIDATE | 14-point checklist passes | REFINE/Deploy |
| REFINE | Edge cases handled, within target | Deploy |

## Naming Conventions

- Agent files: `nw-{name}.md` in `nWave/agents/`
- Skill files: `{skill-name}.md` in `nWave/skills/{agent-name}/`
- Reviewer agents: `nw-{name}-reviewer.md`
- Agent names in frontmatter: `nw-{name}` (kebab-case with nw- prefix)

## Reviewer Agent Creation (Special Case)

Reviewer agents pair with a primary agent and use the Reflection pattern:
1. Set `model: haiku` in frontmatter (cost-efficient review)
2. Use same tools as primary agent (no Write/Edit -- reviewers don't modify)
3. Define structured critique output format (YAML)
4. Include max 2 review iterations
5. Define clear approval/rejection criteria
