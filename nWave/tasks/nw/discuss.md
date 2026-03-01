---
description: "Conducts Jobs-to-be-Done analysis, UX journey design, and requirements gathering through interactive discovery. Use when starting feature analysis, defining user stories, or creating acceptance criteria."
argument-hint: "[feature-name] - Optional: --phase=[jtbd|journey|requirements] --interactive=[high|moderate] --output-format=[md|yaml]"
---

# NW-DISCUSS: Jobs-to-be-Done Analysis, UX Journey Design, and Requirements Gathering

**Wave**: DISCUSS (wave 2 of 6) | **Agent**: Luna (nw-product-owner) | **Command**: `/nw:discuss`

## Overview

Execute DISCUSS wave through Luna's integrated workflow: JTBD analysis|UX journey discovery|emotional arc design|shared artifact tracking|requirements gathering|user story creation|acceptance criteria definition. Luna uncovers jobs users accomplish, maps to journeys and requirements, handles complete lifecycle from user motivations through DoR-validated stories ready for DESIGN. Establishes ATDD foundation.

For greenfield projects (no src/ code, no docs/feature/ history), Luna proposes Walking Skeleton as Feature 0.

## Interactive Decision Points

### Decision 1: Feature Type
**Question**: What type of feature is this?
**Options**:
1. User-facing -- UI/UX functionality visible to end users
2. Backend -- APIs, services, data processing
3. Infrastructure -- DevOps, CI/CD, tooling
4. Cross-cutting -- Spans multiple layers (auth, logging, etc.)
5. Other -- user provides custom input

### Decision 2: Walking Skeleton
**Question**: Should we start with a walking skeleton?
**Options**:
1. Yes -- recommended for greenfield projects
2. Depends -- brownfield; Luna evaluates existing structure first
3. No -- feature is isolated enough to skip

### Decision 3: UX Research Depth
**Question**: Priority for UX research depth?
**Options**:
1. Lightweight -- quick journey map, focus on happy path
2. Comprehensive -- full experience mapping with emotional arcs
3. Deep-dive -- extensive user research, multiple personas, edge cases

## Context Files Required

- docs/project-brief.md | docs/stakeholders.yaml | docs/architecture/constraints.md

## Previous Artifacts (Wave Handoff)

- docs/feature/{feature-id}/discover/problem-validation.md | opportunity-tree.md | lean-canvas.md — From DISCOVER

## Agent Invocation

@nw-product-owner

Execute *jtbd-analysis for {feature-id}, then *journey informed by JTBD artifacts, then *gather-requirements informed by both.

Context files: see Context Files Required and Previous Artifacts above.

**Configuration:**
- format: visual | yaml | gherkin | all (default: all)
- research_depth: {Decision 3} | interactive: high | output_format: markdown
- elicitation_depth: comprehensive | feature_type: {Decision 1}
- walking_skeleton: {Decision 2}
- output_directory: docs/feature/{feature-id}/discuss/

**Phase 1 -- Jobs-to-be-Done Analysis (REQUIRED):**

Grounds all subsequent artifacts in real user motivations.

1. **Job Discovery**: Ask user what users are trying to accomplish. Capture in job story format: "When [situation], I want to [motivation], so I can [outcome]."
2. **Job Dimensions**: For each job — functional (practical task)|emotional (desired feeling)|social (desired perception)
3. **Four Forces Analysis**: For each primary job:
   - **Push** (current frustration): "What frustrated users enough to request this?"
   - **Pull** (desired future): "What could they do that they cannot now?"
   - **Anxiety** (adoption concerns): "What concerns about adopting this?"
   - **Habit** (current behavior): "What behavior must change?"
   If interview transcripts|support tickets|analytics exist, extract forces from those instead of relying solely on user description.
4. **Opportunity Scoring** (multiple jobs): Rank by importance vs. satisfaction gap. High importance + low satisfaction = strongest opportunities. Produce scored table.
5. **JTBD-to-Story Bridge**: Each job story feeds into user stories and acceptance criteria in Phase 3. Every user story must trace to at least one job.

| Artifact | Path |
|----------|------|
| Job Stories | `docs/feature/{feature-id}/discuss/jtbd-job-stories.md` |
| Four Forces | `docs/feature/{feature-id}/discuss/jtbd-four-forces.md` |
| Opportunity Scores | `docs/feature/{feature-id}/discuss/jtbd-opportunity-scores.md` (when multiple jobs) |

