---
name: nw-cicd-and-deployment
description: CI/CD pipeline design methodology, deployment strategies, GitHub Actions patterns, and branch/release strategies. Load when designing pipelines or deployment workflows.
disable-model-invocation: true
---

# CI/CD Pipeline Design and Deployment Strategies

## Local Quality Gates

Catch issues at the developer's machine before they reach CI. Local gates mirror the remote commit stage for fast feedback (seconds vs minutes).

### Gate Taxonomy

| Gate | Trigger | Checks | Tools |
|------|---------|--------|-------|
| Pre-commit | `git commit` | Formatting, linting, unit tests, secrets scan | pre-commit, husky, lefthook |
| Pre-push | `git push` | Integration tests, acceptance tests, coverage threshold | pre-commit (push stage), git hooks |
| Local CI | Manual | Full pipeline locally | act (GitHub Actions), gitlab-runner exec |

### Design Principles

- **Mirror, not duplicate**: local gates run the same checks as the remote commit stage, not additional ones. Keeps developer experience consistent with CI.
- **Fast by default**: pre-commit gates target < 30 seconds. Move slow checks (integration, acceptance) to pre-push.
- **Escapable with audit trail**: allow `--no-verify` for emergencies but log skips. CI remains the authoritative gate.
- **Framework selection**: prefer `pre-commit` (Python ecosystem) or `lefthook` (polyglot, fast parallel execution) over raw git hooks. Husky for JS/TS-heavy projects.

### Hook Stage Assignment

```
pre-commit (< 30s):     formatting | linting | unit tests (fast subset) | secrets scan
pre-push   (< 5 min):   full unit suite | integration tests | coverage check | type checking
```

## Pipeline Stages

### Commit Stage (target: < 10 minutes)
Compile/build | Run unit tests (fast, isolated) | Static code analysis (linting, formatting) | Security scanning (SAST, secrets detection) | Generate build artifacts.
Quality gates: build success | 100% unit test pass rate | coverage threshold (e.g., > 80%) | no critical vulnerabilities | no secrets in code.

### Acceptance Stage (target: < 30 minutes)
Deploy to test environment | Run acceptance/integration/contract tests | Security scanning (DAST).
Quality gates: 100% acceptance/integration pass rate | no high/critical security findings | API contracts validated.

### Capacity Stage (target: < 60 minutes, can run parallel)
Performance, load, and stress testing | Chaos engineering experiments.
Quality gates: performance within SLO thresholds | load test pass (expected traffic + margin) | resilience under failure.

### Production Stage
Progressive deployment (canary/blue-green) | Health checks and smoke tests | SLO monitoring during rollout | Automatic rollback on degradation.
Quality gates: health checks pass | SLOs maintained | no error rate increase | latency within bounds.

## Quality Gate Classification

Every quality gate has a category (where it runs), a type (what happens on failure), and a scope (what it protects).

### Gate Taxonomy

| Category | Stage | Type | Examples |
|----------|-------|------|----------|
| Local | Pre-commit, pre-push | Blocking (developer) | Format, lint, unit tests, secrets scan |
| PR | Pull request | Blocking (merge) | Status checks, review approvals, coverage diff |
| CI | Commit stage | Blocking (pipeline) | Build, unit tests, SAST, coverage threshold |
| CI | Acceptance stage | Blocking (pipeline) | Integration, acceptance, contract tests, DAST |
| Deploy | Environment promotion | Blocking (approval) | Manual approval, change advisory board |
| Deploy | Canary/progressive | Automatic (rollback) | Error rate, latency, SLO breach |
| Production | Post-deploy | Advisory (monitoring) | Smoke tests, SLO monitoring window, business metrics |

### Gate Types

- **Blocking**: pipeline halts on failure. Merge/deploy/promotion is prevented until resolved.
- **Automatic (rollback)**: no human intervention -- system rolls back on threshold breach. Requires pre-defined thresholds and rollback automation.
- **Advisory**: failure is reported but does not block. Used for post-deploy monitoring where rollback is a separate decision.

### Design Checklist

When designing quality gates for a pipeline, verify:
1. Every remote CI gate has a local equivalent (pre-commit or pre-push)
2. PR gates include both automated checks (status checks) and human review (approvals)
3. Deployment gates distinguish blocking (promotion) from automatic (canary rollback)
4. Post-deploy gates have clear escalation paths (advisory -> manual rollback decision)
5. Gate thresholds are documented and versioned (not hardcoded in pipeline YAML)

## GitHub Actions Patterns

### Workflow Structure
Triggers: push to main/develop | pull_request | release tags | manual workflow_dispatch.
Jobs flow: build -> security -> deploy_staging -> deploy_production. Each with appropriate `needs` dependencies and environment gates.

### Quality Gate Pattern
```yaml
- name: Quality Gate
  run: |
    COVERAGE=$(jq '.totals.percent_covered' coverage.json)
    if (( $(echo "$COVERAGE < 80" | bc -l) )); then
      echo "Coverage $COVERAGE% is below 80% threshold"
      exit 1
    fi
```

