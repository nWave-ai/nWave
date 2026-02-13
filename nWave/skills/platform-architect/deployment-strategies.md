---
name: deployment-strategies
description: Deployment patterns (canary, blue-green, rolling), rollback procedures, risk assessment, and contingency planning. Load when orchestrating deployment or preparing rollback plans.
---

# Deployment Strategies

## Pre-Deployment Validation

Before any deployment, validate:
- Deployment scripts tested in staging
- Database migrations tested with rollback scripts
- Configuration management consistent across environments
- Health checks and service discovery configured
- Monitoring and alerting systems prepared
- Backup and disaster recovery procedures validated

## Staged Deployment Patterns

### Canary Deployment
- Route 5-10% of traffic to new version
- Monitor: error rates, latency, business metrics
- Duration: minimum 30 minutes at each stage
- Expansion: 5% --> 25% --> 50% --> 100%
- Rollback: immediate traffic reroute to stable version
- Best for: high-risk changes, API modifications, performance-sensitive features

### Blue-Green Deployment
- Maintain two identical environments (blue = current, green = new)
- Deploy to green, validate, switch traffic
- Rollback: switch traffic back to blue
- Requires: full environment duplication, data synchronization strategy
- Best for: zero-downtime requirements, major version upgrades

### Rolling Deployment
- Replace instances one at a time
- Health monitoring per instance after replacement
- Automatic rollback triggers on health check failure
- Best for: stateless services, horizontal scaling architectures

## Rollback Procedures

### Design Rollback First
Every deployment plan starts with the rollback section:

1. **Database rollback**: migration revert scripts tested and verified
2. **Application rollback**: previous version tagged and deployable
3. **Configuration rollback**: previous config snapshots available
4. **Traffic rollback**: load balancer / feature flag kill switch ready
5. **Data rollback**: data consistency plan for partial rollback scenarios

### Automated Rollback Triggers
Configure automatic rollback when:
- Error rate exceeds baseline by >2x
- P95 latency exceeds SLA threshold
- Health check failures exceed threshold (e.g., 3 consecutive)
- Business metric anomaly detected (e.g., conversion drop >10%)

### Manual Rollback Decision Criteria
- Stakeholder-reported functional issues
- Security vulnerability discovered post-deploy
- Data integrity concerns
- Performance degradation below acceptable levels

## Risk Assessment

### Technical Risks
- Integration failure with downstream services
- Performance degradation under production load
- Data migration integrity issues
- Security vulnerabilities introduced

### Business Risks
- User adoption challenges
- Business process disruption
- Stakeholder expectation misalignment

### Operational Risks
- Infrastructure capacity limitations
- Third-party dependency failures
- Team availability for incident response

### Risk Mitigation Checklist
- [ ] Rollback procedure designed and tested
- [ ] Monitoring dashboards configured for deployment
- [ ] On-call team notified of deployment window
- [ ] Feature flags configured for gradual rollout
- [ ] Communication plan for stakeholders prepared
- [ ] Incident response runbook updated

## Post-Deployment Validation

### Production Smoke Tests
- Critical user paths validated
- Integration points tested with real external systems
- Performance validated under production load
- Security controls verified
- Data integrity confirmed

### Monitoring Validation
- Application performance metrics collecting
- Error tracking and alerting active
- Business metric dashboards updated
- Infrastructure monitoring nominal
