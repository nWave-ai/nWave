---
name: nw-buddy-wave-knowledge
description: How the 7-wave methodology works — wave graph, entry points, skip conditions, and handoff chain. For the buddy agent to explain methodology to users.
user-invocable: false
disable-model-invocation: true
---

# Wave Methodology Knowledge

## The 7-Wave Graph

nWave is a graph, not a linear pipeline. Not every feature runs all 7 waves.

```
DISCOVER -> DIVERGE -> DISCUSS -> DESIGN -> DEVOPS -> DISTILL -> DELIVER
```

**Invariant**: Every feature ends with DISTILL -> DELIVER. No exceptions.

## Wave Purposes

| Wave | Agent | Purpose | Produces |
|------|-------|---------|----------|
| DISCOVER | product-discoverer (Scout) | Validate the problem exists with real customer evidence | Validated jobs, opportunity tree, lean canvas |
| DIVERGE | diverger (Flux) | Generate and evaluate multiple solution approaches | Recommendation, JTBD analysis, taste evaluation |
| DISCUSS | product-owner (Luna) | Define user stories, journeys, acceptance criteria | User stories, journey schemas, requirements |
| DESIGN | system-designer, ddd-architect, solution-architect | Route to the right architect — system (scalability), domain (DDD), or application (components). All write to shared architecture brief. | Architecture brief, C4 diagrams, domain models |
| DEVOPS | platform-architect | CI/CD, infrastructure, observability, KPI contracts | Platform design, KPI contracts |
| DISTILL | acceptance-designer | Create executable acceptance tests (Given-When-Then) | Feature files, step definitions |
| DELIVER | software-crafter | Implement via Outside-In TDD (roadmap -> execute -> finalize) | Working code, passing tests |

## Entry Points

Choose starting wave based on what you already know:

| Situation | Start At | Example |
|-----------|----------|---------|
| New product, no context | DISCOVER | "Build a payment processor" |
| Feature with multiple approaches | DIVERGE | "Add rate limiting -- token bucket or sliding window?" |
| Feature on known journey | DISCUSS | "Add 2FA to login" |
| Technical story, scope clear | DESIGN | "Refactor auth module" |
| Bug fix, cause known | DISTILL | "Auth token expires too early" |
| Bug fix, cause unknown | DISCOVER | "Auth randomly fails" |
| Infrastructure change | DEVOPS | "Add Redis caching layer" |

## Skip Conditions

Each wave can be skipped only if ALL items in its checklist are true.

### DISCOVER skip
- `docs/product/jobs.yaml` has a validated job matching this feature
- The job has `status: validated` and `validated_by` with a real reference

### DIVERGE skip
- Direction is clear (backlog specifies approach)
- No competing solutions need evaluation
- `recommendation.md` already exists or direction is self-evident

### DISCUSS skip
- `docs/product/journeys/{name}.yaml` covers this behavior
- Journey changelog shows recent update (not stale)
- Existing user stories cover this feature's scope

### DESIGN skip
- `docs/product/architecture/brief.md` covers components touched
- No new component boundaries or ADRs needed
- "For Acceptance Designer" section lists the driving port

### DEVOPS skip
- `docs/product/kpi-contracts.yaml` has a contract for this feature
- No new infrastructure or deployment changes needed

## Handoff Chain

Each wave reads SSOT first, then prior wave delta:

```
DISCOVER -> DIVERGE reads jobs.yaml + vision.md
DIVERGE  -> DISCUSS reads recommendation.md + job-analysis.md + journeys/ + jobs.yaml + vision.md
DISCUSS  -> DESIGN reads architecture/brief.md + journeys/*.yaml + user-stories.md
DESIGN   -> DEVOPS reads architecture/brief.md + kpi-contracts.yaml + outcome-kpis.md
DEVOPS   -> DISTILL reads all 3 SSOT dimensions (journeys + architecture + kpi-contracts)
DISTILL  -> DELIVER reads acceptance-tests.feature
```

## Key Commands

| Command | Wave | Quick Description |
|---------|------|-------------------|
| `/nw-new` | routing | Guided wizard -- asks what you're building, recommends starting wave |
| `/nw-continue` | routing | Detects progress, resumes at next wave |
| `/nw-fast-forward` | routing | Runs remaining waves without stopping between them |

## How to Recommend the Next Wave

When a user asks "what should I do next?", walk through the Entry Points table above — match their situation to the starting wave. Then check Skip Conditions for any waves between their entry point and DISTILL. Skip what's already covered by SSOT.

After DISTILL, always DELIVER.

> For the full authoritative wave routing reference, read `docs/guides/wave-routing-and-entry-points/README.md`.
