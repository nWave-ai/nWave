---
name: nw-diverge
description: "Generates 3-5 divergent design directions through JTBD analysis, competitive research, structured brainstorming, and taste evaluation before convergence. Use when the team has a validated problem but hasn't chosen a solution approach."
user-invocable: true
argument-hint: '[feature-id] - Optional: --work-type=[new-product|brownfield|pivot]'
---

# NW-DIVERGE: Structured Divergent Thinking Before Convergence

**Wave**: DIVERGE (between DISCOVER and DISCUSS, optional) | **Agent**: Flux (nw-diverger) | **Command**: `/nw-diverge`

## Overview

Execute DIVERGE wave through Flux's 4-phase workflow: JTBD analysis|competitive research|structured brainstorming|taste-filtered evaluation. Transforms a validated problem into 3-5 concrete, taste-scored design directions so DISCUSS can converge on one with confidence.

DIVERGE is optional. Brownfield features with a clear direction may skip it (see skip checklist in design spec). New products and pivot decisions benefit most from structured divergence.

## Interactive Decision Points

### Decision 1: Work Type
**Question**: What type of work is this?
**Options**:
1. New product -- no prior solution exists, full divergence needed
2. Brownfield feature -- existing product, exploring approach alternatives
3. Pivot / redesign -- existing feature being reconsidered from scratch
4. Other -- user provides custom context

### Decision 2: Research Depth
**Question**: How deep should competitive research go?
**Options**:
1. Lightweight -- 3 competitors, known market
2. Comprehensive -- 5+ competitors including non-obvious alternatives
3. Deep-dive -- cross-category research, adjacent markets, academic references

## Prior Wave Consultation

Before beginning DIVERGE work, read SSOT and prior wave artifacts:

1. **SSOT** (if `docs/product/` exists):
   - `docs/product/jobs.yaml` -- validated jobs and opportunity scores
   - `docs/product/vision.md` -- product vision and strategic context
2. **Project context**: `docs/project-brief.md` | `docs/stakeholders.yaml` (if available)
3. **DISCOVER artifacts**: Read `docs/feature/{feature-id}/discover/` (if present)
   - `wave-decisions.md` -- validated assumptions and key decisions
   - `problem-validation.md` -- customer evidence grounding the problem

**Migration gate**: If `docs/product/` does not exist but `docs/feature/` has existing features, STOP. Guide the user to `docs/guides/migrating-to-ssot-model/README.md` and complete the migration first. If greenfield, DIVERGE will bootstrap `docs/product/jobs.yaml` with the validated job.

**READING ENFORCEMENT**: You MUST read every file listed in Prior Wave Consultation above using the Read tool before proceeding. After reading, output a confirmation checklist. Do NOT skip files that exist -- skipping causes options disconnected from evidence.

## Agent Invocation

@nw-diverger

Execute \*diverge for {feature-id}.

**Context Files:** see Prior Wave Consultation above + project context files.

**Configuration:**
- work_type: {Decision 1}
- research_depth: {Decision 2}
- output_directory: docs/feature/{feature-id}/

**SKILL_LOADING**: Before starting work, load your skill files using the Read tool from `~/.claude/skills/nw-{skill-name}/SKILL.md`. Skills encode your methodology -- without them you operate with generic knowledge only.

**Phase 1 -- JTBD Analysis:**
Flux loads `jtbd-analysis` skill. Extracts and elevates the job from the raw request or DISCOVER evidence. Produces job statements (functional + emotional + social) and ODI outcome statements. Gate G1 validates job level and ODI minimum.

**Phase 2 -- Competitive Research:**
Flux invokes `nw-researcher` sub-agent for evidence-grounded competitive research. Maps how existing products serve the validated job. Identifies non-obvious alternatives. Gate G2 validates real products named and evidence quality.

**Phase 3 -- Brainstorming:**
Flux loads `brainstorming` skill. Frames HMW question, applies SCAMPER lenses, generates structurally diverse options. Gate G3 validates diversity (mechanism|assumption|cost differ).

