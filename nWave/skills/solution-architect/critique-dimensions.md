---
name: critique-dimensions
description: Architecture quality critique dimensions for peer review. Load when invoking solution-architect-reviewer or performing self-review of architecture documents.
---

# Architecture Quality Critique Dimensions

## Dimension 1: Architectural Bias Detection

### Technology Preference Bias
Pattern: Technology chosen by architect preference, not requirements. Detection: ADR lacks comparison matrix with alternatives, choice not mapped to specific requirements, justification is only "best practice" or "modern stack."
Severity: HIGH.

### Resume-Driven Development
Pattern: Complex/trendy tech without requirement justification. Examples: microservices for 3-person team, Kafka for 100 req/day, service mesh without inter-service complexity. Detection: architecture complexity exceeds team size and requirements, new tech adds resume value rather than solving problem.
Severity: CRITICAL.

### Latest Technology Bias
Pattern: Unproven tech (<6 months, small community) for production. Detection: check maturity, community size, LTS support, fallback plan.
Severity: HIGH.

## Dimension 2: ADR Quality Validation

### Missing Context
ADR lacks business problem, technical constraints, or quality attribute requirements. Future maintainers cannot validate decision appropriateness.
Severity: HIGH.

### Missing Alternatives Analysis
ADR documents no alternatives (minimum 2 required). Each alternative must be evaluated against requirements with rejection rationale.
Severity: HIGH.

### Missing Consequences
ADR omits positive/negative consequences and trade-offs. Impact on quality attributes not analyzed.
Severity: MEDIUM.

## Dimension 3: Completeness Validation

### Missing Quality Attributes
Architecture does not address required quality attributes. Verify: performance (latency, throughput), scalability, security (auth, data protection), maintainability (modularity, testability), reliability (fault tolerance, recovery), observability (logging, monitoring, alerting).
Severity: CRITICAL.

### Missing Performance Architecture
Performance requirements exist but no optimization strategy (caching, indexing, rate limiting, CDN).
Severity: CRITICAL.

## Dimension 4: Implementation Feasibility

### Team Capability Mismatch
Architecture requires expertise team lacks. Verify learning curve reasonable for timeline, training plan exists if needed.
Severity: HIGH.

### Budget Constraints
Infrastructure costs exceed budget. Verify cost estimate exists and aligns with constraints.
Severity: HIGH.

### Testability Validation
Architecture prevents effective testing. Components must enable isolated testing with ports/adapters for dependency injection.
Severity: CRITICAL.

## Dimension 5: Priority Validation

Validate roadmap addresses the largest bottleneck, not a secondary concern.

**Q1**: Is this the largest bottleneck? (timing data must show this is primary problem)
**Q2**: Were simpler alternatives considered? (rejected alternatives section required)
**Q3**: Is constraint prioritization correct? (user-mentioned constraints quantified by impact, constraint-free opportunities addressed first)
**Q4**: Is architecture data-justified? (key decision supported by quantitative data)

Failure conditions:
- Q1 = NO (wrong problem addressed)
- Q2 = MISSING (no alternatives considered)
- Q3 = INVERTED (minority constraint dominating solution -- >50% of solution for <30% of problem)
- Q4 = NO_DATA for performance optimization

## Review Output Format

```yaml
review_id: "arch_rev_{timestamp}"
reviewer: "solution-architect-reviewer"
artifact: "docs/architecture/architecture.md, docs/adrs/*.md"
iteration: {1 or 2}

strengths:
  - "{Positive architectural decision with ADR reference}"

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

- **Critical**: Resume-driven development, missing critical quality attributes, untestable architecture, wrong problem addressed
- **High**: Technology bias, incomplete ADRs, feasibility concerns, missing data
- **Medium**: Missing consequences, minor completeness gaps
- **Low**: Documentation improvements, naming consistency
