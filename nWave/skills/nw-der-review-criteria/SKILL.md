---
name: nw-der-review-criteria
description: Evaluation criteria and scoring for data engineering artifact reviews
disable-model-invocation: true
---

# Data Engineer Review Criteria

Evaluation criteria for each review dimension. Load when performing reviews.

## Dimension 1: Research Citation Quality

Evaluate whether recommendations trace to specific evidence.

**Checks**: Each major recommendation cites a specific research finding | Citations are accurate (finding number matches content) | Vendor-specific claims have multiple independent sources | General best practices distinguished from research-validated guidance

**Scoring**: 10: All cited, verified | 7: Most cited, 1-2 missing on non-critical points | 4: Major recommendations lack citations | 0: No citations

## Dimension 2: Security Coverage

Evaluate defense-in-depth for data layer.

**Checks**: Encryption at rest (TDE) | Encryption in transit (TLS) | Access control model (RBAC/ABAC) | SQL injection prevention (parameterized queries) | OWASP/NIST standards referenced | Credential handling (no hardcoded secrets)

**Scoring**: 10: All 6 checks with standard references | 7: 4-5 checks | 4: 2-3 checks, missing encryption or injection prevention | 0: Security not mentioned

## Dimension 3: Trade-off Analysis

Evaluate balanced presentation of alternatives.

**Checks**: Multiple technology options (minimum 2) | Pros/cons for each | Context factors identified (scale, consistency, latency, cost) | Recommendation justified by context fit | Limitations acknowledged

**Scoring**: 10: Comprehensive trade-offs with context-driven justification | 7: Trade-offs present, some alternatives missing | 4: Single recommendation without alternatives | 0: Prescriptive with no analysis

## Dimension 4: Technical Accuracy

**Checks**: SQL/NoSQL syntax correct for specified DB | Architecture patterns appropriate for use case (OLTP vs OLAP, write-heavy vs read-heavy) | Optimization strategies valid for target DB | Normalization level appropriate for workload | Index type matches query patterns (B-tree for range, hash for equality) | CAP trade-offs correctly applied

**Scoring**: 10: All technical claims verified | 7: Minor syntax/edge-case issues | 4: Significant errors affecting recommendations | 0: Fundamentally incorrect guidance

## Dimension 5: Completeness

**Checks**: Scaling strategy (vertical, horizontal, sharding, replication) | Performance characteristics (query patterns, bottlenecks) | Data governance when applicable (lineage, quality, MDM) | Compliance when personal/regulated data involved (GDPR, CCPA, HIPAA) | Backup/recovery for production designs | Monitoring/observability

**Scoring**: 10: All applicable aspects covered | 7: Core covered, 1-2 peripheral missing | 4: Major gaps (missing scaling or governance for production) | 0: Only immediate question, no broader context

## Dimension 6: Bias Detection

**Checks**: No single-vendor preference without justification | No latest-technology bias (new tech only when justified) | Contradictory evidence acknowledged | Open-source and commercial both considered | Technology maturity/community factored in | Cost mentioned

**Scoring**: 10: Demonstrably balanced with explicit trade-offs | 7: Generally balanced, minor preferences | 4: Clear vendor/tech bias | 0: Single-vendor advocacy

## Dimension 7: Implementability

**Checks**: Schema designs include column types, constraints, indexes | Architecture specifies integration points/APIs | Security has concrete steps (not just "use encryption") | Migration path described if changing systems | Dependencies/prerequisites identified | Handoff to next agent clear

**Scoring**: 10: Downstream agent proceeds without clarification | 7: Minor clarifications needed | 4: Significant implementation details missing | 0: Abstract guidance, no actionable content

## Severity Classification Guide

**Blocker**: Prevents downstream work or introduces security vulnerability. Examples: missing encryption for PII, wrong DB choice for workload, SQL syntax errors in migrations.

**Major**: Significantly reduces quality or misses important considerations. Examples: missing trade-off analysis, no scaling strategy for production, incomplete security coverage.

**Minor**: Improvement that does not block progress. Examples: missing citation on secondary recommendation, single alternative not considered, minor syntax variation.

**Suggestion**: Enhancement that adds polish. Examples: additional index for edge-case query, governance for future compliance, alternative monitoring approach.
