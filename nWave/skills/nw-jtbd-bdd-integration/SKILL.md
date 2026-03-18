---
name: nw-jtbd-bdd-integration
description: Translating JTBD analysis to BDD scenarios - job story to Given-When-Then patterns, forces-based test discovery, job-map-based test discovery, and property-shaped criteria
disable-model-invocation: true
---

# JTBD to BDD Integration

Use when translating JTBD discoveries (job stories, forces, job map) into testable BDD scenarios. Job stories map naturally to Given-When-Then because both emphasize context (situation/given), action (motivation/when), and outcome (result/then).

## Job Story to Given-When-Then Translation

### The Pattern

```
Job Story:
  When [situation],
  I want to [motivation],
  so I can [outcome].

BDD Scenario:
  Given [the situation from the job story]
  When [user takes action aligned with the motivation]
  Then [the outcome is achieved and measurable]
```

### Worked Example

**Job Story**: "When I receive an alert that a production service is degraded, I want to see the most likely root cause with supporting evidence, so I can begin remediation within minutes instead of hours."

```gherkin
Scenario: Root cause surfaced from degradation alert
  Given the monitoring system has detected degraded response times on the payment service
  And the degradation started 5 minutes ago
  When the operator opens the incident dashboard
  Then the system displays the top 3 probable root causes ranked by likelihood
  And each root cause includes supporting metrics and log evidence
  And the most likely root cause is displayed within 10 seconds

Scenario: Remediation guidance from identified root cause
  Given the operator has identified the root cause as database connection pool exhaustion
  When the operator selects the recommended remediation action
  Then the system presents a runbook with step-by-step instructions
  And the estimated time to remediate is displayed
  And the operator can execute the first step directly from the dashboard
```

### Translation Rules

1. **Given** = situation from job story, made concrete with specific data
2. **When** = user action fulfilling the motivation
3. **Then** = measurable outcome, including quality attributes (time, confidence, completeness)

### Multi-Scenario Expansion

One job story typically produces 3-5 BDD scenarios:
- **Happy path**: Outcome achieved as described
- **Anxiety path**: User's fear about new solution addressed
- **Habit path**: User transitioning from old workflow supported
- **Edge cases**: Derived from job map steps (see below)

## Forces-Based Test Discovery

Use Four Forces to discover test scenarios that feature-driven thinking misses.

### Force-to-Scenario Mapping

| Force | Test Question | Scenario Pattern |
|-------|--------------|-----------------|
| **Push** | What frustration drove the user here? | `Given [user has experienced the frustration]...` |
| **Pull** | What outcome is the user hoping for? | `Then [the promised improvement is measurable]` |
| **Anxiety** | What could go wrong with the new solution? | `Given [user has specific fear] When [fear-triggering event] Then [safety net activates]` |
| **Habit** | What existing workflow might resist adoption? | `Given [user accustomed to old way] When [new approach encountered] Then [familiar patterns preserved]` |

### Worked Example: Automated Deployment Tool

**Forces analysis**:
- Push: Manual deployments cause errors and take hours
- Pull: One-command deployment with automatic rollback
- Anxiety: "What if the automated rollback breaks worse than the original deploy?"
- Habit: Team SSH-es into servers and runs scripts manually

**Derived scenarios**:

```gherkin
# Push scenario: validates the frustration is resolved
Scenario: Deployment completes without manual intervention
  Given the operator has configured deployment for the payment service
  And the previous manual deployment took 3 hours with 2 errors
  When the operator runs the automated deployment command
  Then deployment completes within 15 minutes
  And zero manual steps are required

# Pull scenario: validates the promised outcome
Scenario: Automatic rollback on health check failure
  Given the deployment has completed and health checks are running
  When the payment endpoint returns 500 errors for 30 seconds
  Then the system automatically rolls back to the previous version
  And the operator receives a notification with rollback details

# Anxiety scenario: addresses the specific fear
Scenario: Rollback preserves database state
  Given the deployment included a database migration
  And the health check has triggered an automatic rollback
  When the rollback completes
  Then the database schema matches the previous stable version
  And no data is lost during the rollback process
  And the operator can verify data integrity from the dashboard

# Habit scenario: eases the transition
Scenario: Manual override available during automated deployment
  Given the operator is accustomed to SSH-based manual deployments
  When the automated deployment is in progress
  Then the operator can view real-time logs (familiar output format)
  And the operator can pause or cancel the deployment at any stage
  And manual SSH access remains available as a fallback
```

## Job-Map-Based Test Discovery

Walk each of the 8 job map steps and generate at least one test scenario per step. Surfaces edge cases that happy-path thinking misses.

