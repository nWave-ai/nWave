---
name: nw-devops
description: "Designs CI/CD pipelines, infrastructure, observability, and deployment strategy. Use when preparing platform readiness for a feature."
user-invocable: true
argument-hint: '[deployment-target] - Optional: --environment=[staging|production] --validation=[full|smoke]'
---

# NW-DEVOPS: Platform Readiness and Infrastructure Design

**Wave**: DEVOPS (wave 4 of 6) | **Agent**: Apex (nw-platform-architect) | **Command**: `/nw-devops`

## Overview

Execute DEVOPS wave: platform readiness|CI/CD pipeline setup|observability design|infrastructure preparation. Positioned between DESIGN and DISTILL (DISCOVER > DISCUSS > SPIKE > DESIGN > DEVOPS > DISTILL > DELIVER), ensures infrastructure is ready before acceptance tests and code.

Apex translates DESIGN architecture decisions into operational infrastructure: CI/CD pipelines|logging|monitoring|alerting|observability.

## Output Tiers (per D2)

Provenance: feature `lean-wave-documentation` — D2 (schema-typed sections), D10 (one-line expansion descriptions). Tier-1 [REF] sections (always emitted) + Tier-2 EXPANSION CATALOG items (lazy, on-demand) are the two output bands. Full contract: `nWave/skills/nw-density-resolution-contract/SKILL.md`.

### Tier-1 [REF] — always emitted

Under `## Wave: DEVOPS / [REF] <Section>` headings:

- Environment matrix — table of target environments with platform + preconditions
- CI/CD pipeline outline — stage list with trigger rules per branch
- Monitoring contracts — KPI-to-instrument mapping (one row per outcome KPI)
- Deployment strategy — chosen strategy + rollback contract (one paragraph)
- Mutation testing strategy — selected mode (per-feature/nightly-delta/pre-release/disabled)
- Observability stack — chosen tools per signal class (logs/metrics/traces)
- Branching strategy — selected model + CI trigger alignment
- Coexistence matrix — tools that must continue to work alongside deployment
- Pre-requisites — DESIGN constraints the platform must satisfy

### Tier-2 EXPANSION CATALOG — lazy, on-demand (per D10)

Rendered under `## Wave: DEVOPS / [WHY|HOW] <Section>` only when requested via `--expand <id>` (DDD-2), the wave-end menu (`expansion_prompt = "ask"`), `mode = "full"` auto-expansion, or an ad-hoc user request mid-session.

| Expansion ID | Tier label | One-line description |
|---|---|---|
| `infra-cost-analysis` | [WHY] | Per-environment monthly cost estimate with vendor pricing assumptions |
| `alternative-deploy-targets` | [WHY] | Cloud/on-prem/hybrid options weighed and rejected with one-paragraph reason |
| `observability-deep-dive` | [HOW] | Detailed metric/log/trace schemas, alert thresholds, dashboard layouts |
| `runbook-drafts` | [HOW] | Incident response runbooks for the top failure modes |
| `kpi-instrumentation-recipes` | [HOW] | Per-KPI data collection recipe (event names, log fields, metric labels) |
| `ci-pipeline-yaml` | [HOW] | Full CI/CD pipeline YAML with comments per stage |
| `disaster-recovery-plan` | [HOW] | Backup, restore, and DR procedures with RPO/RTO targets |
| `expansion-catalog-rationale` | [WHY] | Why this set of expansions, why these defaults, why D10 enforces one-line descriptions |

## Density resolution (per D12)

Call `resolve_density(global_config)` from `scripts/shared/density_config.py` after reading `~/.nwave/global-config.json` (missing/malformed = empty dict). Returns `mode` (`"lean"` | `"full"`) + `expansion_prompt` (`"ask"` | `"always-skip"` | `"always-expand"` | `"smart"`) per the D12 cascade (resolver-internal, DDD-5 — do NOT replicate locally). Branch on `density.mode` for what to emit; branch on `density.expansion_prompt` at wave end for menu behaviour. Full cascade detail, branch semantics, ad-hoc override workflow: `nWave/skills/nw-density-resolution-contract/SKILL.md`.

## Telemetry (per D4 + DDD-6)

Every expansion choice emits a `DocumentationDensityEvent` (dataclass at `src/des/domain/telemetry/documentation_density_event.py`) via `event.to_audit_event()` → `JsonlAuditLogWriter().log_event(...)`. Schema fields per D4: `feature_id`, `wave`, `expansion_id`, `choice`, `timestamp`. For this wave the schema declares `"wave": "DEVOPS"`. Use helper `scripts/shared/telemetry.py:write_density_event(...)` — do NOT write JSONL directly.

Wave-specific signal: DISTILL consuming a lean DEVOPS environment matrix — downstream `--expand` requests for runbook drafts or alternative deploy targets indicate the `[REF]` baseline was insufficient. Full emission rules: `nWave/skills/nw-density-resolution-contract/SKILL.md`.

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

## Prior Wave Consultation

Before beginning DEVOPS work, read targeted prior wave artifacts:

