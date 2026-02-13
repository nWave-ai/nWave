---
name: production-readiness
description: Monitoring, observability, operational procedures, CI/CD lessons learned, and quality gate definitions. Load when assessing production readiness or validating operational excellence.
---

# Production Readiness

## Monitoring and Observability

### Application Monitoring
- **Performance**: response time, throughput, latency percentiles (P50, P95, P99)
- **Resources**: CPU, memory, database connections, cache hit rates
- **Errors**: exception tracking, error rate trends, integration failure detection
- **Business**: KPI tracking, conversion funnels, feature usage, revenue impact

### Infrastructure Monitoring
- Server/container health and resource utilization
- Network performance and connectivity
- Storage capacity and I/O performance
- Security event detection

### Alerting Tiers
| Tier | Condition | Response |
|------|-----------|----------|
| Page | Service down, data loss risk, security breach | Immediate response |
| Urgent | Error rate >2x baseline, latency SLA breach | Response within 15 min |
| Warning | Capacity >80%, error rate trending up | Response within 1 hour |
| Info | Deployment complete, metric threshold crossed | Review next business day |

## Operational Procedures

### Incident Response
1. Detect: automated alerting identifies issue
2. Triage: classify severity, assign responder
3. Communicate: notify stakeholders per severity level
4. Resolve: apply fix or rollback
5. Review: post-incident review within 48 hours
6. Improve: update runbooks and monitoring based on findings

### Maintenance Procedures
- Regular update and patching schedule
- Backup verification (test restores quarterly)
- Security vulnerability scanning (automated, weekly)
- Performance baseline recalibration (after major changes)

### Knowledge Transfer
- Operational runbooks for common procedures
- Architecture documentation with system diagrams
- Deployment procedures and configuration management
- Troubleshooting guides for known failure modes

## Quality Gates for Production Readiness

Before declaring production-ready, all must pass:

- [ ] All acceptance tests passing
- [ ] Unit coverage meets project standard (default: >= 80%)
- [ ] Integration tests validated
- [ ] Performance validated under realistic load
- [ ] Security scan completed (0 critical, 0 high)
- [ ] Monitoring and alerting configured
- [ ] Logging structured and searchable
- [ ] Rollback procedure documented and tested
- [ ] Runbook created for operational procedures
- [ ] On-call team trained on new feature

## CI/CD Architecture Lessons

### Test Architecture and Measurement Coupling

Test execution architecture changes require simultaneous measurement strategy updates.

**Fundamental principle**: treat test execution architecture and measurement strategy as tightly coupled concerns.

### Common Pitfalls

| Pitfall | Symptom | Prevention |
|---------|---------|------------|
| False failure syndrome | Quality gates fail after CI/CD change without code changes | Validate measurement strategy in isolated environment first |
| Baseline drift | Increasing threshold adjustments without justification | Maintain versioned baseline documentation |
| Tool assumption violations | Inconsistent metrics across CI/CD runs | Review tool docs for architecture-specific behaviors |

### CI/CD Change Checklist

**Before**:
- Analyze impact on test discovery mechanisms
- Identify affected measurement tools (coverage, mutation testing)
- Document current baseline metrics

**During**:
- Adjust coverage thresholds for new execution model
- Validate measurement strategy compatibility
- Recalibrate quality gate thresholds

**After**:
- Establish new baseline metrics
- Validate measurement accuracy against known scenarios
- Update runbooks with measurement strategy changes

### Real-World Example
Parallelization (pytest-xdist) without measurement update caused false quality gate failures. Coverage calculation changed due to worker-based test distribution. Fix: document coupling, establish new baseline, mandate measurement review for all CI/CD architecture changes.
