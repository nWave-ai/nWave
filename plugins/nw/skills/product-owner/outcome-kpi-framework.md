---
name: outcome-kpi-framework
description: Outcome KPI definition methodology - synthesizes Who Does What By How Much (Gothelf/Seiden), Running Lean (Maurya), and Measure What Matters (Doerr) into a practical framework for measurable outcome KPIs
---

# Outcome KPI Framework

"Doing stuff isn't the point. Achieving stuff is." -- Jeff Gothelf

Defines measurable outcome KPIs for user stories and features. Loaded during Phase 4 (Requirements Crafting) to produce `outcome-kpis.md`. Synthesizes three frameworks: customer-centric OKRs, lean metrics, and OKR methodology.

## The Outcome KPI Formula

Primary template from Gothelf/Seiden. Every KPI answers five questions:

| Component | Question | Example |
|-----------|----------|---------|
| **Who** | Which user segment? | Returning customers with 2+ orders |
| **Does What** | What observable behavior changes? | Complete checkout without contacting support |
| **By How Much** | What is the measurable target? | 40% reduction in support tickets |
| **Measured By** | How do we collect the data? | Support ticket system + checkout analytics |
| **Timeframe** | When do we measure? | 30 days post-release, then weekly |

Formula: **[Who] [Does what] [By how much]**

Apply as litmus test: if a KPI cannot answer all five components, it measures an output (feature delivery), not an outcome (behavior change).

### Good vs Bad KPIs

| Bad (Output) | Good (Outcome) |
|-------------|----------------|
| Launch mobile app v2 | Mobile users complete purchases 40% more often |
| Build recommendation engine | Users purchase from recommendations, increasing from 10% to 25% |
| Deploy onboarding redesign | New users complete onboarding within 24 hours 30% more often |
| Ship CSV export | Analysts resolve data questions without engineering support 60% of the time |

## Leading vs Lagging Indicators

From Gothelf/Seiden: business results are lagging -- teams cannot directly influence them. Target leading indicators instead.

| Type | Definition | Examples | Actionable? |
|------|-----------|----------|-------------|
| **Lagging** (Impact) | Business results already happened | Revenue, NPS, market share, churn rate | No -- too slow, too many variables |
| **Leading** (Outcome) | Behavior changes predicting business results | Purchase completion rate, feature adoption, retention | Yes -- teams can run experiments |
| **Leading** (Secondary) | Behaviors predicting primary leading indicators | Page visits, trial starts, onboarding steps completed | Yes -- most granular, fastest signal |

### Outcome Mapping Chain

Map every KPI through this chain to ensure traceability:

```
Business KPI (Lagging/Impact)
    Example: "Increase quarterly revenue by 15%"
        |
        v
    Customer Behavior (Leading/Outcome)
        +-- Users complete purchases from recommendations (+25%)
        +-- Users return within 7 days (+20%)
        |
        v
    Secondary Behavior (Leading/Secondary)
        +-- Users browse recommendation pages (+30%)
        +-- Users enable push notifications (+15%)
```

Each layer decomposes into more granular behavioral metrics. Teams target the highest-leverage behavior.

## Actionable vs Vanity Metrics

From Maurya (Running Lean): actionable metrics "tie specific and repeatable actions to observed results."

| Dimension | Vanity | Actionable |
|-----------|--------|------------|
| Measures | Business size (totals) | Individual behavior (rates) |
| Data type | Gross aggregates | Ratios and unit economics |
| Cause/effect | No insight into why | Directly signal product-market fit |
| Examples | Total users, page views, downloads | Activation rate, retention cohort, churn rate |
| Decision value | Cannot inform action | Drives specific experiments |

### The OMTM (One Metric That Matters)

Pick ONE metric per product stage. Optimizing one metric reveals the next.

| Stage | Focus | Example OMTM |
|-------|-------|--------------|
| Empathy | Problem validation | Interview pain intensity (qualitative) |
| Stickiness | Retention | Churn rate, DAU/MAU ratio |
| Virality | Organic growth | Viral coefficient, referral rate |
| Revenue | Monetization | Customer Lifetime Value, MRR |
| Scale | Growth efficiency | CAC/LTV ratio, payback period |

**Good metric characteristics**: rate or ratio (not absolute number) | comparable across time | simple enough to remember | predictive | behavior-changing.

### Customer Factory (AARRR) Constraint Mapping

From Maurya: model the business as a production line. Identify the bottleneck, then focus KPIs there.

| Stage | Key Question | Example Metric |
|-------|-------------|----------------|
| **Acquisition** | Are we reaching the right people? | Visitor-to-signup conversion rate |
| **Activation** | Do users get the "aha moment"? | % completing core action in first session |
| **Retention** | Do users come back? | Week-1 return rate, DAU/MAU |
| **Revenue** | Do users pay? | Trial-to-paid conversion rate |
| **Referral** | Do users tell others? | Referral rate, viral coefficient |

