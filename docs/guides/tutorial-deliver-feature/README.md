# Tutorial: Delivering the Feature

**Time**: ~20 minutes (9 steps)
**Platform**: macOS or Linux (Windows: use WSL)
**Prerequisites**: Python 3.10+, Claude Code with nWave installed, [Tutorial 8](../tutorial-distill/) completed
**What this is**: A hands-on walkthrough of `/nw-deliver` on a real multi-component feature. You will watch the delivery pipeline implement your bookmark CLI against the acceptance tests from Tutorial 8, guided by the hexagonal architecture from Tutorial 7.

---

## What You'll Build

A fully implemented bookmark CLI -- domain logic, CLI adapter, and SQLite storage adapter -- all built through strict TDD against your acceptance tests.

**Before**: You have acceptance tests from Tutorial 8 (`.feature` files with pytest-bdd step definitions), architecture from Tutorial 7 (hexagonal design with component boundaries), and requirements from Tutorial 6. But you have zero implementation code. Your tests are tagged `@skip` and waiting.

**After**: Every acceptance test passes. The bookmark CLI saves, searches, and manages bookmarks through a clean hexagonal architecture. The domain layer was built first, then the adapters -- exactly as the architecture prescribed. Every line of code exists because a test demanded it.

**Why this matters**: Tutorial 1 showed `/nw-deliver` on a simple, single-component feature. This tutorial shows what happens when the pipeline has architecture to follow and acceptance tests to satisfy. The roadmap respects component boundaries. The crafter implements domain logic before adapters. The result is a codebase where architecture decisions are enforced by the delivery process, not just documented and hoped for.

---

## Step 1 of 9: Confirm Your Starting Point (~1 minute)

You should be in the `bookmark-cli` project from Tutorial 8, with acceptance tests committed.

Verify your acceptance tests exist:

```bash
find tests/acceptance -name "*.feature" | head -5
```

You should see something like:

```
tests/acceptance/bookmark_cli/acceptance/walking-skeleton.feature
tests/acceptance/bookmark_cli/acceptance/milestone-1-search.feature
tests/acceptance/bookmark_cli/acceptance/milestone-2-tagging.feature
```

Verify your architecture document exists:

```bash
ls docs/feature/bookmark-cli/design/architecture-design.md
```

You should see:

```
docs/feature/bookmark-cli/design/architecture-design.md
```

> **If either is missing**: Complete the prerequisite tutorials first. `/nw-deliver` reads both acceptance tests and architecture documents to build the roadmap. [Tutorial 7](../tutorial-design/) produces architecture; [Tutorial 8](../tutorial-distill/) produces acceptance tests.

*Next: you will launch the delivery and watch the solution architect plan the work.*

---

## Step 2 of 9: Launch the Delivery (~1 minute)

In Claude Code, type:

```
/nw-deliver "bookmark-cli"
```

> **AI output varies between runs.** Your delivery session will differ from the examples below. The agent generates a roadmap and code based on your specific acceptance tests and architecture. What matters is the structure (phases, order, quality gates), not the exact output.

The first thing you see is the solution architect reading your project:

```
● nw-solution-architect(Reading acceptance tests...)
● nw-solution-architect(Reading architecture documents...)
● nw-solution-architect(Creating roadmap...)
```

The architect takes 30-60 seconds. It reads your acceptance tests to know what "done" looks like, and your architecture documents to know how the pieces should fit together.

**What just happened?** The solution architect produced a roadmap -- an ordered plan of TDD steps. Unlike Tutorial 1 where the architect invented the structure from scratch, here it follows your hexagonal architecture. Domain first, then adapters. You will inspect this roadmap in the next step.

*Next: you will read the roadmap and see how architecture shapes the plan.*

---

## Step 3 of 9: Read the Architecture-Guided Roadmap (~2 minutes)

While the delivery runs (or after it completes), find the roadmap:

```bash
cat docs/feature/bookmark-cli/deliver/roadmap.json
```

You should see something like:

