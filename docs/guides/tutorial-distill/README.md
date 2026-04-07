# Tutorial: Generating Acceptance Tests

**Time**: ~12 minutes (7 steps)
**Platform**: macOS or Linux (Windows: use WSL)
**Prerequisites**: Python 3.10+, Claude Code with nWave installed, [Tutorial 7](../tutorial-design/) completed
**What this is**: An interactive walkthrough of `/nw-distill` -- nWave's acceptance test generation command. You will turn user stories and architecture documents into executable BDD (Behavior-Driven Development) acceptance tests.

---

## What You'll Build

A complete acceptance test suite -- Given/When/Then scenarios in `.feature` files with pytest-bdd step definitions, ready for `/nw-deliver` to implement against.

**Before**: You have requirements from Tutorial 6 (user stories, acceptance criteria) and architecture from Tutorial 7 (hexagonal design, component boundaries, ADRs). But you have no executable tests, no walking skeleton, and no way to know when the feature is "done."

**After**: You have `.feature` files with BDD scenarios covering happy paths, error paths, and edge cases. You have pytest-bdd step definitions wired to driving ports. You have a walking skeleton that defines the simplest end-to-end user journey. Everything is tagged for one-at-a-time implementation in the DELIVER wave.

**Why this matters**: Without executable acceptance tests, "done" is a matter of opinion. `/nw-distill` turns your requirements into a concrete, runnable definition of done -- so when `/nw-deliver` makes all tests green, you know the feature works.

---

## Step 1 of 7: Confirm Your Starting Point (~1 minute)

You should be in the `bookmark-cli` project from Tutorial 7, with architecture artifacts committed.

Verify your requirements exist:

```bash
ls docs/feature/bookmark-cli/discuss/user-stories.md
```

You should see:

```
docs/feature/bookmark-cli/discuss/user-stories.md
```

Verify your architecture exists:

```bash
ls docs/feature/bookmark-cli/design/architecture-design.md
```

You should see:

```
docs/feature/bookmark-cli/design/architecture-design.md
```

> **If either file is missing**: Complete the prerequisite tutorial first. `/nw-distill` reads both requirements and architecture to generate tests. [Tutorial 6](../tutorial-discuss/) produces requirements; [Tutorial 7](../tutorial-design/) produces architecture.

*Next: you will launch the distill command and answer Quinn's setup questions.*

---

## Step 2 of 7: Launch the Distill Session (~1 minute)

In Claude Code, type:

```
/nw-distill bookmark-cli
```

> **AI output varies between runs.** Your session with Quinn will differ from the examples below. That is expected -- Quinn generates tests based on your specific user stories and architecture. What matters is the structure (decisions, feature files, step definitions), not the exact wording.

Quinn (the acceptance test designer agent) will ask four setup questions. Answer them as shown:

| Question | Answer | Why |
|----------|--------|-----|
| Feature scope? | **Core feature** (a) | This is the primary application |
| Test framework? | **pytest-bdd** (a) | We are building in Python |
| Integration approach? | **Mocks for external only** (c) | Sensible default for a CLI with no external services |
| Infrastructure tests? | **No** (b) | Functional tests only for now |

<details>
<summary>Alternative answers for different project types</summary>

- **Feature scope**: Choose "Extension" for adding to an existing feature, or "Bug fix" when writing regression tests for a known defect.
- **Test framework**: Choose "Cucumber" for JVM projects, "SpecFlow" for .NET, or "Custom" if you have an existing test harness.
- **Integration approach**: Choose "Real services" if you have a running dev environment, or "Test containers" for Docker-based integration testing.
- **Infrastructure tests**: Choose "Yes" if your feature includes deployment, CI/CD, or infrastructure-as-code changes.

</details>

**What just happened?** Quinn read your user stories and architecture documents to understand what to test and how the system is structured. These four decisions configure the test suite -- scope determines scenario depth, framework determines output format, integration approach determines how step definitions connect to services, and infrastructure testing adds or skips deployment scenarios.

*Next: Quinn will design the walking skeleton -- your first end-to-end test.*

---

## Step 3 of 7: Watch Quinn Design the Walking Skeleton (~2 minutes)

After your answers, Quinn starts with the walking skeleton -- the simplest scenario that proves a user can accomplish their goal end-to-end. You will see:

```
Designing walking skeleton...

The walking skeleton answers: "Can a user save a bookmark and find it
again?" This is the smallest scenario with observable user value.

Creating tests/acceptance/bookmark_cli/acceptance/walking-skeleton.feature
```

The walking skeleton `.feature` file will look something like:

```gherkin
Feature: Bookmark save and retrieve
  As a developer who saves useful links
  I want to save a bookmark and find it later
  So that I never lose a useful reference

  @walking-skeleton
  Scenario: Save a bookmark and find it by keyword search
    Given Carlos has no saved bookmarks
    When Carlos saves "https://docs.python.org/3/library/argparse.html" tagged "python,cli"
    Then Carlos can find the bookmark by searching "python"
    And the result shows the URL and tags
```

