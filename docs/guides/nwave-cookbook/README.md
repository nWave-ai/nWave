# nWave Cookbook

Copy-paste recipes for using nWave's skills and agents to improve a project.
Each recipe is grounded in this repository's real files and sizes.

Back to the [nWave README](../../../README.md) · [How-to guides](../HOW-TO.md)

Run the categories in the order below when you can. Each one feeds the next.

| # | Category | Use it when |
|---|---|---|
| 1 | Architecture Mapping | Before any change, or when you are new to the code |
| 2 | Code Refactoring | You have a specific file you want to make cleaner |
| 3 | Documentation Audit | Docs feel confusing, or you want to check them |
| 4 | Test Quality | The test suite is slow, noisy, or you do not trust it |
| 5 | Feature Delivery | You are about to build something new |

## The three rules

1. **Scan before you change.** Ask for a report first, then decide.
2. **Get a second opinion.** A reviewer agent checks the report or the change. It does not edit.
3. **Change in one batch, test once.** Apply the planned edits together, run the tests at the end, then commit.

Think of it like a building inspector. The person who did the work should not be the only one who signs off on it.

---

## 1. Architecture Mapping

**Why this category first:** `nwave_ai/platform/` is about 6,500 lines across 20+ files. That makes it hard to see where one job ends and the next begins. `nwave_ai/outcomes/` already has a clean layout (domain, application, ports, adapters). Use it as the model.

Run these in order. Each one feeds the next.

### 1.1 Map the ownership boundaries in `platform/`

*What it does:* Finds which files belong together, which ones mix concerns, and which ones are imported by everything else.
*Agent:* `@nw-solution-architect`

```text
@nw-solution-architect Scan nwave_ai/platform/ — 20+ modules, ~6,500 lines.
Identify: (1) which files share the same bounded context, (2) which represent
infrastructure concerns leaking into domain logic, (3) which have the highest
coupling (import fan-in/fan-out).
Output a module-responsibility table and highlight the top 3 high-coupling smells.
Then compare to nwave_ai/outcomes/ — which uses clean hexagonal structure
(domain/application/ports/adapters) — and explain the gap between them.
```

### 1.2 Find the natural seams in `config.py`

*What it does:* `config.py` is 1,163 lines. It probably mixes reading, writing, checking, and default values. This recipe names those mixed parts. It does not change anything yet.
*Agent:* `@nw-ddd-architect`

```text
@nw-ddd-architect Apply bounded-context analysis to nwave_ai/platform/config.py
(1,163 lines). Identify: (1) distinct sub-domains mixed in this file,
(2) any aggregate roots and their invariants, (3) where the ubiquitous language
breaks down (mixed metaphors in naming).
Propose context boundaries — not refactors yet, just where the seams are.
Reference: nwave_ai/outcomes/domain/ as the target pattern.
```

### 1.3 Propose a split, then have it challenged

*What it does:* Turns the seams into a concrete proposal (at most 3 new sub-packages). Then a reviewer tries to break it before anyone commits to it.
*Skill and agent:* `/nw-design`, then `@nw-solution-architect-reviewer`

```text
/nw-design Using the platform/ boundary map above, propose splitting
nwave_ai/platform/ into at most 3 focused sub-packages. For each:
  1. Name the SSOT concern it owns
  2. List which current files move there
  3. State the invariant it enforces
  4. Name what currently imports it (blast radius)

Then invoke @nw-solution-architect-reviewer to challenge the split
before any changes are made.
```

### 1.4 Find what breaks when outside services are down

*What it does:* `nwave_ai/update/` talks to outside systems (release discovery, package activity). This recipe lists each outside dependency and what the user would see if it failed.
*Skill:* `/nw-stress-analysis`

