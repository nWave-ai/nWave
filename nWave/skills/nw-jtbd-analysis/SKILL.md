---
name: nw-jtbd-analysis
description: JTBD methodology for extracting real jobs behind feature requests — job statements, abstraction layers, first-principles extraction, ODI outcome statements, and opportunity scoring
user-invocable: false
disable-model-invocation: true
---

# JTBD Analysis

## Core Principle

A job is the progress a person is trying to make in a particular circumstance. Jobs are stable over time — technology changes, jobs don't. People hire products to make progress; they fire them when they fail.

**The trap**: Feature requests describe a proposed solution, not the underlying job. Always extract the job first.

---

## Job Statement Format

```
When [situation/trigger], I want to [motivation/action], so I can [expected outcome]
```

**Examples (good)**:
- "When I'm hosting a virtual networking event, I want to facilitate natural conversations between strangers, so I can create valuable connections that wouldn't happen otherwise."
- "When I join an event as a participant, I want to quickly find relevant people to talk to, so I can maximize the value of my limited time."

---

## Job Types — Explore Where Evidenced

Use supplied evidence for each job type. Label proposals and open questions explicitly; emotional and social claims require the human's own account, never inferred feelings or confirmed choices.

| Type | Question | Example |
|------|----------|---------|
| Functional | What task is the user trying to accomplish? | Find someone with complementary expertise |
| Emotional | How does the user want to feel? | Feel confident approaching strangers |
| Social | How does the user want to be perceived? | Appear professional and well-connected |

---

## Abstraction Layers — Navigate to the Real Job

Jobs usually live at strategic or physical level, not tactical.

| Layer | Question | Example |
|-------|----------|---------|
| Tactical | How do we improve this interaction? | Better drag-and-drop for notes |
| Operational | Why does this workflow exist? | Why do we need a facilitator? |
| Strategic | What decision is being pursued? | How do we reduce direction uncertainty? |
| Physical | What's the irreducible function? | Input → Synthesis → Convergence |

**Navigation rules**:
- Use "why?" to move up layers
- Use "how?" to move down layers
- Stop when further "why?" produces a life-goal answer

---

## First-Principles Extraction — 3-Step Inversion

When a feature request is presented as a job, apply this:

1. **Identify the Activity** — What visible action is the user performing?
   - e.g., "User brainstorms on a whiteboard"

2. **Reject the Activity as the Job** — Does anyone wake up wanting to do this activity?
   - "Nobody wakes up wanting to brainstorm" → the job is deeper

3. **Strip to Irreducible Function** — What remains if all tools and methods are removed?
   - e.g., "Reduce uncertainty via input-synthesis-convergence"

**Disruption check**: Is there a higher-level job that would make this entire job unnecessary?

---

## ODI Outcome Statements — Measurable Success Criteria

Format: `[Direction] + [Metric] + [Object] + [Context]`

**Direction**: Always "Minimize" (95% of time). "Maximize" only when more is genuinely better.

**Metrics priority**:
1. `the time it takes to` — speed/efficiency (preferred)
2. `the likelihood of` — avoiding occurrences
3. `the likelihood that` — avoiding results
4. `the number of` — quantity reduction
5. `the effort required to` — ease

**Good vs bad examples**:

| Bad | Problem | Good |
|-----|---------|------|
| "I want easy video calls" | Ambiguous + solution | "Minimize the time it takes to start a conversation with a specific person" |
| "Manage my network effectively" | Vague verb + ambiguous | "Minimize the time it takes to identify who can help with a specific need" |
| "Use breakout rooms to talk privately" | Solution embedded | "Minimize the likelihood of conversations being overheard by unintended parties" |
| "Don't miss important people" | Negative framing | "Minimize the likelihood of failing to connect with relevant attendees" |

**Forbidden words**: easy, reliable, good, better, effective, efficient, manage, handle, deal with.
**Forbidden patterns**: solution references ("using AI", "via the app"), compound statements with "and"/"or", demographics.

---

## Opportunity Scoring

Formula: `Score = Importance + Max(0, Importance - Satisfaction)`

Where Importance and Satisfaction are surveyed 1-10.

| Score | Interpretation |
|-------|---------------|
| 15-20 | Extremely under-served — highest opportunity |
| >12 and <15 | Under-served — high opportunity |
| 10-12 inclusive | Appropriately served — maintain |
| <10 | Over-served — do not invest |

These are the canonical bands in `nw-jtbd-opportunity-scoring`; DISCOVER's >8 eligibility threshold is a different decision, not a served-status classification.

**Output format per opportunity**:
```
| Outcome | Importance | Satisfaction | Score | Status |
|---------|------------|--------------|-------|--------|
| Minimize time to find relevant attendees | 9.2 | 4.1 | 14.3 | Under-served |
```

---

## DIVERGE Output for JTBD Phase

Produce `docs/feature/{feature-id}/diverge/job-analysis.md` with:

1. **Raw request** — verbatim feature/problem statement received
2. **Job extraction** — 5 Why chain from tactical to physical/strategic level
3. **Job statements** — functional (required) + emotional + social (if identifiable)
4. **Disruption check** — Is there a higher-level job this entire job is serving?
5. **Outcome statements** — 3-6 measurable ODI-format statements
6. **Opportunity candidates** — Which outcomes appear most under-served?

**Gate**: Job must be at strategic or physical abstraction level. Tactical-level jobs are not acceptable input for brainstorming — elevate first.