1. **DISCOVER** (skip): DESIGN already synthesizes DISCOVER+DISCUSS into architecture. Not needed for infrastructure design.
2. **DISCUSS** (KPIs only): Read `docs/feature/{feature-id}/discuss/outcome-kpis.md` — drives observability and instrumentation design.
3. **DESIGN** (primary input): Read all files in `docs/feature/{feature-id}/design/` — architecture drives infrastructure decisions.

**READING ENFORCEMENT**: Read every file listed above using the Read tool before proceeding. After reading, output a confirmation checklist (`✓ {file}` for each read, `⊘ {file} (not found)` for missing). Do NOT skip files that exist — skipping causes infrastructure decisions disconnected from architecture.

After reading, check whether any DEVOPS decisions would contradict DESIGN architecture. Flag contradictions and resolve with user before proceeding. Example: DESIGN specifies "single-region deployment" but DEVOPS discovers latency requirements from outcome-kpis.md that demand multi-region — this must be resolved.

## Document Update (Back-Propagation)

When DEVOPS decisions change assumptions from prior waves:

1. **Document change** — Add a `## Changed Assumptions` section at the end of the affected DEVOPS artifact. Gate: section present in artifact.
2. **Reference original** — Quote the original prior-wave document and the original assumption. Gate: quote included.
3. **State new assumption** — Write the new assumption and rationale for the change. Gate: rationale documented.
4. **Flag upstream changes** — If infrastructure constraints require architecture changes, write them to `docs/feature/{feature-id}/devops/upstream-changes.md` for the architect to review. Gate: file created if architecture impact exists.

## Agent Invocation

1. **Dispatch** — Invoke `@nw-platform-architect` with the feature-id and configuration below. Gate: agent accepts invocation.
2. **Provide context** — Pass all prior wave consultation files (see Prior Wave Consultation). Gate: context files attached.
3. **Pass configuration** — Include all Decision 1-9 selections in the invocation:
   - deployment_target: {Decision 1} | container_orchestration: {Decision 2}
   - cicd_platform: {Decision 3} | existing_infrastructure: {Decision 4}
   - observability_and_logging: {Decision 5} | deployment_strategy: {Decision 6}
   - continuous_learning: {Decision 7} | git_branching_strategy: {Decision 8}
   - mutation_testing_strategy: {Decision 9}
4. **KPI-driven observability** — If `outcome-kpis.md` exists in the feature's discuss directory, Apex MUST read it and design instrumentation to collect the defined KPIs. Each KPI's "Measured By" and "Measurement Plan" sections drive: data collection infrastructure (events, logs, analytics), dashboard design (which metrics to visualize), alerting rules (guardrail metric thresholds). Gate: all KPIs have corresponding instrumentation design.

## Mandatory Deliverable: Environment Inventory

BEFORE completing the DEVOPS wave, produce the environment inventory:

1. **Create file** — Write `docs/feature/{feature-id}/devops/environments.yaml` with the structure below. Gate: file written.
2. **Populate target environments** — List all deployment environments with name, description, platform, and preconditions. Gate: at least one environment entry present.
3. **Define coexistence matrix** — List tools that must not break alongside the deployment (e.g., pre-commit, husky). Gate: matrix present.
4. **Specify platform coverage** — List OS/platform versions to support. Gate: coverage table complete.
5. **Document deployment assumptions** — List idempotency, uninstall safety, and hook coexistence requirements. Gate: assumptions enumerated.

```yaml
# environments.yaml — consumed by DISTILL for Mandate 4 (Environmental Realism)
target_environments:
  - name: clean
    description: "Fresh install, no prior state"
    platform: [linux, macos, wsl]
    preconditions: []
  - name: with-pre-commit
    description: "Pre-commit hooks installed and active"
    platform: [linux, macos, wsl]
    preconditions: ["pre-commit installed", "core.hooksPath set to .git/hooks"]
  - name: with-stale-config
    description: "Outdated configuration from prior version"
    platform: [linux, macos]
    preconditions: ["legacy config present", "version mismatch"]

coexistence_matrix:
  - tool: pre-commit
    must_not_break: true
  - tool: husky
    must_not_break: true

platform_coverage:
  macOS: [12.x, 13.x, 14.x]
  Linux: [Ubuntu 22.04, Ubuntu 24.04]
  WSL: [WSL2]
  CI: [GitHub Actions ubuntu-latest]

deployment_assumptions:
  - "Installation MUST be idempotent (safe to run twice)"
  - "Uninstall MUST remove only nWave artifacts"
  - "Hooks MUST survive alongside existing hook managers"
```

For features that do NOT install into systems (pure business logic), the environment inventory contains only `target_environments: [{name: clean, platform: [linux, macos]}]`.

DISTILL reads this file to parametrize acceptance scenarios over target environments. If this file is missing, DISTILL uses defaults (clean, with-pre-commit, with-stale-config) — but coverage gaps are the PA's responsibility.

## Peer Review Gate (OPTIONAL — per-wave; mandatory at end of DISTILL)