```text
/nw-stress-analysis Focus on nwave_ai/update/ — specifically release_discovery.py
and package_activity.py. These modules reach external systems. Identify:
  1. Every external/nondeterministic dependency
  2. What degrades vs. fails hard when each is unavailable
  3. Which failure paths propagate to the user CLI as visible errors

Output: dependency | failure mode | propagation path |
        current mitigation | recommended guard
```

### 1.5 Find the files that change the most

*What it does:* `upgrade_shell.py` has the most commits (6). This checks whether that churn comes with high complexity. Frequent edits to complicated code are a common source of bugs.
*Skill:* `/nw-hotspot`

```text
/nw-hotspot Analyze the nwave_ai/ directory. Find the top 10 files by change
frequency over the full git history. For each: commit count, current line count,
cyclomatic complexity estimate. Flag any file where churn × complexity exceeds
a defensible threshold (use your judgment, explain the threshold).
Confirm: is upgrade_shell.py in the top tier? Explain why it keeps changing.
```

---

## 2. Code Refactoring

**The pattern:** Scan → Review → Apply.

Never ask for the scan and the change in the same recipe. The separate review catches false alarms and misses that the first scan made.

**Refactoring levels (RPP):** `/nw-refactor` works through six levels, from easiest to deepest:

| Level | Name | Looks at |
|---|---|---|
| L1 | Readability | Names, dead code, magic numbers |
| L2 | Complexity | Long methods, deeply nested conditions |
| L3 | Responsibilities | Classes doing too many jobs |
| L4 | Abstractions | Missing or wrong abstractions |
| L5 | Design Patterns | Where a known pattern would fit |
| L6 | SOLID++ | Dependency and interface design |

### 2.1 Analysis-only report for L1–L2

*What it does:* Lists problems in `config.py` and changes nothing.
*Agent and skill:* `@nw-software-crafter` with `/nw-refactor`

```text
@nw-software-crafter Analyze nwave_ai/platform/config.py for RPP L1–L2
violations. Analyze only — report violations without applying any edits.
Report each violation as:
  file:line | level | type | one-line description

L1 (Readability): misleading names, unexplained abbreviations,
  inconsistent casing, magic numbers, dead code
L2 (Complexity): methods too long to read in one screen,
  deeply nested conditionals, complex boolean expressions

Findings list only, sorted by severity.
```

### 2.2 Independent check of the report

*What it does:* A reviewer confirms or rejects each finding, and looks for ones the first scan missed. The reviewer does not edit the file.
*Skill and agent:* `/nw-review`, then `@nw-software-crafter-reviewer`

```text
/nw-review Independently assess the L1–L2 findings from the config.py scan.
For each finding: CONFIRM or REJECT with one-line reason.
Additionally: scan config.py yourself for any L1–L2 violations the initial
scan missed. Output two lists:
  1. Confirmed findings in priority order
  2. New findings not in the original scan
```

### 2.3 Apply the confirmed L1 changes

*What it does:* Makes all the confirmed readability fixes in one go, runs the tests once, and commits. It then shows a before/after picture and suggests the next file to work on.
*Agent:* `@nw-software-crafter`

```text
@nw-software-crafter Apply /nw-refactor L1 to nwave_ai/platform/config.py
using the confirmed findings list only. Rules:
  1. Apply all L1 changes as one batch in a single editing session
  2. Run the test suite once, after all edits. If it is red, fix the
     production code. Do NOT modify tests to make them pass
  3. When green, commit once:
     refactor(config): apply RPP L1 readability batch
  4. Do NOT apply any L2 changes in this pass

When L1 is complete: produce an ASCII before/after diagram of the top 5
most-improved names. Then propose the next highest-value refactoring target
(file + RPP level + one-line reason why that file next).
```

---

## 3. Documentation Audit

**Why it matters:** `docs/guides/` has 40+ entries. Docs go wrong in a common way called "collapse." A tutorial starts explaining theory. A how-to starts teaching concepts. Reference pages get mixed into guides. Each type should do one job.

**The four DIVIO types:**