```yaml
project_id: bookmark-cli
methodology: Outside-In TDD

steps:
  01-01:
    title: "Bookmark entity and save use case"
    acceptance_criteria:
      - "Bookmark entity holds URL and tags"
      - "BookmarkService.save() persists a bookmark"
    files_to_modify:
      - src/bookmark_cli/domain/bookmark.py
      - src/bookmark_cli/domain/services.py

  01-02:
    title: "Search by keyword"
    acceptance_criteria:
      - "BookmarkService.search() returns matching bookmarks"
    files_to_modify:
      - src/bookmark_cli/domain/services.py

  02-01:
    title: "SQLite storage adapter"
    acceptance_criteria:
      - "SQLiteRepository implements BookmarkRepository port"
    files_to_modify:
      - src/bookmark_cli/adapters/sqlite_repository.py

  02-02:
    title: "CLI adapter"
    acceptance_criteria:
      - "CLI save command invokes BookmarkService"
      - "CLI search command displays results"
    files_to_modify:
      - src/bookmark_cli/adapters/cli.py
```

> **Your roadmap will differ.** The step titles, file paths, and acceptance criteria depend on your specific architecture and tests. The structure is what matters.

Notice the ordering -- this is where architecture guidance shows up:

1. **Phase 01 steps: domain layer first.** The bookmark entity and service live in `domain/`. No adapters, no infrastructure. Pure business logic with tests.
2. **Phase 02 steps: adapters second.** The SQLite repository and CLI adapter come after the domain is solid. They plug into the ports the domain defined.

This is the key difference from Tutorial 1. The architect did not invent an arbitrary order -- it followed your hexagonal architecture from Tutorial 6. Domain logic is testable without any adapter. Adapters depend on the domain, never the reverse.

*Next: you will watch the TDD execution phase build the domain layer.*

---

## Step 4 of 9: Watch the Domain Layer Build (~5 minutes)

The software crafter now executes each roadmap step through strict TDD. You will see phases scroll by:

```
● nw-software-crafter(Execute step 01-01: Bookmark entity and save use case)
  RED    — running tests... 1 failing
  GREEN  — writing implementation... tests passing
  COMMIT — feat(bookmark-cli): bookmark entity and save use case - step 01-01

● nw-software-crafter(Execute step 01-02: Search by keyword)
  RED    — running tests... 1 failing
  GREEN  — writing implementation... tests passing
  COMMIT — feat(bookmark-cli): search by keyword - step 01-02
```

This takes 3-5 minutes for the domain steps. Each step follows the cycle you learned in [Tutorial 3](../tutorial-delivery-pipeline/): RED (test fails), GREEN (minimum code to pass), COMMIT.

Two things to notice while it runs:

1. **Acceptance tests get enabled one at a time.** Remember the `@skip` tags from Tutorial 8? The crafter removes one tag, watches that test fail (RED), writes the code to make it pass (GREEN), then moves to the next. This is the "one-at-a-time" strategy Quinn set up.
2. **Domain steps touch only domain files.** Check the commit messages -- steps 01-01 and 01-02 modify files in `domain/`, not `adapters/`. The architecture boundary holds.

> **If the crafter seems stuck on a step for more than 3 minutes**: This is normal for complex steps. The crafter may be writing multiple unit tests before getting to GREEN. Wait for the commit message to confirm completion.

### Messages you can safely ignore

Lines containing `PreToolUse` or `DES_MARKERS` are internal quality gates. They are normal operation, not errors.

*Next: you will watch the adapter layer build on top of the domain.*

---

## Step 5 of 9: Watch the Adapters Build (~4 minutes)

After the domain is solid, the crafter moves to the adapter steps:

```
● nw-software-crafter(Execute step 02-01: SQLite storage adapter)
  RED    — running tests... 1 failing
  GREEN  — writing implementation... tests passing
  COMMIT — feat(bookmark-cli): SQLite storage adapter - step 02-01

● nw-software-crafter(Execute step 02-02: CLI adapter)
  RED    — running tests... 1 failing
  GREEN  — writing implementation... tests passing
  COMMIT — feat(bookmark-cli): CLI adapter - step 02-02
```

The adapter steps wire the domain to the outside world:

- **SQLite repository** implements the `BookmarkRepository` port defined by the domain. The domain never imports from `adapters/` -- the adapter imports from `domain/`.
- **CLI adapter** translates command-line arguments into calls to `BookmarkService`. It is the entry point users interact with.

After the last adapter step, your walking skeleton scenario (the end-to-end test from Tutorial 7) should pass -- a user can save a bookmark and find it again through the CLI.

