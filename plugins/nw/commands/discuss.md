---
description: "Conducts Jobs-to-be-Done analysis, UX journey design, and requirements gathering through interactive discovery. Use when starting feature analysis, defining user stories, or creating acceptance criteria."
argument-hint: "[feature-name] - Optional: --phase=[jtbd|journey|requirements] --interactive=[high|moderate] --output-format=[md|yaml]"
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

## Prior Wave Consultation

Before beginning DISCUSS work, read SSOT and prior wave artifacts:

1. **SSOT** (if `docs/product/` exists):
   - `docs/product/journeys/{name}.yaml` — existing journey to extend (if applicable)
   - `docs/product/jobs.yaml` — validated jobs and opportunity scores
   - `docs/product/vision.md` — product vision
2. **Project context**: `docs/project-brief.md` | `docs/stakeholders.yaml`
3. **DISCOVER artifacts**: Read `docs/feature/{feature-id}/discover/` (if present)
4. **DIVERGE artifacts**: Read `docs/feature/{feature-id}/diverge/` (if present)
   - `recommendation.md` is the primary input — the selected design direction and job statement
   - `job-analysis.md` — validated JTBD job statements and ODI outcome statements — use directly, do not re-run JTBD analysis

DISCUSS is the convergence wave — it takes the direction from DIVERGE (or a direct decision) and transforms it into UX journeys and testable requirements.

If `docs/product/` does not exist, this is the first feature using the SSOT model. DISCUSS will create it (see SSOT Update below).

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

IF DIVERGE artifacts present (`docs/feature/{feature-id}/diverge/recommendation.md` exists):
  Read `recommendation.md` and `job-analysis.md` to ground journey design|execute *journey for {feature-id} informed by DIVERGE direction|then *story-map|then *gather-requirements with outcome KPIs.
ELSE:
  Execute *journey for {feature-id}|then *story-map|then *gather-requirements with outcome KPIs.

Context files: see Prior Wave Consultation above + project context files.

**Configuration:**
- format: visual | yaml | gherkin | all (default: all)
- research_depth: {Decision 3} | interactive: high | output_format: markdown
- elicitation_depth: comprehensive | feature_type: {Decision 1}
- walking_skeleton: {Decision 2}
- output_directory: docs/feature/{feature-id}/discuss/

**Phase 1 -- Job Grounding (from DIVERGE artifacts):**

If DIVERGE artifacts are present, read `recommendation.md` and `job-analysis.md` before any journey work.
Extract: the selected design direction|the validated job statement|ODI outcome statements.
These ground all subsequent journey and story work — every story must trace to the job from DIVERGE.

If no DIVERGE artifacts: journey design proceeds without a pre-validated job. Note this as a risk in `wave-decisions.md`.

**Phase 2 -- Journey Design:**

Luna runs deep discovery (mental model|emotional arc|shared artifacts|error paths) informed by JTBD, produces visual journey + YAML schema + Gherkin scenarios. Each journey maps to one or more identified jobs.

| Artifact | Path |
|----------|------|
| Visual Journey | `docs/feature/{feature-id}/discuss/journey-{name}-visual.md` |
| Journey Schema | `docs/feature/{feature-id}/discuss/journey-{name}.yaml` (includes Gherkin per step — DISTILL extracts at wave start) |
| Artifact Registry | `docs/feature/{feature-id}/discuss/shared-artifacts-registry.md` |

**Phase 2.5 -- User Story Mapping:**
Luna loads `user-story-mapping` skill before this phase.

Organizes discovered stories into a visual story map (backbone → walking skeleton → incremental slices). Produces prioritization suggestions based on outcomes identified in earlier phases.

1. **Backbone**: Map user activities (big steps) horizontally across the top
2. **Walking Skeleton**: Identify minimum slice that delivers end-to-end value
3. **Release Slices**: Group stories into outcome-based releases
4. **Priority Rationale**: Suggest priority order based on outcome impact and dependencies (included as `## Priority Rationale` section in story-map.md)

| Artifact | Path |
|----------|------|
| Story Map (includes Priority Rationale) | `docs/feature/{feature-id}/discuss/story-map.md` |

