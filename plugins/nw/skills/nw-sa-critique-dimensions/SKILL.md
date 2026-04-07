---
name: nw-sa-critique-dimensions
description: Architecture quality critique dimensions for peer review. Load when invoking solution-architect-reviewer or performing self-review of architecture documents.
user-invocable: false
disable-model-invocation: true
---

# Architecture Quality Critique Dimensions

## Dimension 1: Architectural Bias Detection

### Technology Preference Bias
Pattern: tech chosen by preference, not requirements. Detection: ADR lacks comparison matrix, choice not mapped to requirements, justified only as "best practice." Severity: HIGH.

### Resume-Driven Development
Pattern: complex/trendy tech without requirement justification. Examples: microservices for 3-person team, Kafka for 100 req/day, service mesh without complexity. Detection: complexity exceeds team size/requirements, tech adds resume value not solves problem. Severity: CRITICAL.

### Latest Technology Bias
Pattern: unproven tech (<6 months, small community) for production. Detection: check maturity, community, LTS, fallback plan. Severity: HIGH.

## Dimension 2: ADR Quality Validation

### Missing Context
ADR lacks business problem, technical constraints, or quality attribute requirements. Future maintainers cannot validate. Severity: HIGH.

### Missing Alternatives Analysis
No alternatives (min 2 required). Each must be evaluated against requirements with rejection rationale. Severity: HIGH.

### Missing Consequences
Omits positive/negative consequences and trade-offs. Quality attribute impact not analyzed. Severity: MEDIUM.

## Dimension 3: Completeness Validation

### Missing Quality Attributes
Architecture doesn't address required attributes. Verify: performance (latency, throughput) | scalability | security (auth, data protection) | maintainability (modularity, testability) | reliability (fault tolerance, recovery) | observability (logging, monitoring, alerting). Severity: CRITICAL.

### Missing Performance Architecture
Performance requirements exist but no optimization strategy (caching, indexing, rate limiting, CDN). Severity: CRITICAL.

## Dimension 4: Implementation Feasibility

### Team Capability Mismatch
Requires expertise team lacks. Verify learning curve reasonable, training plan exists. Severity: HIGH.

### Budget Constraints
Infrastructure costs exceed budget. Verify cost estimate exists and aligns. Severity: HIGH.

### Testability Validation
Architecture prevents effective testing. Components must enable isolated testing with ports/adapters. Severity: CRITICAL.

## Dimension 5: Priority Validation

Validate roadmap addresses largest bottleneck.

**Q1**: Largest bottleneck? (timing data must confirm primary problem)
**Q2**: Simpler alternatives considered? (rejected alternatives required)
**Q3**: Constraint prioritization correct? (quantified by impact, constraint-free first)
**Q4**: Data-justified? (key decision with quantitative data)

Failure: Q1=NO (wrong problem) | Q2=MISSING (no alternatives) | Q3=INVERTED (>50% solution for <30% problem) | Q4=NO_DATA for performance

## Review Output Format

```yaml
review_id: "arch_rev_{timestamp}"
reviewer: "solution-architect-reviewer"
artifact: "docs/product/architecture/brief.md, docs/product/architecture/adr-*.md"
iteration: {1 or 2}

strengths:
  - "{Positive decision with ADR reference}"

issues_identified:
  architectural_bias:
    - issue: "{pattern detected}"
      severity: "critical|high|medium|low"
      location: "{ADR or section}"
      recommendation: "{actionable fix}"
  decision_quality:
    - issue: "{ADR quality issue}"
      severity: "high"
      location: "ADR-{number}"
      recommendation: "{add missing section}"
  completeness_gaps:
    - issue: "{quality attribute not addressed}"
      severity: "critical"
      recommendation: "{add architecture section}"
  implementation_feasibility:
    - issue: "{capability, budget, testability concern}"
      severity: "high"
      recommendation: "{simplify or add mitigation}"
  priority_validation:
    q1_largest_bottleneck:
      evidence: "{data or NOT PROVIDED}"
      assessment: "YES|NO|UNCLEAR"
    q2_simple_alternatives:
      assessment: "ADEQUATE|INADEQUATE|MISSING"
    q3_constraint_prioritization:
      assessment: "CORRECT|INVERTED|NOT_ANALYZED"
    q4_data_justified:
      assessment: "JUSTIFIED|UNJUSTIFIED|NO_DATA"

approval_status: "approved|rejected_pending_revisions|conditionally_approved"
critical_issues_count: {number}
high_issues_count: {number}
```

## Severity Classification

- **Critical**: resume-driven dev, missing critical quality attributes, untestable, wrong problem
- **High**: technology bias, incomplete ADRs, feasibility concerns, missing data
- **Medium**: missing consequences, minor completeness gaps
- **Low**: documentation improvements, naming consistency
