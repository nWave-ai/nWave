---
name: nw-taste-evaluation
description: Design taste evaluation framework — DVF primary filter, Apple/Google/Jobs design principles as explicit scoring criteria, weighted decision matrix, and option ranking for the DIVERGE wave
user-invocable: false
disable-model-invocation: true
---

# Taste Evaluation

## The Taste Problem

Design taste cannot remain tacit. In the age of AI-assisted product development, taste must be encoded as explicit evaluation criteria — operable, auditable, reproducible. Gut feel is the source from which taste criteria are derived; the weighted matrix is the mechanism that makes taste operational.

**Key insight**: Taste is a fourth lens applied *after* DVF, not instead of it. An option can be Desirable, Feasible, and Viable — and still fail taste by adding three new concepts to the user's mental model when zero would suffice.

---

## Phase 1: DVF Filter — Primary Triage

Apply IDEO's three-lens filter first. Score each lens from 1-5 and apply the explicit DVF-total threshold below before taste scoring.

| Lens | Question | Score 1-5 |
|------|----------|-----------|
| **Desirability** | Do users want this? Does it address the validated job? | 1 = no evidence of want, 5 = clear expressed need |
| **Feasibility** | Can we build it with available skills/tools/time? | 1 = requires unavailable technology, 5 = straightforward to build |
| **Viability** | Does it support a sustainable business model? | 1 = no path to revenue/retention, 5 = clear value capture |

**Elimination threshold**: DVF total < 6 → option eliminated before taste scoring.

---

## Phase 2: Taste Criteria — Four Apple/Jobs Principles

Apply these four criteria to all options that pass DVF. Each is scored 1-5 with explicit rubrics — no subjective override.

### Criterion T1: Subtraction

"Innovation is saying no to a thousand things." — Jobs, 1997

**Test**: Could this option achieve its goal with one fewer feature/concept/step?

| Score | Description |
|-------|-------------|
| 5 | Nothing can be removed without breaking the core value |
| 4 | One minor element could be removed; core intact |
| 3 | Multiple removable elements, value unclear without them |
| 2 | Clearly bloated; several non-essential parts |
| 1 | Feature accumulation masquerading as a product |

### Criterion T2: Concept Count

"Simplicity is the ultimate sophistication." Cognitive load is a design flaw, not a user problem to solve.

**Test**: How many new mental concepts does a first-time user need to learn?

| Score | Description |
|-------|-------------|
| 5 | Zero new concepts — maps entirely to existing mental models |
| 4 | One new concept, well-anchored to something familiar |
| 3 | Two new concepts, introduced sequentially |
| 2 | Three or more concepts, some interdependent |
| 1 | Requires a new mental model to operate |

### Criterion T3: Progressive Disclosure

Complexity must be staged proportionally to user readiness. Front-loading is a design failure.

**Test**: Does the first interaction expose only what's needed for the first use case?

| Score | Description |
|-------|-------------|
| 5 | First interaction = one action; depth revealed only on demand |
| 4 | First interaction = core flow; secondary features one step removed |
| 3 | First interaction exposes 2-3 features; sequencing is logical |
| 2 | First interaction requires choosing between multiple paths |
| 1 | All capabilities exposed at once; user must learn to ignore |

### Criterion T4: Speed-as-Trust

Perceived responsiveness is the primary signal users use to assess product quality and reliability. 75% of users who experience slowness do not return (Akamai).

**Test**: Does this option introduce latency, friction, or steps that erode the sense of speed?

| Score | Description |
|-------|-------------|
| 5 | Instant feedback; every action has immediate response |
| 4 | Minor latency well-masked by progress indicators |
| 3 | Noticeable latency but justified by clear payoff |
| 2 | Multiple wait points; no perceived control |
| 1 | Blocking operations; user cannot tell if it's working |

---

## Phase 3: Weighted Scoring Matrix

Assemble all scores into a weighted matrix.

**Default weights** (adjust per product type):

| Criterion | Default Weight | Developer Tool | Consumer App |
|-----------|---------------|---------------|-------------|
| DVF (avg) | 30% | 25% | 35% |
| Subtraction (T1) | 20% | 15% | 25% |
| Concept Count (T2) | 20% | 20% | 20% |
| Progressive Disclosure (T3) | 15% | 15% | 10% |
| Speed-as-Trust (T4) | 15% | 25% | 10% |

**Final score** = Σ(criterion score × weight). Max = 5.0.

**Output table**:
```
| Option | DVF | T1 Sub | T2 Concept | T3 Prog | T4 Speed | Weighted Total |
|--------|-----|--------|------------|---------|----------|----------------|
| A      | 4.0 | 5      | 4          | 3       | 4        | 4.05           |
| B      | 3.3 | 3      | 5          | 4       | 5        | 3.84           |
| C      | 4.7 | 2      | 3          | 3       | 2        | 3.28           |
```

---

## Phase 4: Recommendation

Produce top 3 options from the scoring matrix.

For each of the top 3, provide:

```
### Option [Name] — Score [X.XX]

**Why it scores well**: What taste principles it satisfies strongly
**Core trade-off**: What it sacrifices (every option trades something)
**Key risk**: The assumption that must be true for this to work
**Hire criteria**: Under what circumstances would a user choose this?
```

**Recommendation**: Identify the top option with a one-paragraph rationale grounded in the scoring — not preference. If the top option has a critical weakness, flag it explicitly.

---

## Anti-Patterns in Taste Evaluation

| Anti-pattern | Detection | Correction |
|-------------|----------|-----------|
| Cherry-picking criteria | Some options evaluated on fewer criteria | Apply all criteria to all options |
| Retroactive justification | Scores given after recommendation chosen | Score first, recommend after |
| Weight manipulation | Weights shifted to favor pre-chosen winner | Lock weights before scoring |
| "It feels right" override | Recommendation contradicts scores | Follow the matrix or change the weights explicitly |
| Feasibility as tie-breaker only | Low-feasibility options kept for aesthetics | DVF is a filter, not a tiebreaker |

---

## DIVERGE Output for Taste Phase

Produce `docs/feature/{feature-id}/diverge/taste-evaluation.md` and `recommendation.md`:

**taste-evaluation.md**:
1. DVF filter table (eliminations documented)
2. Weights selected and rationale
3. Full scoring matrix for surviving options
4. Score breakdown per criterion per option

**recommendation.md**:
1. Top 3 options with pro/con/risk/hire-criteria
2. Recommended option with rationale
3. Dissenting case (which option the scoring almost chose instead, and why)
4. Decision for DISCUSS wave: "Proceed with [option], assuming [key risk] is acceptable"

**Gate**: Recommendation must be derivable from the scoring matrix. Any mismatch between scores and recommendation must be explicitly justified with weight adjustment.
