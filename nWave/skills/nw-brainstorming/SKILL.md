---
name: nw-brainstorming
description: Structured divergent thinking techniques — HMW framing, SCAMPER, Crazy 8s mechanics, and option diversity guarantees. Enforces strict separation of generation and evaluation phases.
user-invocable: false
disable-model-invocation: true
---

# Structured Brainstorming

## The Separation Principle — Foundational Rule

Generation and evaluation CANNOT happen simultaneously. Osborn (1953): "You cannot get hot and cold water from the same faucet at the same time — you only get tepid water."

**Consequence for the agent**: All options must be generated before any option is scored. Never filter or rank during generation. Self-censorship during generation degrades both the quality of ideas and the quality of evaluation.

---

## Phase 1: HMW Framing — Set Up the Ideation Space

Before generating any options, reframe the problem as a "How Might We" question.

**Rules for valid HMW questions**:
- No embedded solutions: "How might we make onboarding faster?" ✓ vs "How might we add tooltips?" ✗
- Outcome-oriented, not feature-oriented
- Broad enough for genuinely different approaches
- Positive framing (not "How might we avoid X?")

**Example transformation**:
- Feature request: "Add a dashboard to show workflow status"
- Bad HMW: "How might we build a better dashboard?"
- Good HMW: "How might we give teams confidence that their workflow is progressing correctly?"

The good HMW opens the solution space: the answer isn't necessarily a dashboard.

---

## Phase 2: SCAMPER — 7 Structurally Different Lenses

Apply each SCAMPER lens to the validated job to generate one option per letter. This guarantees structural diversity — each letter produces a categorically different type of option.

| Letter | Lens | Question | What it produces |
|--------|------|----------|-----------------|
| **S** | Substitute | What if the core mechanism were replaced entirely? | Alternative technology/approach |
| **C** | Combine | What if this job were merged with an adjacent job? | Integrated solution |
| **A** | Adapt | What works well in a different domain? Could we borrow it? | Cross-domain transfer |
| **M** | Modify/Magnify | What if the most important dimension were amplified? | Focused excellence |
| **P** | Put to other use | Who else has this job? Could the solution serve them too? | Market extension |
| **E** | Eliminate | What if we removed the most complex part? | Radical simplification |
| **R** | Reverse | What if the workflow ran backwards? User and system switched roles? | Inversion |

**Required output**: At minimum, one option per SCAMPER letter. For each lens, state a probability per candidate — the distribution over that lens's candidates, summing to 1 — then deliberately keep the low-probability (tail) candidates alongside the head candidates: this counteracts the pull toward the typical answer (verbalized sampling, Zhang et al., arXiv 2510.01171), so that repeated runs tend to sample different tail candidates. Name each option with the requester's own words where they described the thing; coin a name only when nothing the requester said covers it, and make a coined name describe the mechanism rather than evoke. Do not evaluate during generation.

A **tail candidate** is a candidate whose stated probability is at most 0.2 within the distribution it was drawn from — its SCAMPER lens's candidates, or the Crazy 8s supplements' distribution. Every other retained candidate is a head candidate.

---

## Phase 3: Crazy 8s Supplement — Volume and Self-Censorship Removal

After SCAMPER, generate 2-4 additional options by imagining you have only 1 minute per idea. The time pressure mechanic prevents evaluation creep.

**Constraint**: Each additional option must differ structurally from all SCAMPER options. Not a variation — a different type of approach.

**Probability space**: The supplements form one distribution of their own, summing to 1 — state a probability per supplement candidate within it, and keep tail candidates here too.

---

## Phase 4: Option Curation — Converge to 6

Before handing off to taste evaluation:

1. List all generated options (7+ from SCAMPER + supplements)
2. Remove exact duplicates only — not similar ones, exact
3. Group options that are genuine variations of the same approach → keep the strongest representative
4. Target: **6 options** for evaluation (evidence-backed sweet spot: enough diversity, evaluable without overload)

**Diversity test** — each of the 6 options should answer yes to:
- Different mechanism? (not just variation in degree)
- Different assumption about user behavior?
- Different cost/effort profile?

If two options share all three, they are variations — merge them.

**Head-clustering read** — at curation, restate the six `stated_probability` values as one distribution over the curated six, summing to 1, and read that single distribution. The probabilities are the model's stated estimates, not a measured truth; use them to spot clustering, never to rank options. If most stated mass sits on options sharing one mechanism, the set reads diverse but was sampled from one cluster — add tail candidates and re-test. This reads the sample the generator produced for sampling; it does not accept the generator's diversity self-assessment.

---

## Option Format

Each option in `options-raw.md` must follow:

```
### Option N: [handle]

**Core idea**: One sentence — what would a user actually experience?
**Key mechanism**: What makes this work?
**Key assumption**: What must be true for this to succeed?
**SCAMPER origin**: Which lens generated this? (or "Crazy 8s supplement")
**Closest competitor**: What existing product does this most?
**name_origin**: user-words (the requester's own description) | coined (this wave minted it)
**stated_probability**: the probability stated for this candidate within the distribution it was drawn from, restated over the curated six at curation (a stated estimate, not a measurement)
```

The heading handle is an internal cross-reference label for the scoring table. Nothing downstream may read it as vocabulary: replacing a handle with an unrelated word must change no score, weight or ranking. A user-words name is the requester's description verbatim, shortened only to a phrase; a coined name describes the mechanism.

---

## Anti-Patterns to Avoid

| Anti-pattern | Why it fails | Correction |
|-------------|-------------|-----------|
| Generating one good idea and elaborating it | Confirmation bias — narrows too early | Apply all SCAMPER letters before stopping |
| "Improved version of the existing approach" | Not divergent — variation, not option | Apply E (Eliminate) or R (Reverse) |
| Filtering during generation ("that won't work") | Destroys divergent thinking | Generate everything, filter in taste phase |
| Options that share the same core mechanism | False diversity | Apply the diversity test and the head-clustering read before curating |
| Skipping HMW framing | Solution space collapses prematurely | HMW must precede any generation |

---

## DIVERGE Output for Brainstorming Phase

Produce `docs/feature/{feature-id}/diverge/options-raw.md` with:

1. **HMW question** — the validated framing
2. **SCAMPER options** — one per letter, each with name_origin and stated_probability recorded
3. **Crazy 8s supplements** — 2-4 additional structurally distinct options
4. **Curated 6** — with diversity test results including the head-clustering read
5. **Eliminated options** — brief note on why merged/removed

**Gate**: 6 curated options, each passing the 3-point diversity test, two tail candidates among the six — or one tail candidate whose mechanism differs from every head candidate's — name_origin marked on every option, before taste evaluation begins.
