---
name: agent-creation-workflow
description: Detailed 5-phase workflow for creating agents - from requirements analysis through validation and iterative refinement
---

# Agent Creation Workflow

## Overview

Create agents through 5 phases: ANALYZE -> DESIGN -> CREATE -> VALIDATE -> REFINE.

Each phase has clear inputs, outputs, and quality gates. The workflow follows the "start minimal, add based on failure" principle.

## Phase 1: ANALYZE

**Goal**: Understand requirements and determine the right agent architecture.

**Inputs**: User requirements, use case description, existing codebase context.

**Steps**:
1. Identify the agent's single clear responsibility
2. Determine if this is a new agent or modification of existing
3. Check for overlap with existing agents (avoid duplication)
4. Classify agent type:
   - **Specialist**: Single-domain expert (most common)
   - **Reviewer**: Validates outputs from another agent (uses Reflection pattern)
   - **Orchestrator**: Coordinates multiple agents
5. Identify required tools (start with Read, Glob, Grep — add only what's needed)
6. Determine if Skills are needed (domain knowledge > 50 lines)

**Gate**: Single responsibility identified. Agent type classified. No overlap with existing agents.

**Output**: Requirements summary with agent type, tools list, and skill needs.

## Phase 2: DESIGN

**Goal**: Design the agent's architecture and structure.

**Inputs**: Requirements summary from Phase 1.

**Steps**:
1. Select design pattern (load `design-patterns` skill for decision tree)
2. Define the role and goal (1-2 sentences each)
3. Identify core principles that DIVERGE from Claude defaults:
   - What must this agent do differently than Claude would naturally?
   - Domain-specific methodology steps
   - Non-obvious constraints
   - Project-specific conventions
4. Design the workflow (3-7 phases)
5. Plan Skills extraction:
   - Domain knowledge -> separate Skill file
   - Testing/validation details -> separate Skill file
   - Keep workflow and principles in core agent
6. Draft frontmatter configuration:
   ```yaml
   ---
   name: {kebab-case-id}
   description: Use for {domain}. {When to delegate.}
   model: inherit
   tools: [{minimum tools needed}]
   maxTurns: 30
   skills:
     - {skill-name}
   ---
   ```

**Gate**: Design fits in ~200-300 lines (core) + Skills. Pattern selected. Frontmatter drafted.

**Output**: Agent architecture document (informal, working notes — not a deliverable).

## Phase 3: CREATE

**Goal**: Write the agent definition file and any Skills.

**Inputs**: Design from Phase 2.

**Steps**:
1. Create the agent `.md` file following the template:
   - YAML frontmatter (name, description, tools, model, maxTurns, skills)
   - Role + Goal paragraph
   - Core Principles (divergences only, 3-8 items)
   - Workflow phases
   - Critical Rules (3-5, where violation causes real harm)
   - Examples (3-5 canonical cases)
   - Subagent mode instructions
   - Constraints (what the agent does NOT do)
2. Create Skill files if needed:
   - Each in `nWave/skills/{agent-name}/`
   - YAML frontmatter with `name` and `description`
   - Focused content, 100-250 lines each
3. Measure: `wc -l` the definition. Target: under 300 lines.

**Gate**: Agent file created. Line count under 300. Skills created if needed.

**Output**: Agent `.md` file + Skill files.

## Phase 4: VALIDATE

**Goal**: Verify the agent meets quality standards.

**Inputs**: Agent file from Phase 3.

**Steps**:
1. Run the 11-point validation checklist:
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
2. Check anti-patterns:
   - No monolithic sections (>50 lines without structure)
   - No duplicated Claude default behaviors
   - No embedded safety frameworks
   - No aggressive language
3. Test with representative inputs (Layer 1 testing)

**Gate**: All 11 checklist items pass. No anti-patterns found.

**Output**: Validation report (pass/fail per item).

## Phase 5: REFINE

**Goal**: Iteratively improve based on testing feedback.

**Inputs**: Validation results from Phase 4, test observations.

**Steps**:
1. Address any validation failures
2. Test the agent with edge cases
3. Add instructions ONLY for observed failure modes:
   - Agent made wrong decision? Add a rule or example.
   - Agent missed a step? Clarify workflow.
   - Agent over-generated? Add a constraint.
4. Re-measure: `wc -l`. If approaching 400 lines, extract to Skills.
5. Re-validate with the 11-point checklist.

**Gate**: All validation items pass. Line count within target. Agent handles edge cases.

**Output**: Final agent definition, ready for installation.

## Quality Gates Summary

| Phase | Gate | Blocks |
|-------|------|--------|
| ANALYZE | Single responsibility, no overlap | DESIGN |
| DESIGN | Architecture fits size target | CREATE |
| CREATE | File created, under 300 lines | VALIDATE |
| VALIDATE | 11-point checklist passes | REFINE/Deploy |
| REFINE | Edge cases handled, still within target | Deploy |

## Naming Conventions

- Agent files: `nw-{name}.md` in `nWave/agents/`
- Skill files: `{skill-name}.md` in `nWave/skills/{agent-name}/`
- Reviewer agents: `nw-{name}-reviewer.md`
- Agent names in frontmatter: `nw-{name}` (kebab-case with nw- prefix)

## Reviewer Agent Creation (Special Case)

Reviewer agents pair with a primary agent and use the Reflection pattern:

1. Set `model: haiku` in frontmatter (cost-efficient review)
2. Use same tools as the primary agent (no Write/Edit — reviewers don't modify)
3. Define structured critique output format (YAML)
4. Include max 2 review iterations
5. Define clear approval/rejection criteria