Activation is causal -- it drives retention, revenue, and referral. Prioritize activation KPIs when uncertain.

## OKR Integration

From Doerr (Measure What Matters): connect KPIs to strategic objectives.

### Writing Key Results

Every Key Result uses the outcome formula. Quality criteria:

1. **Measurable**: "It's not a Key Result unless it has a number" (Marissa Mayer)
2. **Outcome-focused**: "Increase email subscribers by 20%" not "Launch newsletter"
3. **Time-bound**: deadline (typically end of quarter)
4. **Verifiable**: no ambiguity about whether met
5. **Aggressive yet realistic**: stretch without demoralizing

### Committed vs Aspirational

| Type | Expected Score | Resource Allocation | Failure Response |
|------|---------------|--------------------|-----------------|
| **Committed** | 1.0 (must deliver) | Consume most available resources | Requires explanation, replanning |
| **Aspirational** | 0.7 (stretch goal) | Overcommit slightly beyond capacity | Expected -- carry forward |

Sweet spot: blended aggregate of 0.6-0.7. Consistently hitting 1.0 = not ambitious enough.

### OKR Anti-Patterns

| Anti-Pattern | Signal | Fix |
|-------------|--------|-----|
| Output-based KRs | "Launch X", "Build Y", "Ship Z" | Rewrite as behavior: "Users [do what] [by how much]" |
| Too many KRs | >5 KRs per Objective | Cut to 2-4 per Objective, max 3-5 Objectives |
| Vague KRs | No numeric target | Add baseline + target + deadline |
| Sandbagging | Consistently scoring 1.0 | Increase ambition level |
| Backlog retrofitting | OKRs match existing backlog 1:1 | OKRs filter backlog, not justify it |

### Mapping: Objective to User Stories

```
Objective (qualitative, inspirational, timeboxed)
    |
    Key Results (2-4 per Objective, [Who][Does what][By how much])
    |
    Epics (weeks of work, aligned to Key Results)
    |
    User Stories (days of work, with measurable acceptance criteria)
```

Every story traces back to a Key Result. Orphan stories (no KR link) are potential waste.

## KPI Template

Use this exact structure in `outcome-kpis.md`:

```markdown
## Feature: {feature-name}

### Objective
{What success looks like in one sentence -- qualitative, inspirational, timeboxed}

### Outcome KPIs

| # | Who | Does What | By How Much | Baseline | Measured By | Type |
|---|-----|-----------|-------------|----------|-------------|------|
| 1 | {segment} | {behavior} | {target} | {current} | {method} | Leading/Lagging |

### Metric Hierarchy
- **North Star**: {the ONE metric that matters most for this feature}
- **Leading Indicators**: {behaviors that predict the north star}
- **Guardrail Metrics**: {metrics that must NOT degrade}

### Measurement Plan
| KPI | Data Source | Collection Method | Frequency | Owner |
|-----|------------|-------------------|-----------|-------|

### Hypothesis
We believe that {proposed solution} for {user segment} will achieve {key result}.
We will know this is true when {who} {does what} {by how much}.
```

## KPI Granularity

- **Per Epic**: Define 2-3 north-star KPIs that all contributing stories aim to move
- **Per Story**: Add story-level success criteria tied to the epic-level KPIs
- **Guardrails**: Define at epic level, apply consistently across all stories
- **Rule of thumb**: If the feature has 1-3 stories, one KPI table suffices. If 4+, group by epic.

## Smell Tests

Before finalizing KPIs, verify each one passes:

| Check | Question | If No |
|-------|----------|-------|
| Measurable today? | Can you measure it with current instrumentation? | Add instrumentation to requirements |
| Rate not total? | Is it a ratio/rate, not a gross count? | Convert to rate (vanity -> actionable) |
| Outcome not output? | Does it describe user behavior, not feature delivery? | Rewrite as "[Who] [Does what] [By how much]" |
| Has baseline? | Do you know the current value? | Establish baseline before setting target |
| Team can influence? | Can the team directly affect this metric? | Decompose into more granular leading indicator |
| Has guardrails? | Are there metrics that must not degrade? | Add guardrail metrics (e.g., error rate, load time) |

## Handoff to DEVOPS

The platform-architect needs these from `outcome-kpis.md` to plan instrumentation:

1. **Data collection requirements**: what events/behaviors to instrument, what data points to capture
2. **Dashboard/monitoring needs**: which metrics need real-time dashboards vs. weekly reports
3. **Alerting thresholds**: guardrail metric boundaries that trigger alerts when breached
4. **Baseline measurement**: any metrics needing baseline collection before feature release

## References

For deeper reading on source frameworks:
- Running Lean (Maurya): `docs/research/running-lean-research.md`
- Measure What Matters (Doerr): `docs/research/measure-what-matters-research.md`
- Who Does What By How Much (Gothelf/Seiden): `docs/research/who-does-what-research.md`
