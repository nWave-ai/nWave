---
description: "Designs CI/CD pipelines, infrastructure, observability, and deployment strategy. Use when preparing platform readiness for a feature."
argument-hint: "[deployment-target] - Optional: --environment=[staging|production] --validation=[full|smoke]"
---

# NW-DEVOPS: Platform Readiness and Infrastructure Design

**Wave**: DEVOPS (wave 4 of 6) | **Agent**: Apex (nw-platform-architect) | **Command**: `/nw:devops`

## Overview

Execute DEVOPS wave: platform readiness|CI/CD pipeline setup|observability design|infrastructure preparation. Positioned between DESIGN and DISTILL (DISCOVER > DISCUSS > DESIGN > DEVOPS > DISTILL > DELIVER), ensures infrastructure is ready before acceptance tests and code.

Apex translates DESIGN architecture decisions into operational infrastructure: CI/CD pipelines|logging|monitoring|alerting|observability.

## Interactive Decision Points

Before proceeding, the orchestrator asks:

### Decision 1: Deployment Target
**Question**: What is the deployment target?
**Options**:
1. Cloud-native -- AWS, GCP, Azure managed services
2. On-premise -- self-hosted infrastructure
3. Hybrid -- mix of cloud and on-premise
4. Edge -- distributed edge deployment
5. Other -- user provides custom input

### Decision 2: Container Orchestration
**Question**: Container orchestration approach?
**Options**:
1. Kubernetes -- full orchestration
2. Docker Compose -- lightweight container management
3. Serverless -- function-as-a-service, no containers
4. None -- bare metal or VM-based deployment

### Decision 3: CI/CD Platform
**Question**: CI/CD platform preference?
**Options**:
1. GitHub Actions
2. GitLab CI
3. Jenkins
4. Azure DevOps
5. Other -- user provides custom input

### Decision 4: Existing Infrastructure
**Question**: Is there existing infrastructure or CI/CD to integrate with?
**Options**:
1. Yes, both -- describe existing infrastructure and CI/CD (user provides details)
2. Existing infra only -- infrastructure exists, CI/CD is greenfield
3. Existing CI/CD only -- CI/CD exists, infrastructure is greenfield
4. No -- greenfield, design everything from scratch

### Decision 5: Observability and Logging
**Question**: What observability and logging approach?
**Options**:
1. Prometheus + Grafana (metrics) with structured JSON logs
2. Datadog (full-stack observability including logs)
3. ELK stack (Elasticsearch, Logstash, Kibana for logs and metrics)
4. OpenTelemetry (vendor-agnostic telemetry) with provider of choice
5. CloudWatch (AWS-native metrics and logging)
6. Custom -- user provides details
7. None -- defer observability setup

### Decision 6: Deployment Strategy
**Question**: What deployment strategy?
**Options**:
1. Blue-green -- zero-downtime with environment swap
2. Canary -- gradual traffic shifting
3. Rolling -- incremental pod/instance replacement
4. Recreate -- simple stop-and-replace

### Decision 7: Continuous Learning (conditional)
**Question**: Is there existing monitoring/alerting infrastructure in place?
**Options**:
1. Yes -- include continuous learning and experimentation capabilities
2. No -- focus on foundational monitoring setup first

If Yes to Decision 7:
**Follow-up**: Which continuous learning capabilities to include?
**Options**:
1. A/B testing framework
2. Feature flags (LaunchDarkly, Unleash, custom)
3. Canary analysis (automated rollback on metrics)
4. Progressive rollout (percentage-based deployment)
5. All of the above

### Decision 8: Git Branching Strategy
**Question**: What Git branching strategy should the project follow?
**Options**:
1. Trunk-Based Development -- single main branch, short-lived feature branches (<1 day), continuous integration. Requires robust CI gates on every commit.
2. GitHub Flow -- feature branches from main, pull requests, merge to main after review. Balanced CI with PR-triggered pipelines.
3. GitFlow -- develop/main branches, feature/release/hotfix branches, formal release process. Requires branch-specific pipelines (develop CI, release candidate, hotfix fast-track).
4. Release Branching -- long-lived release branches, cherry-pick fixes between branches. Requires per-branch pipelines and cross-branch validation.
5. Other -- user provides custom strategy

