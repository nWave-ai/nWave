# Tutorial: Requirements and UX Journey

**Time**: ~17 minutes (9 steps)
**Platform**: macOS or Linux (Windows: use WSL)
**Prerequisites**: Python 3.10+, Claude Code with nWave installed, [Tutorial 4](../tutorial-discovery/) completed (optionally [Tutorial 5: DIVERGE](../diverge-wave-guide/) for greenfield projects)
**What this is**: An interactive walkthrough of `/nw-discuss` -- nWave's requirements and UX journey command. You will turn a validated problem into structured user stories with acceptance criteria.

---

## What You'll Build

A complete requirements package -- user stories with Given/When/Then acceptance criteria, ready for architecture design.

**Before**: You have a validated problem from Tutorial 4 (developers lose track of useful links) and a `docs/feature/bookmark-cli/discover/problem-validation.md` with evidence. But you have no requirements, no user stories, and no definition of "done."

**After**: You have a UX journey map showing how the bookmark CLI should *feel* to use, structured user stories with real-world examples, BDD acceptance criteria, and a Definition of Ready validation confirming everything is ready for the DESIGN wave.

**Why this matters**: Jumping from "the problem is real" to "start coding" skips the most important question: what exactly should we build? `/nw-discuss` fills that gap with testable requirements.

---

## Step 1 of 9: Confirm Your Starting Point (~1 minute)

You should be in the `bookmark-cli` project from Tutorial 4, with discovery artifacts already committed.

Verify:

```bash
ls docs/feature/bookmark-cli/discover/problem-validation.md
```

You should see:

```
docs/feature/bookmark-cli/discover/problem-validation.md
```

Check that your discovery recommended proceeding:

```bash
head -30 docs/feature/bookmark-cli/discover/problem-validation.md
```

You should see your problem validation document with a recommendation (likely "PROCEED" or "PROCEED WITH CAUTION").

> **If `docs/feature/bookmark-cli/discover/` does not exist**: Complete [Tutorial 4](../tutorial-discovery/) first. This tutorial builds directly on its output.

> **If your discovery recommended KILL**: You can still follow this tutorial for practice. `/nw-discuss` works regardless of the discovery outcome -- but in a real project, you would pick a different idea first.

*Next: you will launch the discuss command and meet Luna, the product owner agent.*

---

## Step 2 of 9: Launch the Discussion (~1 minute)

Open Claude Code if it is not already running:

```bash
claude
```

Start the requirements conversation:

```
/nw-discuss bookmark-cli
```

> **AI output varies between runs.** Your conversation with Luna will differ from the examples below. That is expected -- Luna adapts to your answers and your discovery artifacts. What matters is the structure (questions, journey design, user stories), not the exact wording.

Luna (the product owner agent) will ask three setup questions before starting. You will see something like:

```
I'm Luna, your Experience-Driven Requirements Analyst. I've read your
discovery artifacts from docs/feature/bookmark-cli/discover/.

Before we begin, I need to understand the scope:

1. What type of feature is this?
   a) User-facing  b) Backend  c) Infrastructure  d) Cross-cutting

2. Should we start with a walking skeleton?
   a) Yes (greenfield)  b) Depends  c) No

3. Priority for UX research depth?
   a) Lightweight  b) Comprehensive  c) Deep-dive
```

For this tutorial, answer:

- **Feature type**: User-facing (option a)
- **Walking skeleton**: Yes (option a) -- this is a greenfield project
- **UX research depth**: Comprehensive (option b)

After your answers, Luna begins Phase 1: Deep Discovery. She will ask questions about how the bookmark CLI should feel to use.

**What just happened?** Luna read your `docs/feature/bookmark-cli/discover/problem-validation.md` to understand the validated problem. The three setup questions configure how deep the requirements process goes. "Comprehensive" gives you the full UX journey experience without the extended research of a deep-dive.

*Next: you will answer Luna's discovery questions about the user experience.*

---