**Phase 2 -- Journey Design:**

Luna runs deep discovery (mental model|emotional arc|shared artifacts|error paths) informed by JTBD, produces visual journey + YAML schema + Gherkin scenarios. Each journey maps to one or more identified jobs.

| Artifact | Path |
|----------|------|
| Visual Journey | `docs/feature/{feature-id}/discuss/journey-{name}-visual.md` |
| Journey Schema | `docs/feature/{feature-id}/discuss/journey-{name}.yaml` |
| Gherkin Scenarios | `docs/feature/{feature-id}/discuss/journey-{name}.feature` |
| Artifact Registry | `docs/feature/{feature-id}/discuss/shared-artifacts-registry.md` |

**Phase 3 -- Requirements and User Stories:**

Luna crafts LeanUX stories informed by JTBD + journey artifacts. Every story traces to at least one job story. Validates against DoR, invokes peer review, prepares handoff.

| Artifact | Path |
|----------|------|
| Requirements | `docs/feature/{feature-id}/discuss/requirements.md` |
| User Stories | `docs/feature/{feature-id}/discuss/user-stories.md` |
| Acceptance Criteria | `docs/feature/{feature-id}/discuss/acceptance-criteria.md` |
| DoR Checklist | `docs/feature/{feature-id}/discuss/dor-checklist.md` |

## Success Criteria

- [ ] JTBD analysis complete: all jobs in job story format
- [ ] Job dimensions identified: functional|emotional|social per job
- [ ] Four Forces mapped per job (push|pull|anxiety|habit)
- [ ] Opportunity scores produced (when multiple jobs)
- [ ] UX journey map with emotional arcs and shared artifacts
- [ ] Every journey maps to at least one job
- [ ] Discovery complete: user mental model understood, no vague steps
- [ ] Happy path defined: all steps start-to-goal with expected outputs
- [ ] Emotional arc coherent: confidence builds progressively
- [ ] Shared artifacts tracked: every ${variable} has single documented source
- [ ] Requirements completeness score > 0.95
- [ ] Every user story traces to at least one job story
- [ ] All acceptance criteria testable
- [ ] DoR passed: all 8 items validated with evidence
- [ ] Peer review approved
- [ ] Handoff accepted by nw-solution-architect (DESIGN wave)

## Next Wave

**Handoff To**: nw-solution-architect (DESIGN wave)
**Deliverables**: JTBD artifacts (job stories|four forces|opportunity scores) + journey artifacts (visual|YAML|Gherkin|artifact registry) + requirements (stories|acceptance criteria|DoR validation|peer review)

## Expected Outputs

```
docs/feature/{feature-id}/discuss/
  jtbd-job-stories.md
  jtbd-four-forces.md
  jtbd-opportunity-scores.md    (when multiple jobs)
  journey-{name}-visual.md
  journey-{name}.yaml
  journey-{name}.feature
  shared-artifacts-registry.md
  requirements.md
  user-stories.md               (each story traces to a job)
  acceptance-criteria.md
  dor-checklist.md
```

## Examples

### Example 1: User-facing feature with comprehensive UX research
```
/nw:discuss first-time-setup
```
Orchestrator asks Decision 1-3. User selects "User-facing", "No skeleton", "Comprehensive". Luna starts with JTBD analysis: discovers jobs like "When I first open the app, I want to feel productive immediately, so I can justify the purchase." Maps four forces for each job. Scores opportunities. Then runs journey discovery informed by JTBD, produces visual journey + YAML + Gherkin. Finally crafts stories where each traces to a job, validates DoR, and prepares handoff.

### Example 2: JTBD-only invocation
```
/nw:discuss --phase=jtbd onboarding-flow
```
Runs only Luna's JTBD analysis phase (job discovery + dimensions + four forces + opportunity scoring). Produces JTBD artifacts without proceeding to journey design or requirements. Useful for early discovery when you need to understand user motivations before committing to UX design.

### Example 3: Journey-only invocation
```
/nw:discuss --phase=journey release-nwave
```
Runs only Luna's journey design phases (discovery + visualization + coherence validation). Produces journey artifacts without proceeding to requirements crafting. Useful when JTBD is already done and journey design needs standalone iteration.

### Example 4: Requirements-only invocation
```
/nw:discuss --phase=requirements new-plugin-system
```
Runs only Luna's requirements phases (gathering + crafting + DoR validation). Assumes JTBD and journey artifacts already exist or are not needed (e.g., backend feature).
