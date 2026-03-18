---
name: nw-investigation-techniques
description: Evidence collection methods, problem categorization, analysis techniques, and solution design patterns
disable-model-invocation: true
---

# Investigation Techniques

## Problem Categorization

### Technical Problems

| Category | Sub-Category | Common Symptoms |
|----------|-------------|-----------------|
| System Failures | App crashes, memory leaks, deadlocks, data corruption | Service unavailability, resource exhaustion, integrity errors |
| System Failures | Hardware, network, database, security | Connectivity loss, capacity limits, access failures |
| Performance | Response time: slow queries, latency, algorithmic inefficiency | High p95/p99, user-reported slowness |
| Performance | Throughput: thread pool exhaustion, connection limits, queue backlog | Reduced capacity, growing queues |
| Integration | Internal: component comms, data format, version conflicts | Interface errors, serialization failures |
| Integration | External: third-party availability, API changes, auth failures | Timeouts, contract violations |

### Operational Problems

| Category | Common Symptoms |
|----------|-----------------|
| Deployment: script failures, config drift, migration errors | Failed releases, environment inconsistencies |
| Monitoring: alerting gaps, backup failures, incident response | Missed incidents, slow recovery |
| Human factors: communication gaps, knowledge silos, skill gaps | Repeated mistakes, slow onboarding |

## Evidence Collection

### Technical Evidence Sources

**Logs**: application (timestamp correlation) | system/infrastructure | database | network traces

**Metrics**: performance/resource utilization | error rates/response time trends | user behavior/transaction patterns | infrastructure health/capacity

**Configuration**: system/deployment settings | code changes/VCS history (git log, blame) | env vars/dependencies | security/access controls

### Evidence Validation
1. **Cross-reference**: verify from multiple independent sources
2. **Timestamp validation**: confirm event sequence accuracy
3. **Completeness check**: identify data gaps/corruption
4. **Correlation vs causation**: distinguish co-occurrence from causation

## Analysis Techniques

### Quantitative
- **Trend**: time series of metrics, error pattern frequency
- **Distribution**: response time percentiles, error rate across components
- **Pattern recognition**: log anomalies, behavior patterns, error clustering

### Qualitative
- **Timeline reconstruction**: detailed incident timeline, correlate changes with symptoms
- **Process analysis**: workflow disruptions, communication flow, decision chains
- **Environmental**: recent changes, system load, external factors, related incidents

## Solution Design Patterns

### Immediate Mitigations (restore service)
Quick fixes | workarounds to minimize impact | emergency procedures | monitoring enhancements

### Permanent Fixes (prevent recurrence)
Architecture modifications | code quality/defensive programming | config management/environment consistency | testing/validation improvements

### Early Detection (catch faster)
Leading indicators | anomaly detection/predictive alerting | automated quality gates | threshold tuning from learnings

### Solution Prioritization Matrix

| Priority | Criteria | Action |
|----------|----------|--------|
| P0 | Active incident, users impacted | Immediate mitigation, hours |
| P1 | Root cause fix for recurring issue | Permanent fix, current sprint |
| P2 | Prevention for potential issues | Next sprint |
| P3 | Systemic improvement | Backlog with evidence |
