---
name: platform-engineering-foundations
description: Foundational platform engineering knowledge from key references -- Continuous Delivery, SRE, Accelerate, Team Topologies, Chaos Engineering, and Secure Delivery. Load when contextual grounding in platform engineering theory is needed.
---

# Platform Engineering Foundations

## Continuous Delivery (Humble and Farley)

Key principles:
- Build quality in -- quality is everyone's responsibility
- Work in small batches -- reduce risk through small, frequent changes
- Automate almost everything -- manual processes are error-prone
- Pursue continuous improvement -- always seek to improve
- Everyone is responsible -- shared ownership of delivery

Pipeline pattern progression:
1. Commit Stage: build, unit tests, code analysis (< 10 min)
2. Acceptance Stage: automated acceptance tests, component tests
3. Capacity Stage: performance, load, stress testing
4. Production Stage: blue-green, canary deployments

## Site Reliability Engineering (Google -- Beyer et al.)

Key principles:
- SLOs over SLAs -- internal targets stricter than external promises
- Error budgets -- balance reliability and velocity
- Toil elimination -- automate repetitive manual work
- Embrace risk -- calculate risk, do not eliminate it

Observability patterns:
- Four Golden Signals: latency, traffic, errors, saturation
- SLI -> SLO -> Error Budget -> Alerting chain
- Dashboards for investigation, not monitoring

## Accelerate (Forsgren, Humble, Kim)

### DORA Metrics
- **Deployment frequency**: How often code is deployed to production
- **Lead time for changes**: Time from commit to production
- **Change failure rate**: Percentage of deployments causing failure
- **Time to restore**: Time to recover from production failure

### Performance Levels

| Metric | Elite | High |
|--------|-------|------|
| Deployment frequency | Multiple times/day | Daily to weekly |
| Lead time | < 1 hour | 1 day to 1 week |
| Change failure rate | 0-15% | 16-30% |
| Time to restore | < 1 hour | < 1 day |

Use DORA metrics as baselines when assessing current state and setting improvement targets.

## Team Topologies (Skelton and Pais)

### Team Types
- **Stream-aligned**: Delivers value to customer, owns full lifecycle
- **Platform**: Provides self-service capabilities, reduces cognitive load
- **Enabling**: Helps teams adopt new practices, temporary engagement
- **Complicated subsystem**: Owns complex technical domain

### Platform Principles
- Platform as a product -- internal developer platform
- Self-service with guardrails
- Reduce cognitive load on stream-aligned teams
- Thinnest viable platform

Use when designing platform team structures and determining which capabilities to centralize vs delegate.

## Chaos Engineering (Rosenthal et al.)

Principles:
- Build hypothesis about steady state
- Vary real-world events
- Run experiments in production
- Automate experiments continuously

Practices:
- GameDays -- scheduled chaos experiments
- Fault injection -- network latency, failures
- Chaos monkey -- random instance termination

## Secure Delivery (Building Secure and Reliable Systems)

Principles:
- Least privilege -- minimal permissions
- Defense in depth -- multiple security layers
- Zero trust -- verify explicitly, assume breach

Pipeline security integration:
- SAST in CI for static analysis
- DAST pre-production for dynamic analysis
- SCA for dependency vulnerabilities
- Secrets scanning to prevent credential leaks
- SBOM for supply chain transparency

## GitOps (GitOps and Kubernetes)

Principles:
- Declarative desired state in Git
- Automated reconciliation
- Drift detection and correction
- Pull-based deployments

Tools: ArgoCD (Kubernetes-native GitOps CD), Flux (GitOps toolkit for Kubernetes).

Patterns:
- App of Apps pattern for multi-environment management
- Helm with GitOps for parameterization
- Kustomize overlays for environment differences

## Constraint Impact Analysis Template

Use when assessing platform constraints before designing infrastructure.

```markdown
## Platform Constraint Impact Analysis

| Constraint | Source | % Delivery Affected | Priority |
|------------|--------|---------------------|----------|
| {constraint} | {architecture/ops/security} | {X}% | {HIGH/MEDIUM/LOW} |

### Constraint-Free Baseline
- Maximum theoretical deployment frequency: ___
- Components that can proceed without constraints: ___ ({X}%)
- Quick wins available now: ___

### Decision Rules
- Constraint affects > 50% of delivery: address as primary focus
- Constraint affects < 50% of delivery: address as secondary
- Constraint affects < 20% of delivery: consider deferring

### Recommendation
Primary focus should be: {constraint-free opportunities or primary constraint}
```
