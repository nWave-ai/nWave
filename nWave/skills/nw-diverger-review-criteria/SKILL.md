---
name: nw-diverger-review-criteria
description: Review criteria for the nw-diverger-reviewer — validates JTBD rigor, research quality, option diversity, taste application correctness, and recommendation coherence in DIVERGE wave artifacts
user-invocable: false
disable-model-invocation: true
---

# Diverger Review Criteria

## Role

You are reviewing DIVERGE wave artifacts. Your job is adversarial: assume artifacts have problems until you prove they don't. Flag issues before the team commits to a design direction.

Five artifact files to review:
- `docs/feature/{id}/diverge/job-analysis.md`
- `docs/feature/{id}/diverge/competitive-research.md`
- `docs/feature/{id}/diverge/options-raw.md`
- `docs/feature/{id}/diverge/taste-evaluation.md`
- `docs/feature/{id}/diverge/recommendation.md`

---

## Dimension 1: JTBD Rigor

### Check 1.1 — Abstraction Level

**Requirement**: Job must be at strategic or physical level, not tactical.

**FAIL signals** (quote from artifact when found):
- Job statement describes a feature: "When I need to see status, I want a dashboard..."
- Job statement contains a solution reference: "When using the app, I want to..."
- Job reads like a user story: "As a developer, I want to..."

**PASS signal**: Job statement answers "what progress is being made?" without specifying how.

### Check 1.2 — First-Principles Extraction

**Requirement**: Evidence of 5-Why or abstraction-layer navigation.

**FAIL signals**:
- Job accepted as stated by user without elevation
- No "why?" chain documented
- Functional, emotional, and social jobs not distinguished

**PASS signal**: At least one level of elevation documented, from the raw request to the extracted job.

### Check 1.3 — Outcome Statement Quality

**Requirement**: ODI-format outcome statements (direction + metric + object): Minimize, or Maximize when more is genuinely better.

**FAIL signals**:
- "Easy", "reliable", "good", "effective" in outcome statements
- Solution references: "using AI", "via the dashboard"
- Compound statements with "and"/"or"
- Future-intent framing: "would reduce"

**PASS signal**: Each statement starts with "Minimize the [time/likelihood/effort]..." or a justified "Maximize the [metric]..." and is solution-agnostic.

---

## Dimension 2: Research Quality

### Check 2.1 — Evidence vs Opinion

**Requirement**: Competitive research cites real products, real behaviors, real data.

**FAIL signals**:
- "Most users probably..." without source
- "The market suggests..." without citation
- Competitor descriptions without named products
- Generic claims not tied to specific evidence

**PASS signal**: Each competitive insight names a real product or cites a real behavior/metric.

### Check 2.2 — Prior Art Coverage

**Requirement**: Research covers at least 3 existing solutions to the validated job.

**FAIL signals**:
- Research covers only direct competitors (ignores adjacent solutions)
- "No existing solutions" claim without justification
- Research treats the feature space, not the job space

**PASS signal**: Research includes at least one surprising or non-obvious alternative (a different category that does the same job).

---

## Dimension 3: Option Diversity

### Check 3.1 — Structural Diversity

**Requirement**: 6 options, each structurally different (different mechanism, different assumption, different cost profile).

**FAIL signals**:
- Two or more options differ only in degree, not kind ("Option A: full dashboard" / "Option B: mini dashboard")
- Options cluster around one approach with minor variations
- No option represents a radical simplification (SCAMPER "Eliminate")
- No option inverts the workflow (SCAMPER "Reverse")

**PASS signal**: Applying the 3-point diversity test to each pair of the 6 curated options before DVF filtering — they differ in mechanism, assumption and cost profile. Documented DVF eliminations may reduce the surviving set.

### Check 3.2 — Generation Discipline

**Requirement**: Options were generated before evaluation (separation principle).

**FAIL signal**: Options-raw.md contains evaluative language ("This is the best because...", "This won't work because...") mixed with generation content.

**PASS signal**: options-raw.md is purely descriptive; evaluation appears only in taste-evaluation.md.

