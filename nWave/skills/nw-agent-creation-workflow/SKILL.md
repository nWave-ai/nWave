---
name: nw-agent-creation-workflow
description: Detailed 5-phase workflow for creating agents - from requirements analysis through validation and iterative refinement
user-invocable: false
disable-model-invocation: true
---

# Agent Creation Workflow

## Overview

Create agents through 5 phases: ANALYZE -> DESIGN -> CREATE -> VALIDATE -> REFINE. Each phase has clear inputs, outputs, and quality gates. Follow "start minimal, add based on failure."

## Skill addressing

Classify every skill by how the role needs it:

1. **Always-needed knowledge** belongs in frontmatter `skills:`. The installer preloads each declared skill body once, so the agent body never tells the role to load, read or invoke it.
2. **Conditional knowledge** stays outside frontmatter. Use the source-aware procedure below to maintain one precise trigger in the generated conditional index; that index also carries the `[SKILL MISSING]` protocol.
3. No handwritten Skill Loading section, table or Load directive in agent bodies. An orphan is an unavailable declared asset or intended conditional knowledge with no reachable trigger, not a missing duplicate directive or an unavailable build-time registry in an installed project.
4. **Self-description in the skill itself** — the skill's `description` frontmatter states when to use it. Knowledge skills with `disable-model-invocation: true` are read on their trigger, never invoked through the Skill tool.

### Source-aware conditional-skill procedure

The registry and doc generator are framework build inputs, not installed-project capabilities. First identify the candidate as a framework source agent or an installed/generated artifact.

- **Framework source available:** establish the actual nWave source checkout and locate its existing `role-skill-loading.yaml` registry and `scripts/docgen.py`, alongside its agent and skill sources. Read the existing registry schema; declare the conditional skill once under its owning role with the precise trigger, then run `python scripts/docgen.py` from that checkout through a permitted execution capability. Inspect the resulting `GENERATED:role-skill-loading` region and referenced skill asset. This is the single conditional index; frontmatter preloads remain untouched.
- **Installed artifact only, or source/registry/generator capability missing:** report exactly which source or execution capability is unavailable. Continue the bounded review or design from the installed generated index and available skill files, but leave registration/regeneration unverified and return the proposed skill/trigger change for the source owner. Do not create a replacement registry in the user's project, hand-edit a generated region, or claim regeneration happened.
- **Review boundary:** judge whether the installed trigger is precise and its skill reachable. Lack of the undistributed registry alone is not evidence of a broken installed role. Source-provenance verification requires the actual source checkout; record that limit separately.

**GOOD vs BAD**:

| | Shape | Why |
|---|---|---|
| GOOD | source-aware registration followed by inspection of the generated conditional index | the trigger is authored in its real source and delivered once |
| GOOD | always-needed skill in frontmatter only | the installer preloads it once |
| BAD | frontmatter skill also reloaded by a body directive or table | duplicates already-loaded knowledge |
| BAD | handwritten Skill Loading section or table in the body | a second, drifting index beside the generated one |

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
1. Select a design pattern by applying the already-supplied `nw-design-patterns` knowledge
2. Define role and goal (1-2 sentences each)
3. Identify core principles that DIVERGE from Claude defaults:
   - What must this agent do differently than Claude naturally would?
   - Domain-specific methodology steps
   - Non-obvious constraints | Project-specific conventions
4. Design workflow (3-7 phases)
5. Plan Skills extraction: domain knowledge -> separate Skill | Testing/validation -> separate Skill | Keep workflow and principles in core agent
6. Design skill addressing:
   - Put only skills needed on every task in frontmatter; the installer preloads them once
   - For each conditional skill, plan a precise trigger and apply the source-aware conditional-skill procedure above
   - Plan no handwritten Skill Loading section, table or Load directive in the body
7. Draft frontmatter:
   ```yaml
   ---
   name: {kebab-case-id}
   description: Use for {domain}. {When to delegate.}
   model: inherit
   tools: [{minimum tools needed}]
   maxTurns: 40
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

4. Apply the source-aware conditional-skill procedure above for each conditional skill. Preserve the single generated index and report missing source or execution capability instead of manufacturing build inputs.
5. Verify: every frontmatter skill exists and is always needed; every intended conditional skill has a reachable precise trigger. Distinguish proposed changes from generated and inspected changes.

**Gate**: Authorized agent/skill changes delivered; conditional registration is either generated and inspected in the actual source checkout or explicitly pending its named source capability.

**Output**: Agent `.md` file + Skill files.

## Phase 4: VALIDATE

**Goal**: Verify agent meets quality standards.

**Steps**:
1. Run `nw-ab-validate-spec`: every item of `nw-ab-validation-checklist` plus the anti-pattern scan.
2. Test with representative inputs (Layer 1 testing)

**Gate**: Every checklist item passes. No anti-patterns.

**Output**: Validation report (pass/fail per item).

## Phase 5: REFINE

**Goal**: Iteratively improve based on testing feedback.

**Steps**:
1. Address validation failures
2. Test with edge cases
3. Add instructions ONLY for observed failure modes: wrong decision -> add rule/example | Missed step -> clarify workflow | Over-generated -> add constraint
4. Re-measure: `wc -l`. If approaching 400 lines, extract to Skills.
5. Re-validate with `nw-ab-validate-spec`.

**Gate**: All validation passes. Line count within target. Edge cases handled.

**Output**: Final agent definition, ready for installation.

## Quality Gates Summary

| Phase | Gate | Blocks |
|-------|------|--------|
| ANALYZE | Single responsibility, no overlap | DESIGN |
| DESIGN | Architecture fits size target | CREATE |
| CREATE | File created, under 300 lines | VALIDATE |
| VALIDATE | every `nw-ab-validation-checklist` item passes | REFINE/Deploy |
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
