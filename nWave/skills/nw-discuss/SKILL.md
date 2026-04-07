---
name: nw-discuss
description: "Conducts Jobs-to-be-Done analysis, UX journey design, and requirements gathering through interactive discovery. Use when starting feature analysis, defining user stories, or creating acceptance criteria."
user-invocable: true
argument-hint: '[feature-name] - Optional: --phase=[jtbd|journey|requirements] --interactive=[high|moderate] --output-format=[md|yaml]'
---

# NW-DISCUSS: Jobs-to-be-Done Analysis, UX Journey Design, and Requirements Gathering

**Wave**: DISCUSS (wave 2 of 6) | **Agent**: Luna (nw-product-owner) | **Command**: `/nw-discuss`

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

### Decision 4: JTBD Analysis
**Question**: Include Jobs-to-be-Done analysis?
**Options**:
1. Yes -- recommended when user motivations are unclear or multiple jobs compete
2. No -- skip JTBD, proceed directly to journey design (default)

## Prior Wave Consultation

Before beginning DISCUSS work, read SSOT and prior wave artifacts:

1. **SSOT** (if `docs/product/` exists):
   - `docs/product/journeys/{name}.yaml` — existing journey to extend (if applicable)
   - `docs/product/jobs.yaml` — validated jobs and opportunity scores
   - `docs/product/vision.md` — product vision
2. **Project context**: `docs/project-brief.md` | `docs/stakeholders.yaml`
3. **DISCOVER artifacts**: Read `docs/feature/{feature-id}/discover/` (if present)
4. **DIVERGE artifacts**: Read `docs/feature/{feature-id}/diverge/recommendation.md` and `job-analysis.md` (if present — job is already validated, do not re-run JTBD)

**Migration gate**: If `docs/product/` does not exist but `docs/feature/` has existing features, STOP. The project has old-model features that should be migrated to SSOT before new waves run. Guide the user to `docs/guides/migrating-to-ssot-model/README.md` and complete the migration first. If `docs/product/` does not exist and no old features exist (greenfield), DISCUSS will bootstrap it.

DISCUSS follows DISCOVER and optionally DIVERGE — reading SSOT first ensures continuity with prior features, then prior wave artifacts ground requirements in evidence.

**READING ENFORCEMENT**: You MUST read every file listed in Prior Wave Consultation above using the Read tool before proceeding. After reading, output a confirmation checklist (`✓ {file}` for each read, `⊘ {file} (not found)` for missing). Do NOT skip files that exist — skipping causes requirements disconnected from evidence.

After reading, check whether any DISCUSS decisions would contradict DISCOVER evidence. Flag contradictions and resolve with user before proceeding. Example: DISCOVER found "users don't want automation" but DISCUSS story assumes "automated workflow" — this must be resolved.

## Document Update (Back-Propagation)

When DISCUSS decisions change assumptions established in DISCOVER:
1. Document the change in a `## Changed Assumptions` section at the end of the affected DISCUSS artifact
2. Reference the original DISCOVER document and quote the original assumption
3. State the new assumption and the rationale for the change
4. Do NOT modify DISCOVER documents directly — they represent historical evidence

## Agent Invocation

@nw-product-owner

IF Decision 4 = Yes: Execute *jtbd-analysis for {feature-id}, then *journey informed by JTBD artifacts, then *story-map, then *gather-requirements with outcome KPIs.
IF Decision 4 = No (default): Execute *journey for {feature-id}, then *story-map, then *gather-requirements with outcome KPIs.

Context files: see Prior Wave Consultation above + project context files.

**Configuration:**
- format: visual | yaml | gherkin | all (default: all)
- research_depth: {Decision 3} | interactive: high | output_format: markdown
- elicitation_depth: comprehensive | feature_type: {Decision 1}
- walking_skeleton: {Decision 2}
- output_directory: docs/feature/{feature-id}/discuss/

**Phase 1 -- Jobs-to-be-Done Analysis (OPTIONAL -- when Decision 4 = Yes):**

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

**Phase 2.5 -- User Story Mapping:**
Luna loads `user-story-mapping` skill before this phase.

Organizes discovered stories into a visual story map (backbone → walking skeleton → incremental slices). Produces prioritization suggestions based on outcomes identified in earlier phases.

1. **Backbone**: Map user activities (big steps) horizontally across the top
2. **Walking Skeleton**: Identify minimum slice that delivers end-to-end value
3. **Release Slices**: Group stories into outcome-based releases
4. **Prioritization**: Suggest priority order based on outcome impact and dependencies

| Artifact | Path |
|----------|------|
| Story Map | `docs/feature/{feature-id}/discuss/story-map.md` |
| Prioritization | `docs/feature/{feature-id}/discuss/prioritization.md` |

**Phase 3 -- Requirements and User Stories:**

Luna crafts LeanUX stories informed by JTBD + journey artifacts. Every story traces to at least one job story. Validates against DoR, invokes peer review, prepares handoff.

