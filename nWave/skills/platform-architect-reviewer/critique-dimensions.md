---
name: critique-dimensions
description: Platform design review critique dimensions and severity levels. Load when reviewing CI/CD pipelines, infrastructure, deployment strategies, observability, or security designs.
---

# Platform Design Critique Dimensions

## Dimension 1: CI/CD Pipeline Completeness

Questions: Are all stages defined (commit, acceptance, capacity, production)? Are quality gates explicit with pass/fail criteria? Is parallelization used to reduce feedback time? Are failure recovery and retry mechanisms documented? Is commit stage < 10 min, acceptance stage < 30 min?

Blocker: Missing critical stage (no acceptance tests), no quality gates, no security scanning.
Critical: Pipeline > 30 min without parallelization, no failure notification, missing artifact versioning.
High: No caching strategy, incomplete environment parity, missing matrix testing.
Medium: Inconsistent naming, missing documentation for manual steps.

## Dimension 2: Infrastructure as Code Quality

Questions: Is infrastructure fully codified? Are modules reusable and parameterized? Is state management secure (encrypted, locked)? Are security best practices followed (least privilege, encryption)? Is infrastructure idempotent and reproducible?

Blocker: Secrets in version control, no state management, production credentials in code.
Critical: No encryption at rest, overly permissive IAM, missing network security.
High: Hardcoded values, missing resource tagging, no cost estimation.
Medium: Inconsistent module structure, missing input variable validation.

## Dimension 3: Deployment Strategy Risk

Questions: Is the strategy appropriate for the risk profile? Is rollback documented? Are health checks and readiness probes defined? Is traffic shifting gradual with automatic rollback? Are database migrations backward compatible?

Blocker: No rollback strategy, no health checks, breaking changes without safeguards.
Critical: Single-shot deployment for critical services, no canary/blue-green for high-traffic, missing pod disruption budgets.
High: Rollback not tested, no gradual traffic shifting, no pre-deployment validation.
Medium: Incomplete manual step documentation, no feature flags for risky features.

## Dimension 4: Observability and SLO Alignment

Questions: Are SLOs defined with specific targets? Are all four golden signals monitored (latency, traffic, errors, saturation)? Is distributed tracing configured? Are alerts SLO burn-rate based? Are dashboards designed for investigation?

Blocker: No SLOs defined, no error rate monitoring, no alerting strategy.
Critical: No latency monitoring (p50/p90/p99), symptom-based alerts, no log-metric-trace correlation.
High: Incomplete metric coverage, alert thresholds misaligned with SLOs, no runbook links.
Medium: Unclear dashboard organization, missing error budget tracking.

## Dimension 5: Pipeline and Infrastructure Security

Questions: Is SAST in commit stage? Is DAST before production? Is SCA configured? Is secrets management using external vault? Is SBOM generated and signed?

Blocker: No security scanning, secrets in env vars or code, no container image scanning.
Critical: Missing SAST in CI, no dependency vulnerability scanning, missing K8s network policies.
High: No DAST before production, no SBOM generation, no image signing.
Medium: Security scan results not blocking deployment, no license compliance.

## Dimension 6: DORA Metrics Enablement

Questions: Does the design enable multiple deployments per day? Can lead time be < 1 hour? Are change failure rate tracking mechanisms in place? Is time to restore measurable with SLOs?

Critical: Manual steps preventing daily deployments, no automated testing for fast feedback, no deployment failure tracking.
High: Pipeline > 1 hour for full deployment, no post-deployment validation, missing deployment frequency metrics.

## Dimension 7: Priority and Constraint Validation

Questions: Does the design address the largest bottleneck first? Were simpler alternatives documented and rejected with evidence? Is constraint prioritization correct? Is complexity justified?

Critical: Design addresses secondary concern while larger exists, no measurement data, simple alternatives not documented.
High: Constraint prioritization not explicit, over-engineered for stated requirements.
