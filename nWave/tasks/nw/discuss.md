---
description: "Conducts UX journey design and requirements gathering through interactive discovery. Use when starting feature analysis, defining user stories, or creating acceptance criteria."
argument-hint: "[feature-name] - Optional: --phase=[journey|requirements] --interactive=[high|moderate] --output-format=[md|yaml]"
---

# NW-DISCUSS: Requirements Gathering and UX Journey Design

**Wave**: DISCUSS (wave 2 of 6)
**Agent**: Luna (nw-product-owner)
**Command**: `/nw:discuss`

## Overview

Execute DISCUSS wave through Luna's integrated workflow: UX journey discovery, emotional arc design, shared artifact tracking, requirements gathering, user story creation, and acceptance criteria definition. Luna handles the complete lifecycle from understanding the user's mental model through to DoR-validated stories ready for DESIGN wave. Establishes ATDD foundation for subsequent waves.

For greenfield projects (no src/ code, no docs/feature/ history), Luna proposes a Walking Skeleton as Feature 0 to validate architecture end-to-end before functional features.

## Interactive Decision Points

Before proceeding, the orchestrator asks the user:

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

- docs/project-brief.md - Project context and objectives
- docs/stakeholders.yaml - Stakeholder identification and roles
- docs/architecture/constraints.md - Technical and business constraints

## Previous Artifacts (Wave Handoff)

- docs/discovery/problem-validation.md - From DISCOVER wave
- docs/discovery/opportunity-tree.md - From DISCOVER wave
- docs/discovery/lean-canvas.md - From DISCOVER wave

## Agent Invocation

@nw-product-owner

Execute *journey for {feature-name}, then *gather-requirements informed by journey artifacts.

Context files: see Context Files Required and Previous Artifacts above.

**Configuration:**

- format: visual | yaml | gherkin | all (default: all)
- research_depth: {from Decision 3}
- interactive: high
- output_format: markdown
- elicitation_depth: comprehensive
- feature_type: {from Decision 1}
- walking_skeleton: {from Decision 2}
- output_directory: docs/ux/{epic}/ (journeys), docs/requirements/ (stories)

**Phase 1 -- Journey Design:**

Luna runs deep discovery (questioning the user's mental model, emotional arc, shared artifacts, error paths), then produces visual journey + YAML schema + Gherkin scenarios.

| Artifact | Path |
|----------|------|
| Visual Journey | `docs/ux/{epic}/journey-{name}-visual.md` |
| Journey Schema | `docs/ux/{epic}/journey-{name}.yaml` |
| Gherkin Scenarios | `docs/ux/{epic}/journey-{name}.feature` |
| Artifact Registry | `docs/ux/{epic}/shared-artifacts-registry.md` |

**Phase 2 -- Requirements and User Stories:**

Luna crafts LeanUX user stories informed by her journey artifacts. Validates against DoR, invokes peer review, and prepares handoff package.

| Artifact | Path |
|----------|------|
| Requirements | `docs/requirements/requirements.md` |
| User Stories | `docs/requirements/user-stories.md` |
| Acceptance Criteria | `docs/requirements/acceptance-criteria.md` |
| DoR Checklist | `docs/requirements/dor-checklist.md` |

## Success Criteria

- [ ] UX journey map complete with emotional arcs and shared artifacts
- [ ] Discovery complete: user mental model understood, no vague steps
- [ ] Happy path defined: all steps from start to goal with expected outputs
- [ ] Emotional arc coherent: confidence builds progressively, no jarring transitions
- [ ] Shared artifacts tracked: every ${variable} has a single documented source
- [ ] Requirements completeness score > 0.95
- [ ] All acceptance criteria testable
- [ ] DoR passed: all 8 items validated with evidence
- [ ] Peer review approved
- [ ] Handoff accepted by solution-architect (DESIGN wave)

## Next Wave

**Handoff To**: nw-solution-architect (DESIGN wave)
**Deliverables**: Luna's complete package -- journey artifacts (visual, YAML, Gherkin, artifact registry) + requirements (stories, acceptance criteria, DoR validation, peer review approval)

## Expected Outputs

```
docs/ux/{epic}/
  journey-{name}-visual.md
  journey-{name}.yaml
  journey-{name}.feature
  shared-artifacts-registry.md

docs/requirements/
  requirements.md
  user-stories.md
  acceptance-criteria.md
  dor-checklist.md
```

## Examples

### Example 1: User-facing feature with comprehensive UX research
```
/nw:discuss first-time-setup
```
Orchestrator asks Decision 1-3. User selects "User-facing", "No skeleton", "Comprehensive". Luna runs full discovery: asks about mental model, emotional arc, shared artifacts. Produces visual journey + YAML + Gherkin. Then Luna crafts stories informed by those journey artifacts, validates DoR, and prepares handoff.

### Example 2: Journey-only invocation
```
/nw:discuss --phase=journey release-nwave
```
Runs only Luna's journey design phases (discovery + visualization + coherence validation). Produces journey artifacts without proceeding to requirements crafting. Useful when journey design needs standalone iteration.

### Example 3: Requirements-only invocation
```
/nw:discuss --phase=requirements new-plugin-system
```
Runs only Luna's requirements phases (gathering + crafting + DoR validation). Assumes journey artifacts already exist or are not needed (e.g., backend feature).
