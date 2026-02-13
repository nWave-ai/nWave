---
name: review-criteria
description: Evaluation criteria and scoring for data engineering artifact reviews
---

# Data Engineer Review Criteria

Detailed evaluation criteria for each review dimension. Load this skill when performing reviews.

## Dimension 1: Research Citation Quality

Evaluate whether recommendations trace to specific evidence.

**Checks**:
- Each major recommendation cites a specific research finding (e.g., "Finding 6: Indexing Strategies")
- Citations are accurate — the finding number matches the claimed content
- Vendor-specific claims have multiple independent sources
- General best practices are distinguished from research-validated guidance

**Scoring**:
- 10: All recommendations cited, citations verified
- 7: Most cited, 1-2 missing citations on non-critical points
- 4: Significant gaps — major recommendations lack citations
- 0: No research citations present

## Dimension 2: Security Coverage

Evaluate defense-in-depth for data layer.

**Checks**:
- Encryption at rest (TDE or equivalent) addressed
- Encryption in transit (TLS) addressed
- Access control model specified (RBAC/ABAC)
- SQL injection prevention mentioned (parameterized queries)
- OWASP/NIST standards referenced where applicable
- Credential handling guidance (no hardcoded secrets)

**Scoring**:
- 10: All 6 checks addressed with standard references
- 7: 4-5 checks addressed
- 4: Only 2-3 checks, missing encryption or injection prevention
- 0: Security not mentioned

## Dimension 3: Trade-off Analysis

Evaluate balanced presentation of alternatives.

**Checks**:
- Multiple technology options presented (minimum 2)
- Pros and cons listed for each option
- Context factors identified (scale, consistency, latency, cost)
- Recommendation justified by context fit, not preference
- Limitations of chosen approach acknowledged

**Scoring**:
- 10: Comprehensive trade-offs with context-driven justification
- 7: Trade-offs present but missing some alternatives
- 4: Single recommendation without alternatives
- 0: Prescriptive recommendation with no analysis

## Dimension 4: Technical Accuracy

Evaluate correctness of technical content.

**Checks**:
- SQL/NoSQL syntax correct for the specified database system
- Architecture patterns appropriate for stated use case (OLTP vs OLAP, write-heavy vs read-heavy)
- Optimization strategies valid for the target database
- Normalization level appropriate for workload type
- Index type selection matches query patterns (B-tree for range, hash for equality)
- CAP theorem trade-offs correctly applied

**Scoring**:
- 10: All technical claims verified correct
- 7: Minor syntax issues or edge-case inaccuracies
- 4: Significant technical errors that affect recommendations
- 0: Fundamentally incorrect technical guidance

## Dimension 5: Completeness

Evaluate whether all relevant aspects are covered.

**Checks**:
- Scaling strategy discussed (vertical, horizontal, sharding, replication)
- Performance characteristics documented (expected query patterns, bottlenecks)
- Data governance addressed when applicable (lineage, quality, MDM)
- Compliance requirements noted when personal/regulated data involved (GDPR, CCPA, HIPAA)
- Backup and recovery strategy mentioned for production designs
- Monitoring and observability considerations included

**Scoring**:
- 10: All applicable aspects covered comprehensively
- 7: Core aspects covered, 1-2 peripheral topics missing
- 4: Major gaps — missing scaling or governance for production design
- 0: Only addresses the immediate question with no broader context

## Dimension 6: Bias Detection

Evaluate objectivity and balance.

**Checks**:
- No single-vendor preference without justification
- Latest-technology bias absent (new tech recommended only when justified)
- Contradictory evidence acknowledged, not suppressed
- Open-source and commercial options both considered where relevant
- Technology maturity and community support factored in
- Cost considerations mentioned

**Scoring**:
- 10: Demonstrably balanced with explicit acknowledgment of trade-offs
- 7: Generally balanced with minor preference tendencies
- 4: Clear vendor or technology bias affecting recommendations
- 0: Single-vendor advocacy without alternatives

## Dimension 7: Implementability

Evaluate whether downstream agents can act on the artifact.

**Checks**:
- Schema designs include column types, constraints, and indexes
- Architecture recommendations specify integration points and APIs
- Security implementation has concrete steps (not just "use encryption")
- Migration path described if changing existing systems
- Dependencies and prerequisites identified
- Handoff to next agent (software-crafter, solution-architect) is clear

**Scoring**:
- 10: Downstream agent can proceed without clarification
- 7: Minor clarifications needed but core is actionable
- 4: Significant gaps — implementation details missing
- 0: Abstract guidance with no actionable content

## Severity Classification Guide

**Blocker**: Prevents downstream work or introduces security vulnerability.
Examples: missing encryption for PII data, fundamentally wrong database choice for workload, SQL syntax errors in migration scripts.

**Major**: Significantly reduces quality or misses important considerations.
Examples: missing trade-off analysis, no scaling strategy for production system, incomplete security coverage.

**Minor**: Improvement opportunity that does not block progress.
Examples: missing citation on a secondary recommendation, single alternative not considered, minor syntax variation.

**Suggestion**: Enhancement that adds polish.
Examples: additional index for edge-case query, governance consideration for future compliance, alternative monitoring approach.
