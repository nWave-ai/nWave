---
name: investigation-techniques
description: Evidence collection methods, problem categorization, analysis techniques, and solution design patterns
---

# Investigation Techniques

## Problem Categorization

### Technical Problems

| Category | Sub-Category | Common Symptoms |
|----------|-------------|-----------------|
| System Failures | Application crashes, memory leaks, deadlocks, data corruption | Service unavailability, resource exhaustion, integrity errors |
| System Failures | Hardware, network, database, security | Connectivity loss, capacity limits, access failures |
| Performance | Response time: slow queries, network latency, algorithmic inefficiency | High p95/p99 latency, user-reported slowness |
| Performance | Throughput: thread pool exhaustion, connection pool limits, queue backlog | Reduced request capacity, growing queues |
| Integration | Internal: component communication, data format, version conflicts | Interface errors, serialization failures |
| Integration | External: third-party availability, API changes, auth failures | Timeout errors, contract violations |

### Operational Problems

| Category | Common Symptoms |
|----------|-----------------|
| Deployment: script failures, config drift, migration errors | Failed releases, environment inconsistencies |
| Monitoring: alerting gaps, backup failures, incident response | Missed incidents, slow recovery |
| Human factors: communication gaps, knowledge silos, skill gaps | Repeated mistakes, slow onboarding |

## Evidence Collection

### Technical Evidence Sources

**Logs**: application logs (with timestamp correlation), system/infrastructure logs, database logs, network traces

**Metrics**: performance and resource utilization, error rates and response time trends, user behavior and transaction patterns, infrastructure health and capacity

**Configuration**: system and deployment settings, code changes and version control history (git log, git blame), environment variables and dependencies, security settings and access controls

### Evidence Validation

1. **Cross-reference**: verify data from multiple independent sources
2. **Timestamp validation**: confirm event sequence accuracy
3. **Completeness check**: identify potential data gaps or corruption
4. **Correlation vs causation**: distinguish patterns that co-occur from patterns that cause each other

## Analysis Techniques

### Quantitative

- **Trend analysis**: time series of performance metrics, frequency of error patterns
- **Distribution analysis**: response time percentiles, error rate distribution across components
- **Pattern recognition**: log anomaly detection, user behavior patterns, error clustering

### Qualitative

- **Timeline reconstruction**: build detailed incident timeline, correlate changes with symptoms
- **Process analysis**: examine workflow disruptions, communication flow, decision chains
- **Environmental analysis**: recent changes, system load, external factors, related incidents

## Solution Design Patterns

### Immediate Mitigations (restore service)
- Quick fixes to restore functionality
- Workarounds to minimize user impact
- Emergency procedures to prevent escalation
- Monitoring enhancements for early warning

### Permanent Fixes (prevent recurrence)
- Architecture modifications to eliminate failure modes
- Code quality improvements and defensive programming
- Configuration management and environment consistency
- Testing and validation process improvements

### Early Detection (catch it faster next time)
- Leading indicator identification and monitoring
- Anomaly detection and predictive alerting
- Automated quality gates at deployment boundaries
- Threshold tuning based on incident learnings

### Solution Prioritization Matrix

| Priority | Criteria | Action |
|----------|----------|--------|
| P0 | Active incident, users impacted | Immediate mitigation within hours |
| P1 | Root cause fix for recurring issue | Permanent fix within current sprint |
| P2 | Prevention for potential issues | Schedule in next sprint |
| P3 | Systemic improvement | Add to backlog with evidence |
