# How to Run DIVERGE: Structured Option Evaluation

Use this guide when you need to explore multiple solution approaches before deciding on one.

---

## When to Run DIVERGE

Run DIVERGE when:

- **New product** — no prior solution exists, multiple approaches possible
- **Pivot** — reconsidering an existing feature from scratch
- **Competitive landscape unclear** — you need to research how others solve this
- **Multiple paths forward** — different trade-offs exist, need structured evaluation

**Estimated time**: 2-4 hours (depending on research depth)

---

## When to Skip DIVERGE

Skip DIVERGE if:

- Direction is already clear (bugfix, refactoring, technical story)
- No competing approaches need evaluation
- `recommendation.md` already exists for this feature

Use the DIVERGE skip checklist from the [Wave Routing Guide](../wave-routing-and-entry-points/).

---

## The 4 Phases

### Phase 1: JTBD Analysis

Extract the validated job from the problem. Go from "we need rate limiting" to "When an API is under load, I want requests to be throttled fairly, so critical operations remain responsive."

**Produces**: Job statement + 3+ outcome statements.

### Phase 2: Competitive Research

Research 3+ real products that solve this job. Include non-obvious alternatives. Map how they serve the validated job.

**Produces**: Evidence of prior art, market positioning, alternatives considered.

### Phase 3: Brainstorming

Apply structured techniques (SCAMPER, How-Might-We) to generate 6+ diverse options. Diversity means different mechanisms, assumptions, or costs — not just minor variations.

**Produces**: 6+ options, unfiltered and unranked.

### Phase 4: Taste Evaluation

Filter options through your taste criteria (complexity, strategic fit, etc.). Score surviving options with locked weights. Produce a ranked recommendation with a documented dissenting case for the runner-up.

**Produces**: Weighted scoring matrix, explicit recommendation, dissent narrative.

---

## Running DIVERGE

### Command

```
/nw-diverge {feature-id}
```

Replace `{feature-id}` with your feature identifier (e.g., `rate-limiting`, `notification-system`).

### Interactive Decisions

The agent will ask:

**Decision 1: Work Type**
- New product
- Brownfield feature
- Pivot / redesign
- Other (provide context)

**Decision 2: Research Depth**
- Lightweight (3 competitors, known market)
- Comprehensive (5+ competitors, non-obvious alternatives)
- Deep-dive (cross-category research, adjacent markets)

---

## What DIVERGE Produces

### Feature delta (in `docs/features/{feature-id}/`)

```
recommendation.md         Top 3 options + rationale + dissent
wave-decisions.md        DIVERGE decisions appended
```

The **recommendation.md** is your main output — read this to understand which option won and why.

### Internal artifacts (in `docs/features/{feature-id}/diverge/`)

```
job-analysis.md          Validated job + outcome statements
competitive-research.md  Prior art, competitor analysis
options-raw.md          All generated options (unfiltered)
taste-evaluation.md     Scoring matrix, locked weights
review.yaml             Peer review result
```

These are archived for history and review.

### SSOT update (in `docs/product/`)

```
jobs.yaml                Adds your validated job + changelog entry
```

---

## After DIVERGE: Handing Off to DISCUSS

Once DIVERGE completes:

1. **Review** `recommendation.md` — does the chosen direction make sense?
2. **Approve** or request revisions (agent will iterate)
3. **Start DISCUSS**:

```
/nw-discuss {feature-id}
```

The product-owner agent will read your recommendation and produce user stories grounded in that direction.

---

## Example: Building a Notification System

**Scenario**: New product, no prior solution exists. You want to notif developers of critical failures.

### Command

```
/nw-diverge notification-system
```

### Decisions

- Work type: **New product**
- Research depth: **Comprehensive** (5+ notification tools, non-obvious alternatives)

### Phase 1: JTBD Analysis

Problem statement: "Developers miss critical failure signals"

Extracted job: "When a production service fails, I want immediate notification through a channel I actively monitor, so I can respond before customers notice."

Outcome statements:
- Minimize time to notice failure (< 30 seconds)
- Minimize false alarm fatigue (critical-only)
- Minimize context switching (notify in existing tool like Slack)

### Phase 2: Competitive Research

Research completed:
- **PagerDuty** — incident escalation, oncall scheduling
- **Sentry** — error tracking, release integration
- **Slack integrations** — direct API, no extra tool
- **Prometheus alerting** — metric-based thresholds
- **Ambient light signals** — non-obvious: hardware-based status indicator (e.g., desk lamp color change for critical alerts)

### Phase 3: Brainstorming

6 generated options:
1. **PagerDuty-native** — full platform, complex setup
2. **Slack webhook** — minimal, but limited to Slack users
3. **Email digest** — low cost, high latency
4. **Hybrid (Slack + email)** — covers both sync and async
5. **Custom dashboard** — self-hosted, maximum control
6. **Ambient hardware** — physical signal + Slack notification

### Phase 4: Taste Evaluation

Taste criteria (with locked weights):
- Implementation speed (30%)
- Operational simplicity (25%)
- Developer adoption (25%)
- Extensibility (20%)

Scoring matrix:

| Option | Speed | Simplicity | Adoption | Extensibility | **Score** |
|--------|-------|-----------|----------|---------------|-----------|
| PagerDuty-native | 2 | 2 | 9 | 8 | 5.3 |
| Slack webhook | 9 | 9 | 10 | 5 | **8.5** |
| Email digest | 8 | 8 | 7 | 4 | 7.2 |
| Hybrid (Slack+email) | 7 | 6 | 9 | 6 | 7.3 |
| Custom dashboard | 4 | 3 | 5 | 9 | 5.4 |
| Ambient hardware | 3 | 4 | 3 | 7 | 4.1 |

### Recommendation

**Chosen**: Slack webhook integration

**Rationale**: Fastest to implement (developers already monitoring Slack), simplest to operate, highest adoption. Extensibility is adequate for phase 1.

**Dissenting case**: Hybrid (Slack+email) is worth reconsidering if we discover low adoption among remote teams who step away from Slack frequently.

---

## When DIVERGE Discovers Competing Approaches

If you thought you had a clear direction but DIVERGE reveals multiple paths forward, that's fine. Keep going. The structured evaluation helps you choose with confidence.

**Example**: You planned "add rate limiting via Redis." But DIVERGE research shows token-bucket vs sliding-window approaches, each with different trade-offs. Evaluation clarifies which fits your constraints best.

---

## Next Steps

1. Review `recommendation.md`
2. Approve or request revisions
3. Run `/nw-discuss {feature-id}` to translate recommendation into user stories