### Caching Pattern
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

### Matrix Testing Pattern
```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
    os: [ubuntu-latest, macos-latest]
```

## Deployment Strategies

### Rolling Deployment
Gradual replacement of instances. Kubernetes config: `type: RollingUpdate`, `maxSurge: 25%`, `maxUnavailable: 0`.
- Pros: zero downtime | simple | efficient resources
- Cons: slow rollback | mixed versions during deployment
- Use when: stateless services | no breaking API changes | low-risk changes

### Blue-Green Deployment
Two identical environments, instant switch: Blue (current) serves traffic -> Deploy new to Green -> Smoke tests on Green -> Switch load balancer -> Blue becomes standby/rollback.
- Pros: instant rollback | easy pre-switch testing | clean version separation
- Cons: requires 2x resources | database migrations need care
- Use when: instant rollback needed | critical services | regulated environments

### Canary Deployment
Gradual traffic shift: 5% -> 25% -> 50% -> 100%, monitoring metrics at each step.

Argo Rollouts config:
```yaml
spec:
  strategy:
    canary:
      steps:
      - setWeight: 5
      - pause: {duration: 10m}
      - setWeight: 25
      - pause: {duration: 10m}
      - setWeight: 50
      - pause: {duration: 10m}
      - setWeight: 100
      analysis:
        templates:
        - templateName: success-rate
```

- Pros: low blast radius | real traffic validation | automatic rollback
- Cons: more complex | requires good observability
- Use when: high-traffic services | real-world validation needed | risk-sensitive

### Progressive Delivery
Feature flags + canary + automatic rollback. Components: feature flags for gradual rollout | canary analysis for automatic decisions | SLO monitoring for health validation.
Tools: Argo Rollouts | Flagger | LaunchDarkly/Flagsmith.

## Branch and Release Strategies

Select branching strategy matching team maturity, release cadence, and risk profile. Shapes pipeline triggers, environment promotion, and release automation.

### Trunk-Based Development
Single main branch, short-lived feature branches (< 1 day). Direct commits to main allowed with protection. Releases from main via tags.
- **CI/CD**: Every commit to main triggers full pipeline. Requires robust automated gates since main always releasable. Feature flags manage incomplete work.
- **Triggers**: `push: [main]`, `tags: ['v*']`
- Use when: high-performing teams | continuous deployment | mature test suites.

### GitHub Flow
Feature branches from main, PRs with review, merge to main after approval. Releases from main.
- **CI/CD**: PR-triggered pipelines run commit + acceptance stages. Merge to main triggers deployment. Requires PR quality gates.
- **Triggers**: `pull_request: [main]`, `push: [main]`
- Use when: teams practicing continuous delivery with code review culture.

### GitFlow
Structured branches: main (production) | develop (integration) | feature/* | release/* | hotfix/*.
- **CI/CD**: Branch-specific pipelines. Feature branches: commit stage only. Develop: commit + acceptance. Release: full pipeline. Hotfix: commit + acceptance with fast-track to production.
- **Triggers**: `push: [main, develop, 'release/**', 'hotfix/**']`, `pull_request: [develop]`
- Use when: scheduled releases | multiple versions in production | regulated environments.

### Release Branching
Long-lived release branches (e.g., `release/1.x`, `release/2.x`), cherry-pick fixes between branches.
- **CI/CD**: Per-branch pipelines with independent deployment targets. Cross-branch validation when cherry-picking.
- **Triggers**: `push: [main, 'release/**']`
- Use when: supporting multiple product versions | enterprise software with customer-specific releases.

### Branch Protection Rules (main)
Require PR reviews (2+ approvers) | Require status checks to pass | Require signed commits | Require linear history | Restrict force pushes and deletions.

### Release Workflow
Semantic versioning (MAJOR.MINOR.PATCH): Create release branch -> Bump version -> Update CHANGELOG -> Run full test suite -> Create release tag -> Deploy to production -> Merge back to main.

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
**Before**: Analyze impact on test discovery | Identify affected measurement tools (coverage, mutation testing) | Document current baseline metrics.
**During**: Adjust coverage thresholds for new execution model | Validate measurement strategy compatibility | Recalibrate quality gate thresholds.
**After**: Establish new baseline metrics | Validate measurement accuracy against known scenarios | Update runbooks with measurement strategy changes.

## Simplest Solution Check for Infrastructure

Before proposing multi-service infrastructure (>3 components), document rejected simple alternatives:
- Single-service deployment (no orchestration) | Managed services instead of self-hosted
- Simple CI/CD (no canary/blue-green) | Monolithic deployment (no microservices infrastructure)

Format:
```markdown
## Rejected Simple Alternatives

### Alternative 1: {Simplest possible approach}
- **What**: {description}
- **Expected Impact**: {what % of requirements this meets}
- **Why Insufficient**: {specific, evidence-based reason}
```
