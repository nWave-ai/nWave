# Tutorial: Understanding the Delivery Pipeline

**Time**: ~16 minutes hands-on (12 steps)
**Platform**: macOS or Linux (Windows: use WSL)
**Prerequisites**: [Tutorial 1](../tutorial-first-delivery/) completed (or Tutorial 2). You should have seen `/nw-deliver` run at least once.
**What this is**: A conceptual walkthrough, not a hands-on coding tutorial. You will explore artifacts that already exist in your completed project.

---

## What You'll Learn

After Tutorial 1, you watched `/nw-deliver` produce working code from failing tests. But what actually happened? This tutorial answers that question.

**Before**: You see a wall of scrolling output and hope it worked.

**After**: You can read every phase, understand every agent's role, and trace every decision through the git log. You trust the tool because you understand it.

---

## Step 1 of 12: Open Your Project (~1 minute)

Open your completed Tutorial 1 project (or Tutorial 2):

```bash
cd tutorial-ascii-art   # or md-converter if you did Tutorial 2
```

Verify you are in the right directory:

```bash
ls docs/
```

You should see:

```
evolution/  feature/
```

> **If you see no `docs/` directory**: You may be in the wrong folder. Run `ls` to check your surroundings, then `cd` to the correct project directory.

The delivery pipeline takes your feature description and turns it into tested, reviewed code. In the next step you will see the phases it goes through.

*Next: you will see the pipeline as a whole.*

---

## Step 2 of 12: The Pipeline at a Glance (~1 minute)

Every `/nw-deliver` run follows a seven-phase pipeline. You do not need to memorize each phase -- just know the flow goes from planning to code to quality checks:

```
/nw-deliver "your feature"
    |
    1. ROADMAP         Plans the work
    2. EXECUTE         Writes code via TDD
    3. REFACTOR        Cleans up code
    4. REVIEW          Adversarial critique
    5. MUTATION TEST   Validates test quality
    6. VERIFY          Integrity check
    7. FINALIZE        Archives artifacts
```

You will explore the important phases (roadmap, execute, review, mutation test) in the steps that follow. For now, just note where the pipeline stores its work:

- **`docs/feature/`** -- in-progress artifacts (roadmap, reports)
- **`docs/evolution/`** -- permanent record after finalization

*Next: you will find the roadmap file.*

---

## Step 3 of 12: Finding the Roadmap (~1 minute)

The solution architect reads your tests and creates a step-by-step plan. Find it:

```bash
ls docs/feature/*/roadmap.json
```

You should see something like:

```
docs/feature/image-to-ascii-art/roadmap.json
```

> **If no `docs/feature/` directory exists**: Your project may have been cleaned up after finalization. That is normal -- the evolution document in `docs/evolution/` is the permanent record. Skip to Step 10 to read the git log instead.

Open the roadmap:

```bash
cat docs/feature/*/roadmap.json
```

You should see something like:

```yaml
project_id: image-to-ascii-art
methodology: Outside-In TDD

steps:
  01-01:
    title: "PPM image parsing"
    acceptance_criteria:
      - "Reads P3 format PPM files"
    files_to_modify:
      - src/ascii_art/__init__.py
```

> **Your roadmap will differ.** The structure is what matters, not the exact content.

The next step explains what these fields mean.

*Next: you will learn how to read the roadmap's structure.*

---

## Step 4 of 12: Reading the Roadmap (~1 minute)

Here is what the top-level fields mean:

```yaml
project_id: image-to-ascii-art        # Derived from your feature description
methodology: Outside-In TDD            # Always TDD -- never code-first

steps:
  01-01:
    title: "PPM image parsing"
    acceptance_criteria:
      - "Reads P3 format PPM files"
      - "Returns pixel brightness values"
    files_to_modify:
      - src/ascii_art/__init__.py
```

> **Your roadmap will differ from this example.** The architect generates a plan based on your specific tests. The structure is what matters, not the exact content.

Three fields to notice:

