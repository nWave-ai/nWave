---
name: nw-par-critique-dimensions
description: Platform design review critique dimensions and severity levels. Load when reviewing CI/CD pipelines, infrastructure, deployment strategies, observability, or security designs.
disable-model-invocation: true
---

# Platform Design Critique Dimensions

## Dimension 1: CI/CD Pipeline Completeness

Questions: All stages defined (commit, acceptance, capacity, production)? Quality gates explicit with pass/fail criteria? Parallelization used? Failure recovery/retry documented? Commit stage < 10 min, acceptance < 30 min?

Blocker: Missing critical stage (no acceptance tests) | no quality gates | no security scanning.
Critical: Pipeline > 30 min without parallelization | no failure notification | missing artifact versioning.
High: No caching strategy | incomplete environment parity | missing matrix testing.
Medium: Inconsistent naming | missing documentation for manual steps.

## Dimension 2: Infrastructure as Code Quality

Questions: Infrastructure fully codified? Modules reusable and parameterized? State management secure (encrypted, locked)? Security best practices (least privilege, encryption)? Idempotent and reproducible?

Blocker: Secrets in version control | no state management | production credentials in code.
Critical: No encryption at rest | overly permissive IAM | missing network security.
High: Hardcoded values | missing resource tagging | no cost estimation.
Medium: Inconsistent module structure | missing input variable validation.

## Dimension 3: Deployment Strategy Risk

Questions: Strategy appropriate for risk profile? Rollback documented? Health checks and readiness probes defined? Gradual traffic shifting with automatic rollback? Database migrations backward compatible?

Blocker: No rollback strategy | no health checks | breaking changes without safeguards.
Critical: Single-shot deployment for critical services | no canary/blue-green for high-traffic | missing pod disruption budgets.
High: Rollback not tested | no gradual traffic shifting | no pre-deployment validation.
Medium: Incomplete manual step documentation | no feature flags for risky features.

## Dimension 4: Observability and SLO Alignment

Questions: SLOs defined with specific targets? All four golden signals monitored? Distributed tracing configured? Alerts SLO burn-rate based? Dashboards for investigation?

Blocker: No SLOs defined | no error rate monitoring | no alerting strategy.
Critical: No latency monitoring (p50/p90/p99) | symptom-based alerts | no log-metric-trace correlation.
High: Incomplete metric coverage | alert thresholds misaligned with SLOs | no runbook links.
Medium: Unclear dashboard organization | missing error budget tracking.

## Dimension 5: Pipeline and Infrastructure Security

Questions: SAST in commit stage? DAST before production? SCA configured? Secrets management using external vault? SBOM generated and signed?

Blocker: No security scanning | secrets in env vars or code | no container image scanning.
Critical: Missing SAST in CI | no dependency vulnerability scanning | missing K8s network policies.
High: No DAST before production | no SBOM generation | no image signing.
Medium: Security scan results not blocking deployment | no license compliance.

## Dimension 6: DORA Metrics Enablement

Questions: Design enables multiple deployments/day? Lead time < 1 hour achievable? Change failure rate tracking in place? Time to restore measurable with SLOs?

Critical: Manual steps preventing daily deployments | no automated testing for fast feedback | no deployment failure tracking.
High: Pipeline > 1 hour for full deployment | no post-deployment validation | missing deployment frequency metrics.

## Dimension 7: Priority and Constraint Validation

Questions: Design addresses largest bottleneck first? Simpler alternatives documented and rejected with evidence? Constraint prioritization correct? Complexity justified?

Critical: Design addresses secondary concern while larger exists | no measurement data | simple alternatives not documented.
High: Constraint prioritization not explicit | over-engineered for stated requirements.