| Job Map Step | Missing Scenario Pattern | Example |
|-------------|------------------------|---------|
| **Define** | User lacks information to start | `Given the user has not reviewed the change log When they attempt to deploy Then the system warns about unreviewed changes` |
| **Locate** | Required inputs unavailable or stale | `Given the build artifact is 30 days old When the user selects it for deployment Then the system flags the artifact as potentially stale` |
| **Prepare** | Setup fails or environment misconfigured | `Given the target environment has a port conflict When preparation runs Then the system reports the conflict with resolution steps` |
| **Confirm** | Validation passes incorrectly (false positive) | `Given the pre-check passes but a dependency is actually down When deployment proceeds Then the system detects the issue at runtime and halts` |
| **Execute** | Execution interrupted midway | `Given deployment is 50% complete When the network connection drops Then the system resumes from the last checkpoint after reconnection` |
| **Monitor** | Monitoring reports misleading success | `Given all health checks pass but latency has doubled When the operator reviews the dashboard Then latency degradation is highlighted as a warning` |
| **Modify** | Modification makes things worse | `Given the operator applies a hotfix during an incident When the hotfix introduces a new error Then the system detects the regression and suggests reverting` |
| **Conclude** | Cleanup fails silently | `Given deployment succeeded and cleanup runs When temporary resources fail to delete Then the system logs the failure and alerts the operator` |

### Application Process

1. List the 8 job map steps for the feature
2. For each step, ask: "What could go wrong here that we have not tested?"
3. Write one scenario per step minimum
4. Steps 1-4 (Define through Confirm) and 7-8 (Modify, Conclude) produce most overlooked scenarios

## The @property Tag for Property-Shaped Criteria

Some AC describe system properties rather than discrete scenarios -- ongoing qualities, not one-time events.

### When to Use @property

Use when criterion: describes quality holding continuously (not one scenario) | cannot be captured by finite Given-When-Then set | relates to performance, consistency, or invariants

### Format

```gherkin
@property
Scenario: Response time consistency under load
  Given the system is handling 100 concurrent requests
  Then all API responses complete within 200ms at the 95th percentile
  And no response exceeds 1000ms

@property
Scenario: Data consistency across replicas
  Given writes have been committed to the primary database
  Then all read replicas reflect the write within 5 seconds
  And no stale reads occur after the consistency window
```

### Property Criteria from JTBD

Outcome statements often translate to property-shaped criteria (ongoing qualities):

| Outcome Statement | Property Scenario |
|-------------------|-------------------|
| "Minimize the likelihood of undetected failures" | `@property` monitoring coverage: all critical paths emit health signals |
| "Minimize the time to recover from exceptions" | `@property` recovery time: system returns to healthy state within 60s |
| "Maximize the likelihood that results are consistent" | `@property` consistency: identical inputs produce identical outputs |

## JTBD-to-BDD Translation Template

Use when translating a complete job story into a BDD scenario set:

```markdown
## JTBD-to-BDD Translation: [Feature Name]

### Source Job Story
When [situation],
I want to [motivation],
so I can [outcome].

### Forces
- Push: [frustration]
- Pull: [attraction]
- Anxiety: [fear]
- Habit: [inertia]

### Scenarios

#### Happy Path (from job story)
Scenario: [outcome achieved]
  Given [situation]
  When [action aligned with motivation]
  Then [outcome measurable]

#### Anxiety Path (from forces)
Scenario: [fear addressed]
  Given [anxiety-triggering context]
  When [fear event occurs]
  Then [safety net / reassurance]

#### Habit Path (from forces)
Scenario: [transition supported]
  Given [user accustomed to old way]
  When [new approach encountered]
  Then [familiar patterns preserved]

#### Job Map Edge Cases
Scenario: [Define step gap]
  Given [insufficient information]
  When [user attempts to start]
  Then [system guides to missing info]

Scenario: [Monitor step gap]
  Given [misleading success indicators]
  When [user checks results]
  Then [system surfaces hidden issues]

#### Properties (from outcome statements)
@property
Scenario: [ongoing quality]
  Given [system under normal operation]
  Then [quality metric holds within threshold]
```

## Integration Checklist

Before handing scenarios to acceptance-designer (DISTILL wave), verify:

- [ ] Happy path scenario derived from job story
- [ ] Anxiety scenario addresses strongest demand-reducing force
- [ ] Habit scenario supports users transitioning from current workflow
- [ ] At least 4 of 8 job map steps have dedicated edge case scenarios
- [ ] Property-shaped criteria tagged with @property
- [ ] All scenarios use concrete data (real names, real values)
- [ ] Scenarios are solution-neutral where possible (describe outcomes, not implementation)

## Cross-References

- For core JTBD theory and the 8-step job map: load `jtbd-core` skill
- For interview techniques to discover forces: load `jtbd-interviews` skill
- For outcome statements feeding @property criteria: load `jtbd-opportunity-scoring` skill
- For BDD methodology (Example Mapping, Three Amigos): load `bdd-requirements` skill