Two things to notice:

1. **Business language only** -- The scenario says "Carlos saves" and "Carlos can find," not "POST to /bookmarks endpoint" or "INSERT INTO bookmarks table." Quinn writes in the language of your user stories, not your architecture.
2. **Observable outcome** -- The Then clause describes what the user sees ("the result shows the URL and tags"), not what the system does internally.

> **Your walking skeleton will differ.** Quinn picks the scenario based on the emotional peak from your UX journey (Tutorial 6). The pattern is what matters: a single scenario that proves end-to-end value.

*Next: Quinn will generate the full scenario suite covering happy paths, errors, and edge cases.*

---

## Step 4 of 7: Review the Full Scenario Suite (~3 minutes)

After the walking skeleton, Quinn generates milestone feature files for each user story. You will see phases scroll by:

```
Designing milestone scenarios...

  Creating tests/acceptance/bookmark_cli/acceptance/milestone-1-search.feature
  Creating tests/acceptance/bookmark_cli/acceptance/milestone-2-tagging.feature

Designing error path scenarios (targeting 40%+ coverage)...

  Adding: Scenario: Search with no results returns clear message
  Adding: Scenario: Save bookmark with invalid URL shows validation error
  Adding: Scenario: Save duplicate bookmark warns user

Creating step definitions...
  Creating tests/acceptance/bookmark_cli/acceptance/steps/conftest.py
  Creating tests/acceptance/bookmark_cli/acceptance/steps/bookmark_steps.py

Invoking peer review (Sentinel)...
  Review result: APPROVED
  - Error path ratio: 42% (target: 40%)
  - Business language: PASS (zero technical terms in .feature files)
  - Hexagonal boundary: PASS (steps invoke driving ports only)
```

> **Your files and scenario count will differ.** Quinn generates scenarios from your specific user stories. A typical bookmark CLI gets 2-3 feature files with 10-20 scenarios total.

The peer review checks three mandates that Quinn must satisfy:

1. **Hexagonal boundary** -- Step definitions call driving ports (like `BookmarkService.save()`), not internal components (like `SQLiteRepository.insert()`). This keeps tests stable even if you swap storage backends.
2. **Business language** -- Feature files contain zero technical terms. "Carlos saves a bookmark" not "system persists entity."
3. **User journey** -- Every scenario represents a complete user action with observable value, not a unit of internal logic.

You do not need to memorize these mandates. They explain why the reviewer checks what it checks.

### Messages you can safely ignore

Lines containing `PreToolUse` or `DES_MARKERS` are internal quality gates. They are normal operation, not errors.

*Next: you will verify the test files Quinn created.*

---

## Step 5 of 7: Verify the Test Files (~2 minutes)

Check the acceptance test directory:

```bash
find tests/acceptance -type f | sort
```

You should see something like:

```
tests/acceptance/bookmark_cli/acceptance/milestone-1-search.feature
tests/acceptance/bookmark_cli/acceptance/milestone-2-tagging.feature
tests/acceptance/bookmark_cli/acceptance/steps/bookmark_steps.py
tests/acceptance/bookmark_cli/acceptance/steps/conftest.py
tests/acceptance/bookmark_cli/acceptance/walking-skeleton.feature
```

> **Your file names and count will differ.** What matters is the pattern: `.feature` files for scenarios, a `steps/` directory for step definitions, and a `conftest.py` for shared fixtures.

Check that the step definitions reference driving ports, not internal components:

```bash
head -20 tests/acceptance/bookmark_cli/acceptance/steps/bookmark_steps.py
```

You should see imports referencing your domain or port layer:

```python
from bookmark_cli.domain.services import BookmarkService
# or
from bookmark_cli.ports.bookmark_repository import BookmarkRepository
```

You should NOT see imports like `from bookmark_cli.adapters.sqlite_repository import SQLiteRepository`. If you do, Quinn violated the hexagonal boundary mandate -- but the peer review should have caught this.

Check the documentation Quinn produced:

```bash
ls docs/feature/bookmark-cli/distill/
```

You should see:

```
test-scenarios.md
walking-skeleton.md
acceptance-review.md
```

> **If the `docs/feature/` path does not exist**: Quinn may have placed documentation in `docs/distill/` or `docs/acceptance/` instead. Check those paths.

*Next: you will run the tests to confirm they fail for the right reason.*

---

## Step 6 of 7: Run the Tests (~1 minute)

The acceptance tests should fail -- there is no implementation yet. But they should fail because business logic is missing, not because of import errors or broken test infrastructure.

```bash
pytest tests/acceptance/ -v --no-header 2>&1 | head -30
```

