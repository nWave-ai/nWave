---
name: critique-dimensions
description: Critique dimensions and scoring for research document reviews
---

# Critique Dimensions for Research Review

Load this skill when reviewing research documents. Apply each dimension systematically.

## Dimension 1: Source Selection Bias

**What to check**:
- Are contradictory viewpoints included?
- Are sources from multiple organizations, authors, and perspectives?
- Is there geographic and temporal diversity?
- Are sources truly independent (not citing each other circularly)?

**Flags**:
- 60%+ sources from single organization or author -> critical
- All sources supporting same conclusion with no counterpoint -> critical
- Sources only from one geographic region -> medium
- Publication dates clustered in narrow window -> medium

## Dimension 2: Evidence Quality

**What to check**:
- Every major claim has a citation
- Sources are reputable (peer-reviewed, official docs, established practitioners)
- Primary sources preferred over secondary interpretations
- Technical sources are recent (within 5 years for fast-moving topics)
- Confidence ratings match the evidence strength

**Flags**:
- Claim without any citation -> high
- Citation from blog post or forum for a factual claim -> high
- All sources are secondary (no primary) -> medium
- Sources older than 5 years for technical topics -> medium
- High confidence rating with only 1-2 sources -> high

## Dimension 3: Replicability

**What to check**:
- Search queries or strategy documented
- Source selection criteria explicit
- Methodology transparent enough for another researcher to follow
- Confidence levels stated with rationale

**Flags**:
- No methodology section -> high
- Methodology present but vague ("searched the web") -> medium
- No confidence ratings on findings -> medium

## Dimension 4: Priority Validation

Use when reviewing research that drives architectural or strategic decisions.

**Questions**:
1. Is this the largest bottleneck? Does timing/measurement data confirm?
2. Were simpler alternatives considered and rejected with evidence?
3. Is constraint prioritization correct? (Flag if >50% of solution targets <30% of problem)
4. Is the key decision supported by quantitative data?

**Flags**:
- Research addresses secondary concern while larger exists -> critical
- No measurement data for performance-related research -> high
- Simple alternatives not documented -> high
- Constraint prioritization not explicit -> medium

**Output template for priority validation**:
```yaml
priority_validation:
  q1_largest_bottleneck:
    evidence: "{timing data or 'NOT PROVIDED'}"
    assessment: "YES|NO|UNCLEAR"
  q2_simple_alternatives:
    assessment: "ADEQUATE|INADEQUATE|MISSING"
  q3_constraint_prioritization:
    minority_constraint_dominating: "YES|NO"
    assessment: "CORRECT|INVERTED|NOT_ANALYZED"
  q4_data_justified:
    assessment: "JUSTIFIED|UNJUSTIFIED|NO_DATA"
  verdict: "PASS|FAIL"
```

## Dimension 5: Completeness

**What to check**:
- Knowledge gaps explicitly documented (what was searched, why insufficient)
- Conflicting information acknowledged with source credibility analysis
- All required sections present (executive summary, findings, sources, gaps, citations)
- Research metadata included (source count, confidence distribution)

**Flags**:
- Missing knowledge gaps section when gaps clearly exist -> critical
- Conflicting sources not acknowledged -> high
- Missing required sections -> high
- No research metadata -> medium

## Review Output Template

```yaml
review_id: "research_rev_{timestamp}"
reviewer: "nw-researcher-reviewer (Scholar)"

issues_identified:
  source_bias:
    - issue: "{specific description with numbers}"
      severity: "critical|high|medium"
      recommendation: "{actionable fix}"
  evidence_quality:
    - issue: "{specific claim or location}"
      severity: "critical|high|medium"
      recommendation: "{actionable fix}"
  replicability:
    - issue: "{what is missing}"
      severity: "critical|high|medium"
      recommendation: "{actionable fix}"
  priority_validation:
    - issue: "{mismatch description}"
      severity: "critical|high|medium"
      recommendation: "{actionable fix}"
  completeness:
    - issue: "{missing element}"
      severity: "critical|high|medium"
      recommendation: "{actionable fix}"

quality_scores:
  source_bias: 0.00
  evidence_quality: 0.00
  replicability: 0.00
  completeness: 0.00
  priority_validation: 0.00

approval_status: "approved|rejected_pending_revisions"
blocking_issues:
  - "{critical issue 1}"
iteration: 1
max_iterations: 2
```