Per-wave Forge review is opt-in. Default: skip and proceed to DISTILL. The mandatory consolidated review covering DISCUSS+DESIGN+DEVOPS+DISTILL fires at end of DISTILL where Eclipse + Architect + Forge + Sentinel run in parallel against the full `feature-delta.md` (all 4 waves visible — catches cross-wave inconsistencies that per-wave review misses).

Invoke per-wave Forge review explicitly via `/nw-review nw-platform-architect-reviewer` only if:
- Novel deployment target not in prior coexistence matrix
- New CI/CD framework introduced (e.g., switching from GitHub Actions to GitLab)
- Observability stack rewrite (not extension)
- Security posture change (new secrets management, new RBAC layer)
- Maintainer explicitly flags uncertainty

When triggered, the reviewer covers: CI/CD pipeline correctness and completeness, environment inventory coverage, observability design alignment with outcome KPIs, infrastructure security and deployment strategy soundness. On REJECTION: revise artifacts per findings and re-submit (max 2 revision cycles before escalation). Gate: optional unless triggered.

## Success Criteria

- [ ] Environment inventory produced (`environments.yaml` with target environments and coexistence matrix)
- [ ] CI/CD pipeline design finalized and documented
- [ ] Logging infrastructure design complete (structured logging|aggregation)
- [ ] Monitoring and alerting design complete (metrics|dashboards|SLOs/SLIs)
- [ ] Observability design complete (distributed tracing|health checks)
- [ ] Infrastructure integration assessed (if existing infra)
- [ ] Continuous learning capabilities designed (if applicable)
- [ ] Git branching strategy selected and CI/CD triggers aligned
- [ ] Mutation testing strategy selected and persisted to project CLAUDE.md
- [ ] Outcome KPIs instrumentation designed (if outcome-kpis.md exists)
- [ ] Data collection pipeline documented for each KPI
- [ ] Dashboard mockup or spec includes all outcome KPIs
- [ ] Per-wave peer review (OPTIONAL — invoked only on trigger; mandatory consolidated review fires at end of DISTILL)
- [ ] Handoff accepted by nw-acceptance-designer (DISTILL wave)

## Next Wave

**Handoff To**: nw-acceptance-designer (DISTILL wave)
**Deliverables**: Infrastructure design documents + `environments.yaml` (mandatory for DISTILL Mandate 4)

## Examples

### Example 1: Cloud-native greenfield
```
/nw-devops payment-gateway
```
User selects: cloud-native, Kubernetes, GitHub Actions, no existing infra, OpenTelemetry, blue-green, trunk-based development. Apex designs full infrastructure from scratch with robust CI gates on every commit to main.

### Example 2: Brownfield with existing CI/CD
```
/nw-devops auth-upgrade
```
User selects: hybrid, Docker Compose, GitLab CI (existing), existing CI/CD only, Datadog, rolling, GitFlow. Apex extends existing pipelines with branch-specific stages for develop, release, and hotfix branches.

## Wave Decisions Summary

Before completing DEVOPS, produce `docs/feature/{feature-id}/devops/wave-decisions.md`:

```markdown
# DEVOPS Decisions — {feature-id}

## Key Decisions
- [D1] {decision}: {rationale} (see: {source-file})

## Infrastructure Summary
- Deployment: {target + strategy}
- CI/CD: {platform + branching strategy}
- Observability: {stack}
- Mutation testing: {strategy}

## Constraints Established
- {infrastructure constraint}

## Upstream Changes
- {any DESIGN assumptions changed, with rationale}
```

## Outputs

**Single narrative file**: `docs/feature/{feature-id}/feature-delta.md` — environment matrix, CI/CD outline, monitoring contracts, deployment strategy, mutation strategy, observability stack, branching strategy, coexistence matrix all become `## Wave: DEVOPS / [REF|WHY|HOW] <Section>` headings.

**Machine artifacts** (declared, parseable by downstream):
- `docs/feature/{feature-id}/environments.yaml` — target environments + coexistence matrix + platform coverage + deployment assumptions. DISTILL parses this to parametrize acceptance scenarios over environments (Mandate 4 / Environmental Realism).

**SSOT updates** (per Recommendation 3 / back-propagation contract):
- `docs/product/kpi-contracts.yaml` — instrumentation deltas: per-KPI data collection (event names, log fields, metric labels), dashboard mapping, alerting thresholds. Created if absent; extended otherwise.
- `docs/product/architecture/brief.md` — append/update deployment topology subsection if the chosen platform changes the system-context diagram (e.g. new managed services, new region).

Legacy multi-file outputs (`platform-architecture.md`, `ci-cd-pipeline.md`, `observability-design.md`, `monitoring-alerting.md`, `infrastructure-integration.md`, `branching-strategy.md`, `continuous-learning.md`, `kpi-instrumentation.md`, `wave-decisions.md` as separate files) are NOT produced — that content lives in `feature-delta.md`. Only `environments.yaml` survives as a separate machine artifact because it has a parseable downstream consumer. Validator: `scripts/validation/validate_feature_layout.py`.