You should see output like:

```
tests/acceptance/.../walking-skeleton.feature::Save a bookmark and find it by keyword search SKIPPED
tests/acceptance/.../milestone-1-search.feature::Search by tag returns matching bookmark SKIPPED
tests/acceptance/.../milestone-1-search.feature::Search with no results returns clear message SKIPPED
```

Most scenarios are marked `@skip` or `@pending` -- this is intentional. Quinn tags all scenarios except the walking skeleton for one-at-a-time implementation. When you reach `/nw-deliver` in Tutorial 8, the software crafter enables one test at a time: make it pass, commit, enable the next.

> **If you see import errors**: The step definitions may reference modules that do not exist yet. This is expected for a greenfield project -- the imports describe the architecture Quinn expects `/nw-deliver` to create. The key is that the `.feature` files parse correctly and scenarios are tagged.

> **If pytest cannot find the tests**: Make sure you have pytest-bdd installed. Run `pip install pytest-bdd` and try again.

**What just happened?** You confirmed the test infrastructure works. The tests are skipped (not erroring), which means the feature files are valid Gherkin syntax (the Given/When/Then language from your user stories), the step definitions are syntactically correct, and the one-at-a-time tagging strategy is in place. This is exactly the state `/nw-deliver` expects to receive.

*Next: commit everything and see the full picture.*

---

## Step 7 of 7: Commit and Review (~2 minutes)

Commit the acceptance test suite:

```bash
git add -A && git commit -m "test: acceptance tests from distill session"
```

You should see:

```
[main ...] test: acceptance tests from distill session
```

### What You Built

You started with requirements and architecture, and ended with an executable test suite:

1. **Walking skeleton** -- The simplest end-to-end scenario proving a user can accomplish their goal
2. **Milestone feature files** -- BDD scenarios covering happy paths, error paths, and edge cases across all user stories
3. **Step definitions** -- pytest-bdd steps wired to driving ports, enforcing hexagonal architecture boundaries
4. **One-at-a-time tagging** -- `@skip` tags on all scenarios except the walking skeleton, ready for incremental delivery

### What You Didn't Have to Do

- Write BDD scenarios from scratch
- Figure out which error paths to cover
- Wire step definitions to the right architectural layer
- Decide implementation order
- Ensure 40% error path coverage manually

### The Wave So Far

```
DISCOVER             DIVERGE              DISCUSS              DESIGN               DEVOPS               DISTILL
(/nw-discover)       (/nw-diverge)        (/nw-discuss)        (/nw-design)         (/nw-devops)         (/nw-distill)
────────────────     ────────────────     ────────────────     ────────────────     ────────────────     ────────────────
"Is the problem      "Which direction     "What should we      "How should we       "How do we           "What does done
 real?"               should we go?"       build?"              build it?"           deploy it?"          look like?"

Evidence-based       Design exploration   Journey + stories    Architecture +       CI/CD pipeline       Acceptance tests
validation           + recommendation     + acceptance         ADRs + diagrams      + infra +            + walking skeleton
                     (optional)           criteria                                  observability        + step definitions

Tutorial 4           Tutorial 5           Tutorial 6           Tutorial 7           Tutorial 10          This tutorial
```

Each wave feeds the next. The acceptance tests reference your user stories (the scenarios) and your architecture (the driving ports). Nothing is generated in a vacuum.

---

## Next Steps

- **[Tutorial 9: Delivering the Feature](../tutorial-deliver-feature/)** -- Take your acceptance tests into `/nw-deliver` to implement the bookmark CLI with architecture-guided TDD
- **Read a feature file aloud** -- If it sounds like a conversation about what the user does, it is well-written. If it sounds like a technical specification, it may be too implementation-focused.
- **Open the walking skeleton** -- Trace the scenario from Given to Then and check that it matches the emotional peak from your UX journey (Tutorial 6)

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Quinn does not start after `/nw-distill` | Make sure nWave is installed. Run `/nw-help` to verify. |
| Quinn skips the four decisions and generates immediately | Say `*create-acceptance-tests bookmark-cli` to explicitly start the interactive flow. |
| Peer review fails repeatedly | Say "let's simplify -- focus on the walking skeleton and 2 milestone features only." Fewer scenarios are easier to validate. |
| No `tests/acceptance/` directory after the session | Quinn writes test files after the four decisions and scenario design. If you ended the session early, run `/nw-distill bookmark-cli` again. |
| Import errors when running pytest | Expected for greenfield projects. The imports describe the architecture `/nw-deliver` will create. Feature files should still parse correctly. |
| `pytest-bdd` not found | Run `pip install pytest-bdd` to install the test framework. |
| Want to start fresh | Delete `tests/acceptance/` and `docs/feature/bookmark-cli/distill/` and run `/nw-distill` again. |

---

**Last Updated**: 2026-04-06