| Artifact | Path |
|----------|------|
| User Stories (includes requirements + embedded AC) | `docs/feature/{feature-id}/discuss/user-stories.md` |
| DoR Validation | `docs/feature/{feature-id}/discuss/dor-validation.md` |
| Outcome KPIs | `docs/feature/{feature-id}/discuss/outcome-kpis.md` |

## Success Criteria

- [ ] (when JTBD selected) JTBD analysis complete: all jobs in job story format
- [ ] (when JTBD selected) Job dimensions identified: functional|emotional|social per job
- [ ] (when JTBD selected) Four Forces mapped per job (push|pull|anxiety|habit)
- [ ] (when JTBD selected) Opportunity scores produced (when multiple jobs)
- [ ] UX journey map with emotional arcs and shared artifacts
- [ ] (when JTBD selected) Every journey maps to at least one job
- [ ] Discovery complete: user mental model understood, no vague steps
- [ ] Happy path defined: all steps start-to-goal with expected outputs
- [ ] Emotional arc coherent: confidence builds progressively
- [ ] Shared artifacts tracked: every ${variable} has single documented source
- [ ] Story map created with backbone, walking skeleton, and release slices
- [ ] Outcome KPIs defined with measurable targets
- [ ] Prioritization suggestions based on outcome impact
- [ ] Requirements completeness score > 0.95
- [ ] (when JTBD selected) Every user story traces to at least one job story
- [ ] All acceptance criteria testable
- [ ] DoR passed: all 9 items validated with evidence
- [ ] Peer review approved
- [ ] Handoff accepted by nw-solution-architect (DESIGN wave)

## Next Wave

**Handoff To**: nw-solution-architect (DESIGN wave) + nw-platform-architect (DEVOPS wave, KPIs only)
**Deliverables**: User stories + story map + outcome KPIs + SSOT journey/jobs updates | JTBD artifacts (when selected)

DISCUSS hands off to BOTH DESIGN (full artifacts) and DEVOPS (outcome-kpis.md only). DEVOPS and DESIGN can proceed in parallel — DESIGN receives the complete artifact set while DEVOPS receives only the KPI file to drive observability and instrumentation design.

## Wave Decisions Summary

Before completing DISCUSS, produce `docs/feature/{feature-id}/discuss/wave-decisions.md`:

```markdown
# DISCUSS Decisions — {feature-id}

## Key Decisions
- [D1] {decision}: {rationale} (see: {source-file})

## Requirements Summary
- Primary jobs/user needs: {1-3 sentence summary}
- Walking skeleton scope: {if applicable}
- Feature type: {user-facing|backend|infrastructure|cross-cutting}

## Constraints Established
- {constraint from requirements analysis}

## Upstream Changes
- {any DISCOVER assumptions changed, with rationale}
```

This summary enables DESIGN to quickly assess DISCUSS outcomes. DESIGN reads this plus key artifacts (user-stories.md, story-map.md, outcome-kpis.md) rather than all DISCUSS files.

## Expected Outputs

```
docs/feature/{feature-id}/discuss/     (feature delta)
  user-stories.md               (requirements + embedded AC, each story traces to a job)
  story-map.md
  dor-validation.md
  outcome-kpis.md
  wave-decisions.md

docs/product/                          (SSOT updates)
  journeys/{name}.yaml          (create or extend journey schema)
  journeys/{name}-visual.md     (human-readable journey narrative)
  jobs.yaml                     (add validated job if new)
```

## Examples

### Example 1: User-facing feature with comprehensive UX research
```
/nw-discuss first-time-setup
```
Orchestrator asks Decision 1-3. User selects "User-facing", "No skeleton", "Comprehensive". Luna starts with JTBD analysis: discovers jobs like "When I first open the app, I want to feel productive immediately, so I can justify the purchase." Maps four forces for each job. Scores opportunities. Then runs journey discovery informed by JTBD, produces visual journey + YAML + Gherkin. Finally crafts stories where each traces to a job, validates DoR, and prepares handoff.

### Example 2: JTBD-only invocation
```
/nw-discuss --phase=jtbd onboarding-flow
```
Runs only Luna's JTBD analysis phase (job discovery + dimensions + four forces + opportunity scoring). Produces JTBD artifacts without proceeding to journey design or requirements. Useful for early discovery when you need to understand user motivations before committing to UX design.

### Example 3: Journey-only invocation
```
/nw-discuss --phase=journey release-nwave
```
Runs only Luna's journey design phases (discovery + visualization + coherence validation). Produces journey artifacts without proceeding to requirements crafting. Useful when JTBD is already done and journey design needs standalone iteration.

### Example 4: Requirements-only invocation
```
/nw-discuss --phase=requirements new-plugin-system
```
Runs only Luna's requirements phases (gathering + crafting + DoR validation). Assumes JTBD and journey artifacts already exist or are not needed (e.g., backend feature).