This directly influences CI/CD pipeline design: trigger rules|branch protection|environment promotion|release automation.

### Decision 9: Mutation Testing Strategy
**Question**: When should mutation testing run?
**Options**:
1. **per-feature** (default) -- Runs after each feature delivery (refactoring + review), scoped to modified files. Best for small/medium projects where per-feature overhead is acceptable. Fastest feedback loop but adds ~5-15 min per delivery.
2. **nightly-delta** -- Runs in CI nightly on files modified that day. Best for large projects where per-feature mutation testing is too slow. Delays feedback but keeps delivery fast.
3. **pre-release** -- Runs before each release on the entire solution. Best for projects with long release cycles where comprehensive mutation coverage matters most at release boundaries. Slowest feedback but most thorough.
4. **disabled** -- No mutation testing. Only appropriate for prototypes, spikes, or projects where test quality is validated through other means.

After selection, Apex asks permission to write to project CLAUDE.md under `## Mutation Testing Strategy`:

**per-feature**: `This project uses **per-feature** mutation testing. Runs after refactoring during each delivery, scoped to modified files. Kill rate gate: >= 80%.`

**nightly-delta**: `This project uses **nightly-delta** mutation testing. CI runs on files modified each day. NOT run during feature delivery.`

**pre-release**: `This project uses **pre-release** mutation testing. Runs on entire solution before each release. Delivery not blocked.`

**disabled**: `Mutation testing is **disabled**. Test quality validated through code review and CI coverage.`

Default if not chosen: **per-feature**.

## Context Files Required

- docs/feature/{feature-id}/design/architecture-design.md
- docs/feature/{feature-id}/design/technology-stack.md
- docs/feature/{feature-id}/design/component-boundaries.md

## Previous Artifacts (Wave Handoff)

- docs/feature/{feature-id}/design/* — Complete architecture from DESIGN

## Agent Invocation

@nw-platform-architect

Execute platform readiness and infrastructure design for {feature-id}.

Context files: see Context Files Required above.

**Configuration:**
- deployment_target: {Decision 1} | container_orchestration: {Decision 2}
- cicd_platform: {Decision 3} | existing_infrastructure: {Decision 4}
- observability_and_logging: {Decision 5} | deployment_strategy: {Decision 6}
- continuous_learning: {Decision 7} | git_branching_strategy: {Decision 8}
- mutation_testing_strategy: {Decision 9}

## Success Criteria

- [ ] CI/CD pipeline design finalized and documented
- [ ] Logging infrastructure design complete (structured logging|aggregation)
- [ ] Monitoring and alerting design complete (metrics|dashboards|SLOs/SLIs)
- [ ] Observability design complete (distributed tracing|health checks)
- [ ] Infrastructure integration assessed (if existing infra)
- [ ] Continuous learning capabilities designed (if applicable)
- [ ] Git branching strategy selected and CI/CD triggers aligned
- [ ] Mutation testing strategy selected and persisted to project CLAUDE.md
- [ ] Handoff accepted by nw-acceptance-designer (DISTILL wave)

## Next Wave

**Handoff To**: nw-acceptance-designer (DISTILL wave)
**Deliverables**: Infrastructure design documents informing test environment setup

## Examples

### Example 1: Cloud-native greenfield
```
/nw:devops payment-gateway
```
User selects: cloud-native, Kubernetes, GitHub Actions, no existing infra, OpenTelemetry, blue-green, trunk-based development. Apex designs full infrastructure from scratch with robust CI gates on every commit to main.

### Example 2: Brownfield with existing CI/CD
```
/nw:devops auth-upgrade
```
User selects: hybrid, Docker Compose, GitLab CI (existing), existing CI/CD only, Datadog, rolling, GitFlow. Apex extends existing pipelines with branch-specific stages for develop, release, and hotfix branches.

## Expected Outputs

```
docs/feature/{feature-id}/devops/
  platform-architecture.md
  ci-cd-pipeline.md
  observability-design.md
  monitoring-alerting.md
  infrastructure-integration.md    (if existing infra)
  branching-strategy.md
  continuous-learning.md           (if applicable)
```