| Type | Reader's question | Good for |
|---|---|---|
| Tutorial | "Teach me by doing" | Step-by-step learning |
| How-to | "How do I do X?" | Goal-based recipes |
| Reference | "What exactly is Y?" | Facts and options |
| Explanation | "Why does it work this way?" | Background and reasoning |

### 3.1 Sort every guide into a type

*What it does:* Builds a table of which guides are which type, and where each one has drifted.
*Agent:* `@nw-documentarist`

```text
@nw-documentarist Audit docs/guides/ using DIVIO/Diataxis classification.
For each document or directory:
  1. Classify: tutorial | how-to | reference | explanation
  2. State whether the content matches that type (yes / partial / no)
  3. Flag any collapse: mixed types in one doc

Output as a table:
  filename | classified-as | content-match | collapse? | top-fix-needed
Sort by severity (worst collapse first).
```

### 3.2 Fix the two worst cases

*What it does:* Rewrites the opening of the two worst guides to match their type. Then a reviewer checks that nothing important was lost.
*Skill and agent:* `/nw-document`, then `@nw-documentarist-reviewer`

```text
/nw-document Using the documentarist audit, pick the 2 documents with the
worst collapse score. For each:
  1. Rewrite the opening section to match its classified type
  2. Extract any mixed-type content into a separate correctly-typed stub
     (don't write the stub — just show its proposed title and type)
Show before/after for each rewrite.
Invoke @nw-documentarist-reviewer to confirm the rewrite resolved the
collapse without dropping essential content.
```

### 3.3 First-time reader check on the README and CONTRIBUTING

*What it does:* Pretends to be someone who has never seen nWave. Scores how quickly they can run something, and how clear the setup steps are.
*Agent:* `@nw-documentarist`

```text
@nw-documentarist Review README.md and CONTRIBUTING.md as a first-time nWave
user who has never seen the tool. Assess:
  1. Time-to-first-working-command: how many steps before anything runs?
  2. Concept model: is the mental model explained before the commands?
  3. Error coverage: are common failure modes documented?
  4. Prerequisite clarity: are version requirements explicit?

Rate each criterion 1–5 with one sentence of evidence. End with the single
highest-ROI fix for each file.
```

---

## 4. Test Quality

**The order matters:** Clean up first, then look for gaps.

If you run mutation testing (which breaks code on purpose to see if tests notice) on a messy test suite, the results are misleading. Redundant tests cover the same code, so gaps look smaller than they are.

### 4.1 Propose tests to delete

*What it does:* Finds tests that check Python itself rather than nWave, tests that repeat each other, and parameter sets that test the same path. Changes nothing.
*Skill:* `/nw-optimize-tests`

```text
/nw-optimize-tests Scan the nwave_ai test suite and identify:
  1. Tests that assert Python language guarantees rather than nWave behavior
  2. Parametrize inflation: test sets where multiple params exercise the
     same code path (same branch, same logic)
  3. Exact or near-duplicate test functions

For each category: list file:test_name. Estimate total tests-to-delete
and coverage impact (expected: zero reduction in meaningful coverage).
Do NOT delete anything — produce the deletion proposal only.
```

### 4.2 Independent veto on the deletions

*What it does:* A reviewer blocks any deletion that would remove a real behavior check.
*Agent:* `@nw-test-optimizer-reviewer`

```text
@nw-test-optimizer-reviewer Independently review the test deletion proposal.
For each proposed deletion:
  1. Confirm or refute the coverage-impact estimate (run coverage if needed)
  2. APPROVE or VETO — veto if deleting removes observable-behavior coverage
  3. For vetoes: state what behavior the test pins that nothing else covers

Output: approved deletions list / vetoed list with veto reason.
Only approved deletions proceed to execution.
```

### 4.3 Find gaps in the two riskiest files

*What it does:* Breaks the code on purpose in small ways. Any break the tests miss is a behavior nobody is checking.
*Skill:* `/nw-mutation-test`

