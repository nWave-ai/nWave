---
name: nw-rr-critique-dimensions
description: Critique dimensions and scoring for research document reviews
disable-model-invocation: true
---

# Critique Dimensions for Research Review

Load when reviewing research documents. Apply each dimension systematically.

## Dimension 1: Source Selection Bias

Check: contradictory viewpoints included? | Multiple organizations/authors/perspectives? | Geographic/temporal diversity? | Sources truly independent (not circular)?

Flags: 60%+ from single org/author -> critical | All supporting same conclusion without counterpoint -> critical | Single geographic region -> medium | Clustered publication dates -> medium

## Dimension 2: Evidence Quality

Check: every major claim cited | sources reputable (peer-reviewed, official, established) | primary over secondary | technical sources recent (5 years) | confidence matches evidence

Flags: uncited claim -> high | blog/forum for factual claim -> high | all secondary sources -> medium | sources >5 years for tech -> medium | high confidence with 1-2 sources -> high

## Dimension 3: Replicability

Check: search strategy documented | source selection criteria explicit | methodology transparent | confidence levels with rationale

Flags: no methodology section -> high | vague methodology ("searched the web") -> medium | no confidence ratings -> medium

## Dimension 4: Priority Validation

For research driving architectural/strategic decisions.

Q1: Is this the largest bottleneck? (timing/measurement data?) | Q2: Simpler alternatives considered and rejected with evidence? | Q3: Constraint prioritization correct? (>50% solution for <30% problem = flag) | Q4: Key decision data-justified?

Flags: secondary concern addressed while larger exists -> critical | no measurement data for performance -> high | alternatives not documented -> high | prioritization not explicit -> medium

Output template:
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

Check: knowledge gaps documented (what searched, why insufficient) | conflicting info acknowledged with credibility analysis | all required sections present (summary, findings, sources, gaps, citations) | research metadata included

Flags: missing gaps section when gaps exist -> critical | conflicting sources unacknowledged -> high | missing required sections -> high | no metadata -> medium

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
