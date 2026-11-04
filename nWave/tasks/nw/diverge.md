---
description: "Generates 3-5 divergent design directions through JTBD analysis, competitive research, structured brainstorming, and taste evaluation before convergence."
argument-hint: "[feature-id] - Optional: --work-type=[new-product|brownfield|pivot]"
---

# NW-DIVERGER: Structured Divergent Thinking Before Convergence

**Wave**: DIVERGE (between DISCOVER and DISCUSS, optional) | **Agent**: Flux (nw-diverger) | **Command**: `/nw-diverger`

## Overview

Execute DIVERGE wave through Flux's 4-phase workflow: JTBD analysis|competitive research|structured brainstorming|taste-filtered evaluation. Transforms a validated problem into 3-5 concrete, taste-scored design directions so DISCUSS can converge on one with confidence.

DIVERGE is optional. Brownfield features with a clear direction may skip it (see skip checklist in design spec). New products and pivot decisions benefit most from structured divergence.

## Delivery route

Use nwdes for delivery: read `nw-nwdes`. Divergent directions remain proposals
until a product choice is made; no candidate direction creates a delivery plan.
For DISCUSS, the host creates or selects the nwdes feature and builds the
installed Product Owner's prompt with `nwdes prompt`. The PO uses Bash and
`nwdes product decision add` to record the chosen direction and
unresolved alternatives, then closes. Render its brief with `nwdes document`.
The host orchestrates; a candidate-options report is not a second handoff.

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
   - `docs/product/vision.md` -- product vision and strategic context, including any DISCOVER assumptions already promoted here
2. **Project context**: `docs/project-brief.md` | `docs/stakeholders.yaml` (if available)
3. **DISCOVER evidence** (if a DISCOVER pass ran for this problem): re-read the returned problem-validation evidence, or ask the user for it if not still in context -- customer evidence grounding the problem. Validated assumptions already live in the SSOT above.

If `docs/product/` does not exist, this is the first wave using the SSOT model. DIVERGE will create it (bootstrap `docs/product/jobs.yaml` with the validated job).

**READING ENFORCEMENT**: You MUST read every file listed in Prior Wave Consultation above using the Read tool before proceeding. After reading, output a confirmation checklist. Do NOT skip files that exist -- skipping causes options disconnected from evidence.

## Agent Invocation

@nw-diverger

Execute \*diverge for {feature-id}.

**Context Files:** see Prior Wave Consultation above + project context files.

**Configuration:**
- work_type: {Decision 1}
- research_depth: {Decision 2}

**SKILL_LOADING**: Before starting work, load your skill files using the Read tool from `~/.claude/skills/nw-{skill-name}/SKILL.md`. Skills encode your methodology -- without them you operate with generic knowledge only.

**Phase 1 -- JTBD Analysis:**
Flux loads `jtbd-analysis` skill. Extracts and elevates the job from the raw request or DISCOVER evidence. Produces job statements (functional + emotional + social) and ODI outcome statements. Gate G1 validates job level and ODI minimum.

**Phase 2 -- Competitive Research:**
Flux invokes `nw-researcher` sub-agent for evidence-grounded competitive research. Maps how existing products serve the validated job. Identifies non-obvious alternatives. Gate G2 validates real products named and evidence quality.

**Phase 3 -- Brainstorming:**
Flux loads `brainstorming` skill. Frames HMW question, applies SCAMPER lenses, states a probability per candidate, keeps tail candidates, and names options with the requester's words where they exist (coined names marked as coined). Gate G3 validates diversity (mechanism|assumption|cost differ) plus the head-clustering read of the stated probabilities restated as one distribution over the curated six.

**Phase 4 -- Taste Evaluation:**
Flux loads `taste-evaluation` skill. Applies DVF filter, scores surviving options on 4 taste criteria with locked weights, produces weighted ranking and recommendation with dissenting case. Gate G4 validates completeness and traceability.

**Peer Review:**
After Phase 4 gates pass, Flux invokes `nw-diverger-reviewer` (Prism) to validate all 5 dimensions. Max 2 revision iterations before handoff.


## Success Criteria

- [ ] Job extracted at strategic or physical level (not tactical, not a feature description)
- [ ] Minimum 3 ODI outcome statements produced
- [ ] 3+ real competitors researched, at least one non-obvious alternative
- [ ] 6 structurally diverse options generated (different mechanism, assumption, cost; two tail candidates among the six or one differing in mechanism from every head candidate; head-clustering read documented; name_origin marked per option)
- [ ] All surviving options scored on all 4 taste criteria with locked weights
- [ ] Recommendation traceable to scoring matrix (no "feels right" overrides)
- [ ] Dissenting case documented for second-place option
- [ ] Peer review approved by nw-diverger-reviewer
- [ ] Handoff accepted by nw-product-owner (DISCUSS wave)

## Next Wave

**Handoff To**: nw-product-owner (DISCUSS wave)
**Deliverables**: The candidate directions are ephemeral working material; only
the recommended direction and its explicit decision statement are returned
directly to DISCUSS, backed by the updated `docs/product/jobs.yaml`.

## SSOT Update

The durable product-level SSOT is the only normative handoff the next wave
reads -- not a per-wave decision file. Update it directly:

1. **Jobs SSOT**: Create or update `docs/product/jobs.yaml` with the validated job from Phase 1. Add changelog entry referencing this feature-id.
2. If `docs/product/` does not exist, create the directory. This is the SSOT bootstrap.

SSOT files use `schema_version` and `changelog` fields. The public schema walkthrough is `docs/guides/migrating-to-ssot-model/`.

## Expected Outputs

### SSOT updates (in `docs/product/`)
```
  jobs.yaml                     (created or updated with validated job + changelog entry)
```

## Examples

### Example 1: New product divergence
```
/nw-diverger notification-system
```
DISCOVER evidence present for a validated problem. Flux re-reads the returned problem-validation evidence, extracts job ("minimize likelihood of developers missing critical failure signals"), researches 5 notification tools including non-obvious alternatives (ambient light signals, IDE annotations), generates 6 structurally diverse options, scores with taste evaluation, recommends proactive push with Slack integration. Updates `jobs.yaml` with validated job.

### Example 2: Brownfield feature without DISCOVER
```
/nw-diverger rate-limiting
```
No DISCOVER artifacts. Flux works from project-brief.md and direct conversation. Extracts job via 5 Whys from "we need rate limiting" to strategic level. Creates `docs/product/jobs.yaml` (SSOT bootstrap). Proceeds through all 4 phases.

### Example 3: Skip validation (DIVERGE not needed)
```
/nw-diverger --skip auth-bugfix
```
Skip checklist evaluated: clear direction exists (bugfix), no competing approaches, self-evident path. DIVERGE skipped. User directed to `/nw-discuss` or `/nw-distill` depending on work type.