```text
/nw-mutation-test Run an explicit mutation probe on:
  - nwave_ai/upgrade_shell.py   (hottest by change frequency: 6 commits)
  - nwave_ai/platform/config.py  (largest file: 1,163 lines)

For each surviving mutant:
  file:line | mutation type | behavior the survivor exposes |
  the test that would kill it

Sort by behavioral risk (highest first). Cap at top 10 survivors per file.
```

---

## 5. Feature Delivery

**The rule:** Check that the problem is real before you design anything.

A solution to a problem nobody has wastes the whole delivery. Ten minutes of discovery is cheaper than building the wrong thing.

**The flow:** discover → diverge → deliver.

### 5.1 Check the problem is real

*What it does:* Lists the assumptions in your problem statement and what evidence would confirm or disprove each one.
*Skill:* `/nw-discover`

```text
/nw-discover The team reports that: [paste the specific pain point here].

Before any design or code:
  1. List every assumption embedded in this problem statement
  2. For each assumption: what evidence validates it? what invalidates it?
  3. What user or system signal confirms the problem is real and frequent?
  4. What would make this problem not worth solving?

Output: validated problem statement WITH evidence
     OR "not yet validated — still need: [specific evidence]"
```

### 5.2 Generate three different options

*What it does:* Proposes three approaches that are truly different, not three versions of one idea. A reviewer checks that they differ.
*Skill and agent:* `/nw-diverge`, then `@nw-diverger-reviewer`

```text
/nw-diverge Given the validated problem: [paste validated statement here].

Generate exactly 3 design directions. Each must include:
  1. The JTBD (job-to-be-done) it solves
  2. The key trade-off (what this direction gives up)
  3. The minimum testable version — the skateboard: something a person
     can actually use right now, not a component of the final thing
  4. The signal that would prove this direction is wrong

Invoke @nw-diverger-reviewer to verify the 3 options are structurally
diverse and not 3 variations of the same approach.
```

### 5.3 Deliver with a clear pass/fail test

*What it does:* Starts delivery with an explicit "done" definition. An independent examiner checks the result from the user's point of view.
*Skill:* `/nw-deliver`

```text
/nw-deliver [one-sentence Request — be specific, not "add feature X"]

Route: Spine waves
Deliverable type: [code | plugin | skill | documentation]
Exit criteria: [specific observable behavior — not "it works" but e.g.
  "nwave doctor shows all checks green" or
  "the CLI outputs X when given input Y with flag Z"]
Acceptance oracle: what nw-user-examiner will independently verify —
  user-visible behavior only, no internal implementation details
```

---

## Related

- [How-to guides](../HOW-TO.md) — task-oriented procedures for nwdes delivery, install and upgrade.
- [Skill reference](../../reference/skills/index.md) — every `/nw-*` skill and its inputs.
- [Refactoring tutorial](../tutorial-refactoring/README.md) — a guided walk through the refactoring levels.
- [Mikado method](../../reference/skills/nw-mikado.md) — the experimental planner for large refactors, used in the refactoring recipes.

## Glossary

- **Recipe** — one copy-paste instruction, with its agent or skill and what it produces.
- **Agent** — a specialist helper, written as `@name`. It does the work.
- **Reviewer** — an agent whose job is to check someone else's work. It does not edit.
- **Skill** — a reusable procedure, written as `/name`.
- **Batch** — applying all planned edits together, then testing once.
- **Mutation testing** — deliberately breaking code to see whether the tests catch it.
- **Collapse** — when one document mixes several kinds of writing.
- **Seam** — a place where code can be split without breaking things.
- **Blast radius** — how many other files would be affected if this one changed.

## Where this came from

Built from the nWave skill and agent definitions in `nWave/skills/` and `nWave/agents/`, and checked against this repository's file sizes and commit history. The refactoring recipes follow `nWave/skills/nw-refactor/SKILL.md`.