**Phase 3 -- User Stories:**

Luna crafts LeanUX stories informed by JTBD + journey artifacts. Every story traces to at least one job story. System constraints go in `## System Constraints` section at the top of user-stories.md. Validates against DoR, invokes peer review, prepares handoff.

| Artifact | Path |
|----------|------|
| User Stories (includes System Constraints + AC per story) | `docs/feature/{feature-id}/discuss/user-stories.md` |
| DoR Validation | `docs/feature/{feature-id}/discuss/dor-validation.md` |
| Outcome KPIs | `docs/feature/{feature-id}/discuss/outcome-kpis.md` |

## Success Criteria

- [ ] (when DIVERGE artifacts present) DIVERGE recommendation read and direction confirmed before journey design
- [ ] UX journey map with emotional arcs and shared artifacts
- [ ] (when DIVERGE artifacts present) Every journey maps to the job from DIVERGE job-analysis.md
- [ ] Discovery complete: user mental model understood, no vague steps
- [ ] Happy path defined: all steps start-to-goal with expected outputs
- [ ] Emotional arc coherent: confidence builds progressively
- [ ] Shared artifacts tracked: every ${variable} has single documented source
- [ ] Story map created with backbone, walking skeleton, release slices, and priority rationale
- [ ] Outcome KPIs defined with measurable targets
- [ ] (when DIVERGE artifacts present) Every user story traces to the validated job from DIVERGE
- [ ] All UAT scenarios testable (AC derived from scenarios, embedded in user-stories.md)
- [ ] DoR passed: all 9 items validated with evidence
- [ ] Peer review approved
- [ ] Handoff accepted by nw-solution-architect (DESIGN wave)

## Next Wave

**Handoff To**: nw-solution-architect (DESIGN wave) + nw-platform-architect (DEVOPS wave, KPIs only)
**Deliverables**: Journey artifacts (visual + YAML) + story map (with priority rationale) + user-stories + outcome KPIs

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

## SSOT Update

After producing feature-level artifacts, update the product-level SSOT:

1. **Journey SSOT**: If journey is new, create `docs/product/journeys/{name}.yaml` + `{name}-visual.md`. If journey exists, update it with new/changed steps and add a changelog entry.
2. **Jobs SSOT**: If DIVERGE produced a validated job, ensure it is in `docs/product/jobs.yaml`. If `jobs.yaml` does not exist, create it.

If `docs/product/` does not exist, create the directory structure. This is the SSOT bootstrap — first wave initializes it.

SSOT files use `schema_version` and `changelog` fields. See canonical schemas in the design-methodology skill.

## Expected Outputs

### Feature delta (in `docs/feature/{feature-id}/discuss/`)
```
  user-stories.md               (includes ## System Constraints + ## Impacted Journeys + AC per story)
  story-map.md                  (includes ## Priority Rationale)
  dor-validation.md
  outcome-kpis.md
  wave-decisions.md
```

### SSOT updates (in `docs/product/`)
```
  journeys/{name}.yaml          (created or updated + changelog entry)
  journeys/{name}-visual.md     (created or updated)
  jobs.yaml                     (updated with validated jobs, if DIVERGE ran)
```

### Internal artifacts (produced but not persisted as standalone files)
```
  shared-artifacts-registry.md  (used during coherence validation, content folded into journey.yaml shared_artifacts)
```

## Examples

### Example 1: User-facing feature after DIVERGE wave
```
/nw-discuss first-time-setup
```
Orchestrator detects DIVERGE artifacts present. Reads `recommendation.md` — direction is "proactive push notification on workflow failure". Luna reads `job-analysis.md` for the validated job statement. Runs journey discovery informed by the selected direction, produces visual journey + YAML. Crafts stories where each traces to the DIVERGE job, validates DoR, prepares handoff.

### Example 2: Feature without DIVERGE
```
/nw-discuss new-monitoring-feature
```
No DIVERGE artifacts found. Luna proceeds with discovery conversation from scratch, notes the absence of a pre-validated job in `wave-decisions.md` as a risk.

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