**Phase 4 -- Taste Evaluation:**
Flux loads `taste-evaluation` skill. Applies DVF filter, scores surviving options on 4 taste criteria with locked weights, produces weighted ranking and recommendation with dissenting case. Gate G4 validates completeness and traceability.

**Peer Review:**
After Phase 4 gates pass, Flux invokes `nw-diverger-reviewer` (Prism) to validate all 5 dimensions. Max 2 revision iterations before handoff.

## Success Criteria

- [ ] Job extracted at strategic or physical level (not tactical, not a feature description)
- [ ] Minimum 3 ODI outcome statements produced
- [ ] 3+ real competitors researched, at least one non-obvious alternative
- [ ] 6 structurally diverse options generated (different mechanism, assumption, cost)
- [ ] All surviving options scored on all 4 taste criteria with locked weights
- [ ] Recommendation traceable to scoring matrix (no "feels right" overrides)
- [ ] Dissenting case documented for second-place option
- [ ] Peer review approved by nw-diverger-reviewer
- [ ] Handoff accepted by nw-product-owner (DISCUSS wave)

## Next Wave

**Handoff To**: nw-product-owner (DISCUSS wave)
**Deliverables**: `recommendation.md` with explicit decision statement + supporting DIVERGE artifacts

## Wave Decisions Summary

Before completing DIVERGE, produce (or append to) `docs/feature/{feature-id}/wave-decisions.md`:

```markdown
# DIVERGE Decisions -- {feature-id}

## Key Decisions
- [D1] {decision}: {rationale} (see: {source-file})

## Job Summary
- Validated job: {job statement at strategic/physical level}
- ODI outcomes: {count} outcome statements

## Options Evaluated
- {count} options generated, {count} survived DVF filter
- Recommended: {option name} -- {one-line rationale}
- Dissent: {second-place option} -- {why it might be better under different assumptions}

## SSOT Updates
- jobs.yaml: {created|updated} with job JOB-{NNN}
```

## SSOT Update

After producing feature-level artifacts, update the product-level SSOT:

1. **Jobs SSOT**: Create or update `docs/product/jobs.yaml` with the validated job from Phase 1. Add changelog entry referencing this feature-id.
2. If `docs/product/` does not exist, create the directory. This is the SSOT bootstrap.

SSOT files use `schema_version` and `changelog` fields. See canonical schema in the design spec.

## Expected Outputs

### Feature delta (in `docs/feature/{feature-id}/`)
```
  recommendation.md             (top 3 options, dissenting case, decision for DISCUSS)
  wave-decisions.md             (DIVERGE section appended)
```

### Internal artifacts (in `docs/feature/{feature-id}/diverge/`)
```
  job-analysis.md               (validated job + ODI outcome statements)
  competitive-research.md       (prior art, competitor analysis, non-obvious alternatives)
  options-raw.md                (all generated options, unfiltered, no evaluation)
  taste-evaluation.md           (DVF filter, locked weights, scoring matrix)
  review.yaml                   (peer review result from nw-diverger-reviewer)
```

### SSOT updates (in `docs/product/`)
```
  jobs.yaml                     (created or updated with validated job + changelog entry)
```

## Examples

### Example 1: New product divergence
```
/nw-diverge notification-system
```
DISCOVER artifacts present with validated problem. Flux reads `problem-validation.md`, extracts job ("minimize likelihood of developers missing critical failure signals"), researches 5 notification tools including non-obvious alternatives (ambient light signals, IDE annotations), generates 6 structurally diverse options, scores with taste evaluation, recommends proactive push with Slack integration. Updates `jobs.yaml` with validated job.

### Example 2: Brownfield feature without DISCOVER
```
/nw-diverge rate-limiting
```
No DISCOVER artifacts. Flux works from project-brief.md and direct conversation. Extracts job via 5 Whys from "we need rate limiting" to strategic level. Creates `docs/product/jobs.yaml` (SSOT bootstrap). Proceeds through all 4 phases.

### Example 3: Skip validation (DIVERGE not needed)
```
/nw-diverge --skip auth-bugfix
```
Skip checklist evaluated: clear direction exists (bugfix), no competing approaches, self-evident path. DIVERGE skipped. User directed to `/nw-discuss` or `/nw-distill` depending on work type.
