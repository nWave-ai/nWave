---
name: nw-jtbd-opportunity-scoring
description: JTBD opportunity scoring and prioritization - outcome statement format, opportunity algorithm, scoring interpretation, feature prioritization, and opportunity matrix template
user-invocable: false
disable-model-invocation: true
---

# JTBD Opportunity Scoring

Use when prioritizing features, stories, or backlog items based on customer-defined outcomes. Opportunity scoring (Ulwick's ODI) replaces gut-feel prioritization with evidence-based ranking.

## Outcome Statements

Every customer need expressed as a desired outcome following strict format:

```
[Direction] + the [metric] + [object of control] + [contextual clarifier]
```

- **Direction**: "Minimize" or "Maximize"
- **Metric**: time, likelihood, number, or frequency

### Examples

- "Minimize the time it takes to identify the root cause of a production issue"
- "Minimize the likelihood of deploying untested code to production"
- "Maximize the likelihood that acceptance criteria cover all relevant scenarios"
- "Minimize the number of iterations needed to reach shared understanding"
- "Minimize the frequency of false positive alerts during monitoring"

### Quality Checks

Outcome statement must be: **Solution-free** (no specific technology) | **Measurable** (ratable on importance/satisfaction 1-5) | **Controllable** (customer can assess improvement) | **Unambiguous** (same interpretation by all stakeholders)

### Deriving Outcome Statements

Walk the 8-step job map (see `jtbd-core` skill) and generate 2-3 per step. Produces 16-24 outcome statements per job -- comprehensive view of customer needs.

| Job Map Step | Outcome Statement Pattern |
|-------------|--------------------------|
| Define | "Minimize the time to determine [what is needed]" |
| Locate | "Minimize the likelihood of missing [required input]" |
| Prepare | "Minimize the time to set up [environment/context]" |
| Confirm | "Minimize the likelihood of proceeding with [invalid state]" |
| Execute | "Minimize the time to complete [core action]" |
| Monitor | "Minimize the likelihood of [undetected failure]" |
| Modify | "Minimize the time to recover from [exception]" |
| Conclude | "Minimize the likelihood of [incomplete cleanup]" |

## The Opportunity Algorithm

```
Opportunity Score = Importance + max(0, Importance - Satisfaction)
```

Where:
- **Importance** = % of respondents rating outcome 4 or 5 on 1-5 scale
- **Satisfaction** = % of respondents rating current satisfaction 4 or 5 on 1-5 scale
- **Score range**: 0-20 (higher = greater opportunity)

### How It Works

Rewards outcomes both important and unsatisfied. If satisfaction >= importance, second term is zero (appropriately served). If satisfaction < importance, gap amplifies score (underserved).

### Score Interpretation

| Score Range | Category | Action |
|-------------|----------|--------|
| 15-20 | Extremely underserved | High-priority; invest heavily |
| 12-15 | Underserved | Strong opportunity; plan for next iteration |
| 10-12 | Appropriately served | Maintain; incremental improvement |
| < 10 | Overserved | Simplification candidate; may be over-engineered |

## Applying to Feature Prioritization

### Step 1: Generate Outcome Statements
From job mapping and interview findings, compile 15-30 per major job.

### Step 2: Rate Importance and Satisfaction
Gather ratings from users/stakeholders. For small teams:
- Interview 5-10 users directly
- Use internal team ratings as proxy (mark as "team estimate" vs "user data")
- Leverage support tickets, feature requests, bug reports as signals

### Step 3: Calculate and Rank
Compute scores, sort descending. Top scores = highest-priority features.

### Step 4: Map to Stories
Each high-scoring outcome maps to one or more stories. Score 15+ should produce at least one story in current iteration.

### Step 5: Identify Overserved Areas
Scores below 10 are simplification candidates. Resources on overserved outcomes are better redirected to underserved ones.

## Opportunity Scoring Matrix Template

```markdown
## Opportunity Scoring: [Product/Feature Area]

| # | Outcome Statement | Imp. (%) | Sat. (%) | Score | Priority |
|---|-------------------|----------|----------|-------|----------|
| 1 | Minimize the time to [outcome A] | | | | |
| 2 | Minimize the likelihood of [outcome B] | | | | |
| 3 | Maximize the [quality] when [context C] | | | | |

### Scoring Method
- Importance: % of respondents rating 4+ on 5-point scale
- Satisfaction: % of respondents rating 4+ on 5-point scale
- Score: Importance + max(0, Importance - Satisfaction)
- Priority: Extremely Underserved (15+), Underserved (12-15),
  Appropriately Served (10-12), Overserved (<10)

### Top Opportunities (Score >= 12)
1. [Outcome] -- Score: [X] -- Story: [link or title]
2. [Outcome] -- Score: [X] -- Story: [link or title]

### Overserved Areas (Score < 10)
1. [Outcome] -- Score: [X] -- Simplification opportunity: [description]

### Data Quality Notes
- Source: [user interviews / team estimates / support ticket analysis]
- Sample size: [N respondents]
- Confidence: [High if N >= 10 with user data, Medium if team estimates]
```

## Worked Example

Context: CLI tool for deploying applications. 8 users surveyed.

| # | Outcome Statement | Imp. | Sat. | Score | Priority |
|---|-------------------|------|------|-------|----------|
| 1 | Minimize time to identify root cause of failed deployment | 92% | 35% | 14.9 | Extremely Underserved |
| 2 | Minimize likelihood of deploying untested code | 88% | 72% | 10.4 | Appropriately Served |
| 3 | Minimize time to roll back a bad deployment | 85% | 30% | 14.0 | Underserved |
| 4 | Minimize time to onboard a new team member to deploy | 65% | 40% | 9.0 | Overserved |
| 5 | Minimize likelihood of misconfiguring environment variables | 80% | 45% | 11.5 | Appropriately Served |

**Prioritization result**:
1. Root cause identification (14.9) -- build better deployment diagnostics
2. Rollback speed (14.0) -- invest in one-command rollback
3. Environment misconfiguration (11.5) -- incremental improvements to validation
4. Untested code prevention (10.4) -- maintain current pre-deploy checks
5. Onboarding time (9.0) -- consider simplifying; current docs may be over-engineered

## Small-Team Adaptations

Ulwick's methodology assumes large-scale surveys (100+ respondents). For small agile teams:

- **5-10 interviews sufficient** for directional signals. Treat scores as relative rankings, not absolute.
- **Support tickets as proxy data**: High-frequency complaints = high importance + low satisfaction.
- **Team consensus estimation**: When user access limited, rate collectively. Document as "team estimate."
- **Iterate**: Re-score after each release as satisfaction shifts.

## Integration with Other Prioritization Methods

| Method | Best For | Combine With Opportunity Scoring |
|--------|----------|--------------------------------|
| MoSCoW | Sprint-level scope decisions | Use opportunity scores to inform Must/Should/Could |
| Value/Effort matrix | Quick relative ranking | Use opportunity scores as "value" axis |
| RICE | Feature-level prioritization | Use opportunity score as "Impact" component |
| Story mapping | Release planning | Use opportunity scores to prioritize rows (MVP vs later) |

## Cross-References

- For core JTBD theory and job map steps: load `jtbd-core` skill
- For interview techniques to gather importance/satisfaction data: load `jtbd-interviews` skill
- For translating high-priority outcomes to BDD scenarios: load `jtbd-bdd-integration` skill
- For story-level prioritization (MoSCoW, Value/Effort): load `leanux-methodology` skill