*Next: the adversarial reviewer will inspect everything the crafter built.*

---

## Step 6 of 9: The Adversarial Review (~2 minutes)

After all steps execute, the reviewer agent inspects the implementation:

```
● nw-software-crafter-reviewer(Review)
  Checking test budget...
  Checking hexagonal compliance...
  Checking external validity...
  Review result: APPROVED (or CHANGES_REQUESTED)
```

The reviewer checks the same seven dimensions described in [Tutorial 3](../tutorial-delivery-pipeline/). The ones most relevant here:

| Dimension | What It Checks for Bookmark CLI |
|-----------|-------------------------------|
| Hexagonal compliance | Mocks only at port boundaries, not inside domain |
| External validity | CLI entry point is wired and callable |
| Test budget | Tests are proportional to behaviors (2x budget) |

If the reviewer requests changes, the crafter fixes them automatically. You will see another round of commits. Maximum two rounds -- if it still fails, the pipeline stops for your manual intervention.

> **If you see "CHANGES_REQUESTED"**: This is normal. The reviewer may ask for a missing edge case test or flag a mock placed in the wrong layer. The crafter handles it. Watch for the follow-up commit.

*Next: mutation testing validates that your tests catch real bugs.*

---

## Step 7 of 9: Mutation Testing (~2 minutes)

After review, the pipeline runs mutation testing:

```
● Running mutation testing...
  Mutating src/bookmark_cli/domain/services.py
  Mutating src/bookmark_cli/domain/bookmark.py
  Mutating src/bookmark_cli/adapters/sqlite_repository.py

  Kill rate: 87% (target: 80%)
  Status: PASSED
```

Mutation testing makes small changes to your production code (like changing `>` to `>=`) and checks whether your tests catch them. If they do, the mutant is "killed." The quality gate requires 80% or higher.

> **If kill rate is below 80%**: The pipeline asks the crafter to add tests for the surviving mutants. You will see additional test commits. This is automatic -- no action needed from you.

> **If you want to inspect surviving mutants**: After the pipeline completes, check `docs/feature/bookmark-cli/deliver/mutation-report.md` for details on which mutations survived and why.

*Next: you will verify the final result yourself.*

---

## Step 8 of 9: Verify the Result (~2 minutes)

The pipeline finishes with the finalize phase, archiving artifacts to `docs/evolution/`. Now verify everything yourself.

Run the acceptance tests:

```bash
pytest tests/acceptance/ -v --no-header 2>&1 | head -30
```

You should see all tests passing:

```
tests/acceptance/.../walking-skeleton.feature::Save a bookmark and find it by keyword search PASSED
tests/acceptance/.../milestone-1-search.feature::Search by tag returns matching bookmark PASSED
tests/acceptance/.../milestone-1-search.feature::Search with no results returns clear message PASSED
tests/acceptance/.../milestone-2-tagging.feature::Save bookmark with multiple tags PASSED
```

> **Your test names and count will differ.** What matters is that all tests pass -- no failures, no skips.

Check the git log to see the full delivery story:

```bash
git log --oneline | head -15
```

You should see commits ordered domain-first, then adapters:

```
abc1234 feat(bookmark-cli): CLI adapter - step 02-02
def5678 feat(bookmark-cli): SQLite storage adapter - step 02-01
9876543 feat(bookmark-cli): search by keyword - step 01-02
aaa1111 feat(bookmark-cli): bookmark entity and save use case - step 01-01
bbb2222 test: acceptance tests from distill session
```

> **If you see extra commits**: Refactoring passes and review fixes produce additional commits. That is expected.

Try the CLI yourself:

```bash
python -m bookmark_cli save "https://docs.python.org/3/" --tags "python,docs"
python -m bookmark_cli search "python"
```

You should see the saved bookmark in the search results.

> **If the module is not found**: The entry point name depends on what the crafter created. Check `git log --oneline` for the CLI adapter commit, then run `git show <commit-hash> --stat` to find the actual module path.

*Next: review what the full wave accomplished.*

---

## Step 9 of 9: The Complete Wave (~1 minute)

Check the evolution document:

```bash
ls docs/evolution/
```

You should see:

```
bookmark-cli.md
```

This is the permanent record of the delivery -- roadmap, quality gates passed, mutation testing results.

### What You Built

A fully tested bookmark CLI with clean architecture:

```
bookmark-cli/
  src/bookmark_cli/
    domain/
      bookmark.py          # Entity
      services.py          # Use cases (save, search)
      ports.py             # Repository interface
    adapters/
      cli.py               # CLI entry point
      sqlite_repository.py # Storage implementation
  tests/
    acceptance/            # BDD scenarios (all green)
    unit/                  # TDD unit tests
  docs/
    evolution/bookmark-cli.md  # Permanent delivery record
    feature/bookmark-cli/
      design/                  # Architecture docs
      discuss/                 # Requirements + journey
      distill/                 # Test design docs
      deliver/                 # Roadmap + execution log
```

> **Your file structure will differ.** The crafter organizes files based on your architecture document. The pattern is what matters: domain layer with no adapter dependencies, adapters that implement ports.

### The Full Wave

```
DISCOVER         DIVERGE          DISCUSS          DESIGN           DEVOPS           DISTILL          DELIVER
(/nw-discover)   (/nw-diverge)    (/nw-discuss)    (/nw-design)     (/nw-devops)     (/nw-distill)    (/nw-deliver)
──────────────   ──────────────   ──────────────   ──────────────   ──────────────   ──────────────   ──────────────
"Is the problem  "Which direction "What should     "How should we   "How do we       "What does done  "Build it with
 real?"           should we go?"   we build?"       build it?"       deploy it?"      look like?"      quality gates"

Evidence-based   Design explore   User stories +   Hexagonal arch   CI/CD pipeline   Acceptance       Domain-first
validation       + recommendation acceptance       + ADRs +         + infra +        tests + walking  TDD + review +
                 (optional)       criteria         diagrams         observability    skeleton         mutation test

Tutorial 4       Tutorial 5       Tutorial 6       Tutorial 7       Tutorial 10      Tutorial 8       This tutorial
```

Each wave constrained the next. Requirements shaped the architecture. Architecture shaped the tests. Tests shaped the implementation. Nothing was generated in a vacuum.

---

## Next Steps

- **[Tutorial 9: Production Readiness](../tutorial-devops/)** -- Take your delivered feature into `/nw-devops` for CI/CD and deployment strategy
- **Run it again on a different feature** -- Add a new feature to the bookmark CLI (e.g., "bookmark export to markdown") by running through tutorials 5-8 again
- **Read the evolution document** -- `docs/evolution/bookmark-cli.md` traces every decision. Compare it to your architecture document to see how closely the implementation followed the plan
- **[Tutorial 3: Understanding the Delivery Pipeline](../tutorial-delivery-pipeline/)** -- If you want to understand each phase in more detail

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/nw-deliver` does not start | Make sure nWave is installed. Run `/nw-help` to verify. |
| Architect cannot find acceptance tests | Ensure `.feature` files exist under `tests/acceptance/`. Run `find tests -name "*.feature"` to check. |
| Architect cannot find architecture docs | Ensure `docs/feature/bookmark-cli/design/architecture-design.md` exists. Complete [Tutorial 6](../tutorial-design/) if missing. |
| Roadmap has many more steps than expected | The architect breaks work into small, testable increments. More steps means more granularity, not more complexity. |
| Crafter stuck on RED for more than 5 minutes | The step may be too large for one TDD cycle. Let it continue -- the crafter often needs multiple attempts. If it truly hangs, press Ctrl+C and run `/nw-deliver` again. It resumes from the last committed step. |
| Review requests changes repeatedly (3+ rounds) | The pipeline stops after 2 rounds. Review the requested changes manually and fix them, then run `/nw-deliver` again. |
| Mutation kill rate below 80% after retries | Check `docs/feature/bookmark-cli/deliver/mutation-report.md`. Some surviving mutants are semantically equivalent (the change does not affect behavior). If the gap is small, this may be acceptable. |
| `pytest` cannot find tests after delivery | Make sure `pytest-bdd` is installed: `pip install pytest-bdd`. Also check that `conftest.py` exists in the test directory. |
| Import errors when running the CLI | The module path depends on what the crafter created. Check `setup.py` or `pyproject.toml` for the package name and entry points. |
| Want to start fresh | Run `git log --oneline` to find the commit before delivery started, then `git reset --hard <commit>` and run `/nw-deliver` again. |

---

**Last Updated**: 2026-02-17