## Step 3 of 9: Answer Luna's Discovery Questions (~3 minutes)

Luna's questions focus on the user's mental model -- what they type, what they see, how they feel. This is different from Scout's interview in Tutorial 4: Scout asked whether the *problem* is real; Luna asks what the *solution* should feel like.

Here is an example exchange (yours will differ):

**Luna asks about the first interaction:**
```
Walk me through the ideal first experience. A developer has just
installed bookmark-cli. What is the first thing they type? What do
they see? How should they feel?
```

**You answer** (use your real mental model):
```
They type "bm add https://docs.python.org/3/library/argparse.html"
with a tag like "--tag python,cli". They should see a brief
confirmation. It should feel instant -- no friction.
```

**Luna probes further:**
```
Good -- "instant, no friction" is the emotional target for saving.
Now the harder moment: retrieval. A week later, they need that link
but can't remember the exact URL. What do they type? What emotion
are they feeling when they start searching?
```

**You answer:**
```
They're feeling frustrated -- they know they saved it but can't find
it. They type something like "bm search python cli" and want to see
matching bookmarks immediately. The relief of finding it fast is the
key moment.
```

Luna will continue for 3-5 more questions, covering the save, search, and retrieve interactions.

> **If Luna asks a question you cannot answer**: Say so. "I haven't thought about that yet" is useful input. Luna will suggest options and ask you to pick.

**What just happened?** Luna gathered the raw material for the UX journey: what the user types at each step, what they expect to see, and how they should feel. She needs these concrete details before she can map the full journey.

*Next: you will see Luna turn your answers into a visual journey map.*

---

## Step 4 of 9: Review the Journey Output (~2 minutes)

After discovery, Luna produces visual journey artifacts. You will see her write files:

```
Creating docs/feature/bookmark-cli/discuss/journey-core-visual.md
Creating docs/feature/bookmark-cli/discuss/journey-core.yaml
```

> **You may see different file names.** Luna names artifacts based on the journey she discovers. The path pattern `docs/feature/{name}/discuss/journey-{name}.*` is what matters. Journey files are `.yaml` (structured data) and `-visual.md` (human-readable diagram).

The journey visual maps the complete experience from start to finish. Luna designed it using two ideas:

1. **Emotional arc** -- The journey tracks how the user feels at each step: frustrated (lost a link), hopeful (searching), relieved (found it). Luna designs for feelings, not just actions.
2. **Horizontal-first mapping** -- Luna mapped the complete journey (save, search, retrieve) before designing any individual feature. A coherent whole beats disconnected features.

You do not need to memorize these ideas. They explain why the journey artifact looks the way it does.

> **If Luna is still asking questions and has not produced artifacts yet**: Say "I think you have enough to sketch the journey now." Luna will proceed to visualization.

*Next: you will see Luna craft user stories from the journey.*

---

## Step 5 of 9: Read Luna's User Stories (~2 minutes)

After the journey visualization, Luna transitions to writing user stories. You will see her shift from asking questions to producing structured output:

```
Journey artifacts complete. Now I'll craft user stories informed by
what we designed.

Starting with the highest-value story from the journey:
the search-and-find moment (the emotional peak).
```

Luna writes user stories following a specific template. Here is an example of what you will see (your stories will differ):

```markdown
# US-01: Find a Saved Bookmark by Keyword Search

## Problem (The Pain)
Carlos Rivera is a backend developer who saves useful documentation
links throughout the week. He finds it frustrating to dig through
browser bookmarks when he needs a specific Python reference during
active debugging -- the context switch from terminal to browser
breaks his flow.

## Domain Examples
### Example 1: Happy Path
Carlos saved https://docs.python.org/3/library/argparse.html tagged
"python,cli" three days ago. He types `bm search python cli` and
sees the matching bookmark with URL and tags within 200ms.

### Example 2: Partial Match
Carlos types `bm search arg` and sees the argparse bookmark because
the URL contains "argparse" -- search covers URLs, tags, and titles.

### Example 3: No Results
Carlos types `bm search kubernetes` and sees "No bookmarks found for
'kubernetes'" -- clear feedback, not a silent empty output.
```

