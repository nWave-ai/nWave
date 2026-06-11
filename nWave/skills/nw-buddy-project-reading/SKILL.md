---
name: nw-buddy-project-reading
description: How the nWave buddy agent reads a project to answer questions — detection, order of inspection, and citation discipline.
---

# Project Reading for the Buddy Agent

The buddy agent answers questions about a project by *reading it*, not by guessing. Every answer must be traceable to a specific file and line. This skill is the reading protocol.

## Goals

1. Understand the project's architecture, current state, and methodology enough to answer the user's question.
2. Cite every claim (`path:line`) so the user can verify.
3. Avoid reading more than necessary — tokens and time both cost.
4. Never invent file contents, function names, or architecture claims.

## Order of inspection (cheap first)

Read in this order. Stop as soon as you have enough context for the current question.

### 1. Project identity (always, <1s)

- `README.md` — what is this project, for whom.
- `CLAUDE.md` (project root) — how Claude-based tools should behave here.
- `pyproject.toml` / `package.json` / `Cargo.toml` / equivalent — language, dependencies, versions, scripts.
- `VERSION` or the version field in the package manifest.

These four files tell you the project's name, language, purpose, and roughly how big it is. Skip nothing here.

### 2. Planning and state

- `BACKLOG.md` — the single source of truth for planned work (in nWave projects).
- `CHANGELOG.md` — recent user-visible changes.
- `git status` — what's in flight right now.
- `git log --oneline -20` — recent direction of travel.

If the user's question is "what should I work on next" or "what did we just do", these four are usually the answer.

### 3. Architecture documentation

- `docs/architecture/architecture-design.md` (or similar SSOT file).
- `docs/adrs/` — Architecture Decision Records.
- `docs/feature/` — feature specs with wave subdirectories.

The architecture doc is authoritative for design intent. If a claim in the architecture doc contradicts the code, the code is what runs — but the mismatch is itself a finding worth reporting.

### 4. Source layout

- `ls` the top-level dirs.
- `ls src/` (or the project's source root).
- Read the main entry point (`main.py`, `index.ts`, `Main.fs`, etc.).

A project's directory layout tells you 80% of its architecture in a few seconds: `domain/`, `application/`, `adapters/`, `ports/`, `tests/` means hexagonal. `src/`, `views/`, `controllers/`, `models/` means MVC. `core/`, `api/`, `ui/` means layered.

### 5. Tests

- `tests/` or equivalent — top-level directories only, initially.
- `conftest.py` / test config — tells you how tests are organized and marked.
- A representative test file from each layer (unit, integration, acceptance, e2e).

Tests often document behavior more precisely than prose docs.

### 6. Specific files (on demand)

Once the question is clear, read the specific files it touches. Don't pre-load.

## Detection heuristics

Answer these as you read:

- **Is this a nWave project?** Clues: `nWave/` directory, `framework-catalog.yaml`, `BACKLOG.md` at root, agents/commands/skills layout, mentions of waves in docs.
- **Is this greenfield or brownfield?** Clues: git history length, number of commits, presence of legacy folders, CHANGELOG age.
- **What language(s)?** `pyproject.toml`, `package.json`, `.csproj`, `build.sbt`, etc.
- **What architecture style?** Directory names (see section 4 above).
- **What test strategy?** Marker definitions, CI config, presence of acceptance/e2e folders.
- **What's the current branch?** `git status` or `git branch --show-current`. Branch name often encodes the current focus.
- **Who owns what?** `CODEOWNERS` if present.

Record the answers silently; draw on them when answering.

## Wave progress detection

When reading a feature to answer "what's next?", check for these wave artifacts in order:

| Wave | Artifact Path | Existence Check |
|------|---------------|----|
| DIVERGE | `docs/feature/{id}/diverge/recommendation.md` | Branch point recommendation exists |
| DISCUSS | `docs/feature/{id}/discuss/user-stories.md` | User stories written |
| DESIGN | `docs/feature/{id}/design/wave-decisions.md` | Architecture decisions documented |
| DEVOPS | `docs/feature/{id}/devops/wave-decisions.md` | CI/CD and deployment decisions documented |
| DISTILL | `tests/{test-type-path}/{id}/acceptance/*.feature` | BDD test scenarios written (the .feature file is the SSOT) |
| DELIVER | `docs/feature/{id}/deliver/roadmap.json` | All implementation steps at COMMIT/PASS |

Stop at the first missing artifact — that's where the feature currently is. For features using the old flat model (no wave subdirectories), treat as pre-DIVERGE.

## Citation discipline

Every concrete claim in an answer must point to a source:

- "The TDD cycle has 5 phases (`src/des/data/workflows/tdd-deliver.yaml:12`)"
- "Hexagonal boundaries defined in `docs/architecture/architecture-design.md` section 3"
- "Current branch is `feature/foo` (from `git status`)"

If you're paraphrasing, still cite. If you're guessing, say "I don't see this in the files I've read" and stop — don't fabricate.

When a citation would be noise (trivial claims like "this is a Python project"), omit it. When a claim is load-bearing, always cite.

## What NOT to do

- **Don't read the whole repo.** It's expensive and usually unnecessary.
- **Don't read generated files.** `node_modules/`, `.venv/`, `build/`, `dist/`, `target/`, lock files (unless the question is about deps).
- **Don't read test output or logs as primary sources.** They're stale by the time you see them.
- **Don't invent file contents** when a grep returns nothing. Report "not found" and suggest where it might live.
- **Don't answer without reading.** If you can't ground the answer in the repo, say so.

## Escalation

If the user's question requires reading more than ~15 files, or requires running commands, or touches a part of the codebase you can't reach, say so explicitly. Offer a plan: "to answer this I would need to read X, Y, Z — proceed?"

## Example: "what is this project and where are we with it?"

A well-formed answer:

1. Read `README.md`, `pyproject.toml`, `CLAUDE.md` — get the elevator pitch and version.
2. Read `BACKLOG.md` — get the current priorities.
3. Run `git status` + `git log --oneline -10` — get the current branch and recent direction.
4. Synthesize: "This is `<name>` v`<version>`, a `<one-sentence purpose>` written in `<language>`. The current branch is `<branch>`. Recent commits focus on `<summary>`. The backlog's top items are `<top 3>`. (citations for each claim)"

Total reading: 4-5 files, under a minute. That's the standard to aim for.
