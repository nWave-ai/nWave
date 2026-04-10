---
name: nw-buddy-ssot-knowledge
description: Single Source of Truth detection — where truth lives in an nWave repo and how to avoid contradicting it.
---

# SSOT Knowledge for the Buddy Agent

Large projects accumulate multiple copies of "the same" information: a version in `pyproject.toml`, a version in a `VERSION` file, a version in the README, a version in a changelog. When these disagree, the buddy agent must know which one is authoritative. This skill is the SSOT map for nWave projects.

## Why it matters

Answering a user's question with a stale secondary copy is worse than saying "I don't know": it spreads wrong information with a confident tone. The buddy's job is to read the authoritative source every time, and to flag contradictions when the copies diverge.

## The SSOT map

Each concept below has one authoritative file. Read that file first. Treat everything else as a cache that may be stale.

### Versions

- **Authoritative**: `pyproject.toml` `[project] version = "..."` (or the equivalent field in the package manifest for non-Python projects).
- **Caches**: `VERSION` file, README badges, docs footer, release notes.
- **Rule**: quote `pyproject.toml`. If asked about a cache that disagrees, report the discrepancy.

### Planned work

- **Authoritative**: `BACKLOG.md` at the repo root.
- **Caches**: GitHub issues, conversation context, notes in other docs, stale TODO comments.
- **Rule**: work that isn't in `BACKLOG.md` is not planned. Don't invent items. If the user mentions something not on the backlog, point that out and suggest they add it.

### Architecture intent

- **Authoritative**: `docs/architecture/architecture-design.md` (or whichever file the project uses as the single architecture doc — usually linked from `CLAUDE.md` or `README.md`).
- **Caches**: individual feature specs in `docs/feature/` with wave subdirectories, ADRs in `docs/adrs/`, diagrams in `docs/`, comments in code.
- **Rule**: design *intent* lives in the architecture doc; design *decisions* live in ADRs; design *details* live in feature specs. If they disagree, the architecture doc wins for high-level questions; ADRs win for "why did we choose X".

### Runtime behavior

- **Authoritative**: the code.
- **Caches**: docs, specs, comments, commit messages.
- **Rule**: if a doc claims behavior X and the code does Y, the code is what users experience. Report the discrepancy as a finding.

### Configuration

- **Authoritative**: the config file the runtime actually loads (`pyproject.toml`, `.pre-commit-config.yaml`, `ci.yml`, whichever applies).
- **Caches**: docs describing the config, README examples.
- **Rule**: quote the real file, including its path.

### Agent / command definitions

- **Authoritative**: the YAML frontmatter of the agent or command file, and the framework catalog (`framework-catalog.yaml` or equivalent) if the project uses one.
- **Caches**: READMEs, marketing docs, generated reference pages.
- **Rule**: trust the frontmatter + catalog.

### Git state

- **Authoritative**: `git status`, `git log`, `git branch`.
- **Caches**: conversation memory, "what I was doing" notes.
- **Rule**: run git commands before answering state questions. Never guess.

## Conflict resolution hierarchy

When two sources disagree and it isn't obvious which wins, use this hierarchy from most to least authoritative:

1. The code itself (runtime behavior).
2. The config files that control the runtime.
3. The SSOT file declared by the project (`BACKLOG.md`, `architecture-design.md`, etc.).
4. ADRs (for "why" questions).
5. Feature specs.
6. Generated docs.
7. README.
8. Prose in commit messages.
9. Conversation context and memory.

Reporting a conflict is a valuable answer. "The README says X but the code does Y — you probably want to update the README" is more useful than picking one silently.

## How to recognize a stale secondary copy

Signals that a doc is out of date:

- It references APIs, commands, or files that no longer exist in the repo.
- It claims a version number older than `pyproject.toml`.
- Its "last updated" date (if present) is much older than recent commits to the code it describes.
- Its vocabulary matches an older phase of the project (old feature names, old architecture terms).
- It contradicts a more recent ADR.

When you spot one, mention it in the answer and suggest it be updated or deleted.

## Read-before-answer discipline

Before any concrete answer:

1. Identify which concept the question is about (version, backlog, architecture, behavior, config, state).
2. Look up the SSOT for that concept in the map above.
3. Read the authoritative file.
4. Form the answer from that file, with a citation.
5. If you also happen to see a contradicting cache, report it.

Don't answer from memory. The buddy agent's memory is not an SSOT; the repo is.

## Never invent, always cite

If you don't find the information, say so and suggest where the user might add it. Never fabricate a file path, a function name, a version number, or a backlog item. Fabrication destroys trust; "I couldn't find this" preserves it.

## A short example

User asks: "what version are we on and what's next?"

Good answer:

> We're on v2.17.5 (`pyproject.toml:3`). The top three items in `BACKLOG.md` are:
> 1. Finish the D-PLUGIN-00b delivery (`BACKLOG.md:12`)
> 2. Docker validation matrix refresh (`BACKLOG.md:27`)
> 3. CI matrix expansion (`BACKLOG.md:34`)
>
> Note: the README badge shows v2.17.3 — probably stale, consider updating.

Bad answer:

> I think we're on v2.17 something and you're working on the plugin feature.

The good answer is sourced, cited, and adds a finding. The bad answer is vibes.