Notice three things about Luna's story template:

1. **Template structure** -- Each story has three sections: Problem, Domain Examples, and UAT Scenarios. This consistent structure makes stories scannable.
2. **Real names and data** -- "Carlos Rivera" and real URLs, not "User" and "example.com". Concrete details force concrete thinking and catch vague requirements.
3. **Problem-first** -- The story starts with pain, not a solution. This keeps the focus on the user's need rather than jumping to implementation.

Luna will produce 2-4 user stories covering the core journey (save, search, retrieve).

> **If Luna produces more than 5 stories**: Say "Let's focus on the core journey only -- save, search, retrieve." Luna will consolidate. Fewer stories means faster delivery in Tutorial 8.

**What just happened?** Luna started from the journey's emotional peaks and wrote stories that address the user's pain directly. The persona ("Carlos Rivera") comes from patterns Luna identified during discovery.

*Next: you will look at the acceptance criteria that make each story testable.*

---

## Step 6 of 9: Understanding Acceptance Criteria (~2 minutes)

Each user story ends with UAT Scenarios written in Given/When/Then format. Look at the bottom of any story Luna wrote:

```markdown
## UAT Scenarios (BDD)
### Scenario: Search by tag returns matching bookmark
Given Carlos has saved a bookmark tagged "python,cli"
When Carlos runs `bm search python`
Then Carlos sees the bookmark URL, title, and tags
```

Two things to notice:

1. **Given/When/Then format** -- Each scenario has exactly three parts: a starting condition (Given), an action (When), and a verifiable outcome (Then). You can read each scenario and know exactly what to test.
2. **Persona-driven** -- The scenarios use "Carlos" (the persona from the story), not abstract "the user." This keeps acceptance criteria grounded in the real use case Luna designed.

Luna writes these scenarios to the discuss artifacts:

```
Creating docs/feature/bookmark-cli/discuss/user-stories.md
```

**What just happened?** Luna translated the user stories into testable acceptance criteria. These Given/When/Then scenarios become the basis for automated tests when you reach the DELIVER wave. The format comes from Behavior-Driven Development (BDD), which bridges the gap between requirements and test code.

*Next: you will see Luna validate the stories against a readiness checklist.*

---

## Step 7 of 9: Definition of Ready Gate (~3 minutes)

Before handing off to the DESIGN wave, Luna validates every story against an 8-item checklist called the Definition of Ready (DoR). This is a hard gate that ensures requirements are complete enough to architect and build.

You will see Luna run the validation:

```
Running Definition of Ready validation...

| #  | Item                                  | Status |
|----|---------------------------------------|--------|
| 1  | Problem statement in domain language  | PASS   |
| 2  | User/persona with characteristics     | PASS   |
| 3  | At least 3 domain examples            | PASS   |
| 4  | UAT scenarios (Given/When/Then)       | PASS   |
| 5  | Acceptance criteria from UAT          | PASS   |
| 6  | Right-sized (1-3 days, 3-7 scenarios) | PASS   |
| 7  | Technical notes on constraints        | PASS   |
| 8  | Dependencies resolved or tracked      | PASS   |

DoR Status: PASSED (8/8)
```

> **Your DoR may not pass on the first try.** Luna sometimes catches gaps and fixes them herself ("Item 3 has only 2 examples -- adding a third"). If she asks you for input to fix a gap, answer based on your domain knowledge.

After DoR passes, Luna invokes her peer reviewer (Eclipse) for a final quality check:

```
Invoking peer review...

Review result: APPROVED
- Journey coherence: no orphan steps
- Emotional arc: smooth, no jarring transitions
- Shared artifacts: all tracked
- Antipatterns: none detected
```

> **If the reviewer finds issues**: Luna fixes them and re-submits. This may take 1-2 iterations. You do not need to intervene unless Luna asks you a question.