### Check 3.3 — HMW Framing Quality

**Requirement**: The HMW question doesn't embed a solution.

**FAIL signals**:
- HMW question names a specific technology: "How might we use AI to..."
- HMW question names a specific UI pattern: "How might we build a dashboard that..."
- HMW question is narrower than the validated job

**PASS signal**: HMW question can be answered by options that don't share the same technology or UI pattern.

---

## Dimension 4: Taste Application

### Check 4.1 — Criteria Applied Consistently

**Requirement**: All four taste criteria (Subtraction, Concept Count, Progressive Disclosure, Speed-as-Trust) applied to all surviving options.

**FAIL signals**:
- Some options scored on fewer criteria than others
- Criteria added or removed mid-evaluation
- DVF elimination not documented (options disappeared without reason)

**PASS signal**: Full scoring matrix present for all post-DVF-filter options with all criteria scored.

### Check 4.2 — Cherry-Picking Prevention

**Requirement**: Weights locked before scoring begins; recommendation follows from scores.

**FAIL signals**:
- Recommendation contradicts the highest-scoring option without a documented weight adjustment and consistent recalculation of all surviving options
- Weights not specified in artifact
- "This option feels right" language in recommendation without score grounding

**PASS signal**: Recommended option has the highest weighted total in the current matrix. If weights change for an evidenced product reason or human decision, preserve that provenance, apply the revised weights to all surviving options and recalculate before recommending. A prose preference for the runner-up alone does not satisfy this check; retain it as dissent.

### Check 4.3 — Score Rubric Application

**Requirement**: Scores justified against rubric, not assigned freely.

**FAIL signals**:
- Score of 5 for "Subtraction" on an option with multiple features, without justification
- Score of 1 for "Speed-as-Trust" on a text-based tool without latency analysis
- Scores assigned without quoting the rubric criterion

**PASS signal**: Each score accompanied by one sentence referencing the specific rubric level.

---

## Dimension 5: Recommendation Coherence

### Check 5.1 — Traceability

**Requirement**: Recommendation traceable to JTBD → Research → Scores.

**FAIL signal**: Recommendation could be made without reading job-analysis.md or taste-evaluation.md.

**PASS signal**: Recommendation references the validated job, cites competitive research findings, and derives from the highest-scoring option(s).

### Check 5.2 — Dissent Documented

**Requirement**: "Runner-up" case documented — which option almost won and why.

**FAIL signal**: Only the winning option discussed in recommendation.

**PASS signal**: recommendation.md includes a "dissenting case" section naming the runner-up and the margin.

### Check 5.3 — DISCUSS Handoff Readiness

**Requirement**: Recommendation ends with a clear decision statement for the DISCUSS wave.

**FAIL signal**: Recommendation ends with "both options are viable" or "the team should decide."

**PASS signal**: Explicit decision statement: "Proceed with [option], assuming [key risk] is acceptable."

---

## Review Output Format

```yaml
review_result:
  artifact_path: "docs/feature/{id}/diverge/"
  review_date: "{timestamp}"
  reviewer: "nw-diverger-reviewer"

  jtbd_rigor:
    status: "PASSED|FAILED"
    issues: [{check, location, quoted_evidence, remediation}]

  research_quality:
    status: "PASSED|FAILED"
    issues: [{check, location, quoted_evidence, remediation}]

  option_diversity:
    status: "PASSED|FAILED"
    issues: [{check, location, quoted_evidence, remediation}]

  taste_application:
    status: "PASSED|FAILED"
    issues: [{check, location, quoted_evidence, remediation}]

  recommendation_coherence:
    status: "PASSED|FAILED"
    issues: [{check, location, quoted_evidence, remediation}]

  approval_status: "approved|conditionally_approved|rejected_pending_revisions"
  blocking_issues: []
  recommendations: []
```

**Approval thresholds**:
- `approved`: all dimensions PASSED
- `conditionally_approved`: no FAILED dimensions, minor issues only
- `rejected`: any dimension FAILED, with specific remediation required