1. **project_id** -- identifies the feature. Derived from your description.
2. **methodology** -- always Outside-In TDD. The pipeline never writes code without tests first.
3. **steps** -- the ordered list of work. Each step has a title, acceptance criteria, and files to modify.

The roadmap is reviewed by an independent reviewer before execution begins. If the reviewer finds problems, the architect revises it automatically.

*Next: you will learn three rules that govern how steps are written.*

---

## Step 5 of 12: Roadmap Step Rules (~1 minute)

Look at the step entry from the previous example:

```yaml
  01-01:
    title: "PPM image parsing"
    acceptance_criteria:
      - "Reads P3 format PPM files"
    files_to_modify:
      - src/ascii_art/__init__.py
```

Three rules govern every step:

1. **Step IDs use NN-NN format** (01-01, 01-02). The first number is the phase, the second is the step within that phase. The crafter executes them in order.
2. **Acceptance criteria describe WHAT, not HOW**. "Returns pixel brightness values" -- not "use a for loop to iterate pixels." The architect owns the what; the crafter owns the how.
3. **files_to_modify scopes each step**. The crafter only touches listed files, preventing scope creep.

*Next: you will see how the crafter turned each step into code.*

---

## Step 6 of 12: The TDD Cycle (~2 minutes)

For each roadmap step, the software crafter runs a strict TDD cycle:

```
RED             Run test -- must FAIL (proves the test checks something real)
    |
GREEN           Write minimum code to pass ALL tests
    |
COMMIT          Commit with detailed message
```

**Why this matters**: Every line of production code exists because a test demanded it. No speculative code. No "I might need this later."

Look at the git log to see this in action:

```bash
git log --oneline
```

You should see commits like:

```
abc1234 feat(ascii-art): brightness mapping - step 01-02
def5678 feat(ascii-art): PPM parsing - step 01-01
```

Each commit represents a completed TDD cycle.

*Next: you will inspect a single commit to see what happened inside a cycle.*

---

## Step 7 of 12: Inside a TDD Commit (~1 minute)

Pick any commit and inspect it:

```bash
git show --stat HEAD~1
```

You should see something like:

```
commit def5678...
Author: ...
Date:   ...

    feat(ascii-art): PPM parsing - step 01-01

 src/ascii_art/__init__.py | 25 +++++++++++++++++++++++++
 tests/test_ascii_art.py   |  8 ++------
 2 files changed, 27 insertions(+), 6 deletions(-)
```

Two things to notice:

1. **Both test files and production files changed in the same commit** -- proof that tests and code were written together, not after the fact.
2. **The Deterministic Execution System (DES) enforces every phase.** If the crafter tries to skip RED and jump straight to GREEN, the system blocks it.

> **If you see more commits than expected**: The crafter may write multiple unit tests per step. Each step still produces exactly one commit at the end.

*Next: you will learn what the adversarial reviewer checks.*

---

## Step 8 of 12: The Adversarial Review (~2 minutes)

After all steps execute and refactoring completes, an independent reviewer agent inspects the entire feature. This reviewer runs on a separate model -- it has no knowledge of the crafter's reasoning.

The reviewer checks three key dimensions:

| Dimension | What It Catches |
|-----------|----------------|
| Test budget | Too many tests? Budget is 2x the number of distinct behaviors. |
| Testing Theater | Tests that always pass regardless of implementation. |
| External validity | Feature is wired to an entry point, not just floating code. |

If the reviewer finds issues, the crafter fixes them automatically. Maximum two rounds -- after that, the workflow stops for your manual intervention.

*Next: you will see how mutation testing validates your tests catch real bugs.*

---

## Step 9 of 12: Mutation Testing (~2 minutes)

Code coverage tells you which lines ran. Mutation testing tells you whether your tests would **catch a bug** on those lines.

Here is how it works:

1. The tool makes a small change (**mutation**) to your production code -- for example, changing `>` to `>=`
2. It runs your tests against the mutated code
3. If your tests **catch** the mutation (fail), the mutant is "killed" -- good. If your tests **miss** the mutation (still pass), the mutant "survived" -- your tests have a gap

The **kill rate** is the percentage of mutants killed. The quality gate requires 80% or higher. Below that, the pipeline asks for more tests before proceeding.

> **If mutation testing reports surviving mutants**: The report in `docs/feature/*/mutation/mutation-report.md` shows exactly which mutations survived and in which files.

*Next: you will trace the full story through the git log.*

---

## Step 10 of 12: Tracing the Git Log (~1 minute)

Everything the pipeline did is traceable through commits. View them:

```bash
git log --oneline --all
```

You should see something like:

```
abc1234 feat(ascii-art): brightness mapping - step 01-02
def5678 feat(ascii-art): PPM parsing - step 01-01
9876543 test(ascii-art): add acceptance tests
```

Each message follows the pattern `feat({feature}): {description} - step {step-id}`, linking directly back to the roadmap. You can trace any line of code back to the roadmap step that required it.

> **If you see extra commits**: Refactoring and review fixes produce additional commits beyond the TDD steps. That is expected.

*Next: you will find the permanent record of the delivery.*

---

## Step 11 of 12: The Evolution Document (~1 minute)

The finalize phase creates a permanent record. Find it:

```bash
ls docs/evolution/
```

You should see:

```
image-to-ascii-art.md
```

This evolution document contains a summary of the feature, the steps taken, quality gates passed, and mutation testing results. It is the single source of truth for what was delivered and why.

*Next: a summary of what you now know.*

---

## Step 12 of 12: What You Now Know (~1 minute)

| Question | Answer |
|----------|--------|
| Who planned the work? | The solution architect, reviewed before execution |
| Who wrote the code? | The software crafter, through strict TDD |
| Who reviewed the code? | An independent reviewer on a separate model |
| How do I know the tests are real? | Mutation testing -- 80%+ kill rate required |
| How do I trace a decision? | Git log + roadmap step IDs |
| Can the crafter skip steps? | No -- DES enforces every TDD phase |

---

## Next Steps

- **Try it yourself**: Run `/nw-deliver` on a new feature in your Tutorial 1 or 2 project. This time, watch the output with the pipeline phases in mind.
- **[Tutorial 4: From Idea to Validated Problem](../tutorial-discovery/)** -- Start from the very beginning of the nWave workflow with `/nw-discover`
- **[Tutorial 13: Validating Your Test Suite](../tutorial-mutation-testing/)** -- Deep dive into mutation testing as a standalone tool

---

## Reference: All Seven Review Dimensions

The adversarial reviewer (Step 8) checks these seven dimensions:

| Dimension | What It Catches |
|-----------|----------------|
| Test budget | Too many tests? Budget is 2x the number of distinct behaviors. |
| Port-to-port | Tests must enter through public API, not internal classes. |
| Testing Theater | Tests that always pass regardless of implementation. |
| Hexagonal compliance | Mocks only at **port boundaries** (the interfaces where your code talks to external systems like databases or APIs), never inside the core domain logic. |
| Business language | Tests and code use domain terms, not technical jargon. |
| External validity | Feature is wired to an entry point, not just floating code. |
| Code smells | Detection of poor design patterns (duplicated logic, overly long functions, tight coupling) across refactoring levels. |

---

## Troubleshooting

| Symptom | Explanation |
|---------|-------------|
| No `docs/feature/` directory | The finalize phase archives and may clean up. Check `docs/evolution/` instead. |
| Roadmap has more steps than expected | The architect breaks work into small, testable increments. More steps = more granularity, not more complexity. |
| Git log shows extra commits | Refactoring and review fixes produce additional commits beyond the TDD steps. |
| Mutation report shows surviving mutants | Not a failure unless kill rate drops below 80%. Some mutations are semantically equivalent (e.g., changing an unreachable branch). |

---

**Last Updated**: 2026-02-17