Luna then writes the final artifacts:

```
Creating docs/feature/bookmark-cli/discuss/dor-validation.md
Creating docs/feature/bookmark-cli/discuss/peer-review.md
```

**What just happened?** The Definition of Ready applies the same "validate before you proceed" principle from Tutorial 4, but at the requirements level. In Tutorial 4, the gate checked whether the *problem* was real. Here, the gate checks whether the *requirements* are complete. Each nWave wave validates before the next one begins.

*Next: you will review all your artifacts and commit them.*

---

## Step 8 of 9: Review and Commit Artifacts (~2 minutes)

Check what Luna created:

```bash
ls docs/feature/bookmark-cli/discuss/
```

You should see something like:

```
dor-validation.md
journey-core-visual.md
journey-core.yaml
outcome-kpis.md
story-map.md
user-stories.md
wave-decisions.md
```

> **Your file names will differ.** Luna names files based on the journey she designed. The path pattern `docs/feature/{name}/discuss/` is what matters. Luna also updates the SSOT at `docs/product/journeys/` with journey YAML files.

Commit everything:

```bash
git add -A && git commit -m "docs: UX journey and requirements from discuss session"
```

You should see:

```
[main ...] docs: UX journey and requirements from discuss session
```

*Next: a recap of what you built and where it fits in the nWave workflow.*

---

## Step 9 of 9: What You Built (~1 minute)

You started with a validated problem and ended with a complete requirements package:

1. **UX journey map** -- How the bookmark CLI should feel at every step, with emotional annotations
2. **User stories** -- Problem-first stories with real personas, real data, and BDD acceptance criteria
3. **Definition of Ready** -- 8-item validation confirming the requirements are complete

### What You Didn't Have to Do

- Write user stories from scratch
- Guess what acceptance criteria to include
- Hire a PM to facilitate requirements gathering
- Hold stakeholder meetings to agree on scope
- Wonder whether your requirements are "detailed enough"

### The Wave So Far

```
DISCOVER             DIVERGE              DISCUSS              DESIGN
(/nw-discover)       (/nw-diverge)        (/nw-discuss)        (/nw-design)
────────────────     ────────────────     ────────────────     ────────────────
"Is the problem      "Which direction     "What should we      "How should we
 real?"               should we go?"       build?"              build it?"

Evidence-based       Design exploration   Journey + stories    Architecture
validation           + recommendation     + acceptance         decisions
                     (optional)           criteria

Tutorial 4           Tutorial 5           This tutorial        Tutorial 7
```

Each wave validates before the next one begins. No handoff without evidence. DIVERGE is optional -- skip it for brownfield features where the approach is clear.

---

## Next Steps

- **[Tutorial 7: Architecture Design](../tutorial-design/)** -- Take your requirements into `/nw-design` to make architecture decisions before writing code
- **Review the journey visual** -- Open `docs/feature/bookmark-cli/discuss/journey-core-visual.md` and trace the emotional arc from frustration to relief
- **Read a user story aloud** -- If the Given/When/Then reads naturally, the acceptance criteria are well-written. If it sounds awkward, Luna may have been too technical.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Luna does not start after `/nw-discuss` | Make sure nWave is installed. Run `/nw-help` to verify. |
| Luna skips the journey and goes straight to stories | Say `*journey "bookmark-cli"` to explicitly start the journey phase. |
| DoR validation fails repeatedly | Say "let's simplify -- focus on the 2 most important stories only." Fewer stories are easier to validate. |
| No `docs/feature/bookmark-cli/discuss/` directory after the session | Luna writes journey artifacts after the discovery questions. If you ended the session early, run `/nw-discuss bookmark-cli` again. |
| Luna asks too many questions | Say "I think you have enough to sketch the journey now." Luna will proceed to visualization. |
| Want to start fresh | Delete `docs/feature/bookmark-cli/discuss/` and run `/nw-discuss` again. |

---

**Last Updated**: 2026-04-06
