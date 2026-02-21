# Component Boundaries: Wizard Commands

**Feature**: wizard-commands
**Date**: 2026-02-21

## Component Map

```
nWave/tasks/nw/
  new.md        -- Conversational intake wizard (US-001, US-003)
  continue.md   -- Progress scanner and resume (US-002)
  ff.md         -- Fast-forward chainer (US-004)
```

## Boundary Definitions

### /nw:new (new.md)

**Owns**:
- Feature description intake and classification
- Project ID derivation (prefix stripping, stop word removal, kebab-case, 5-segment limit)
- Name conflict detection and resolution
- Wave recommendation based on user answers and artifact presence
- Single-wave dispatch after user confirmation

**Does not own**:
- Wave execution (delegated to target wave command)
- Artifact creation (each wave creates its own artifacts)
- Multi-project selection (that belongs to /nw:continue)

### /nw:continue (continue.md)

**Owns**:
- Project directory scanning (`docs/feature/` enumeration)
- Wave completion detection (artifact presence checking per wave detection rules)
- Multi-project listing and selection (ordered by last modification)
- Per-wave progress display (complete / in progress / not started)
- DELIVER step-level progress (reading execution-log.yaml and .develop-progress.json)
- Anomaly detection: empty files, skipped waves
- Single-wave dispatch after user confirmation

**Does not own**:
- Project ID derivation (users select from discovered projects, not create new ones)
- Feature classification (not needed for resume)
- Wave execution (delegated to target wave command)

### /nw:ff (ff.md)

**Owns**:
- Wave sequence planning (determining remaining waves)
- --from flag parsing and prerequisite validation
- Sequential multi-wave dispatch (chain execution)
- Inter-wave artifact verification (checking each wave's output before starting next)
- Failure handling (stop on error, suggest /nw:continue)
- One-time confirmation before chain execution

**Does not own**:
- Wave detection logic (reuses continue.md's approach inline)
- Project ID derivation (reuses new.md's approach inline when description provided)
- Individual wave execution (delegated to each wave command)

## Shared Behaviors (Inline, Not Extracted)

These behaviors appear in multiple task files. Since task files are independent markdown instructions (no code sharing mechanism), each file contains its own copy of the instructions.

| Behavior | Used By | Notes |
|----------|---------|-------|
| Wave detection rules | continue.md, ff.md | Same artifact-to-wave mapping table |
| Project ID derivation | new.md, ff.md | Same prefix/stop-word/kebab logic; also in deliver.md |
| Wave command dispatch | new.md, continue.md, ff.md | Same invocation pattern |

**Rationale for inline duplication**: Task files are read by the Claude instance at invocation time. There is no import/include mechanism for markdown task files. Each file must be self-contained. The wave detection rules and ID derivation logic are compact enough (< 30 lines each) that duplication is acceptable. The source of truth for detection rules is the requirements document; task files copy the table.

## Relationship to Existing Commands

```
                    +-----------+
                    | /nw:new   |----> /nw:discover
                    |           |----> /nw:discuss
                    |           |----> /nw:design
                    |           |----> /nw:devops
                    |           |----> /nw:distill
                    |           |----> /nw:deliver
                    +-----------+

                    +-------------+
                    | /nw:continue|----> any wave command (based on detection)
                    +-------------+

                    +-----------+
                    | /nw:ff    |----> DISCUSS -> DESIGN -> DEVOPS -> DISTILL -> DELIVER
                    |           |     (sequential chain, DISCOVER skipped by default)
                    +-----------+
```

All three wizard commands are **leaf dispatchers** -- they determine which wave to run and invoke it, but they never modify artifacts themselves. The wave commands remain the sole owners of artifact creation and modification.

## Interaction Boundaries

| Interaction | Allowed | Forbidden |
|-------------|---------|-----------|
| Wizard reads filesystem | Yes (scanning for artifacts) | Writing/creating artifacts |
| Wizard asks user questions | Yes (AskUserQuestion tool) | Proceeding without confirmation |
| Wizard dispatches wave command | Yes (invokes /nw:{wave}) | Executing wave logic directly |
| Wizard uses Task tool for subagents | No (wizard is main instance) | Creating new subagent types |
| Wizard modifies existing commands | No | Any changes to discover through deliver |

## File Ownership

| File | Owner | Consumers |
|------|-------|-----------|
| `nWave/tasks/nw/new.md` | wizard-commands feature | Claude Code task file loader |
| `nWave/tasks/nw/continue.md` | wizard-commands feature | Claude Code task file loader |
| `nWave/tasks/nw/ff.md` | wizard-commands feature | Claude Code task file loader |
| `docs/feature/*/` | Existing wave commands | Wizard commands (read-only) |
| `docs/discovery/` | /nw:discover | /nw:continue, /nw:ff (read-only) |
| `execution-log.yaml` | /nw:deliver (via DES) | /nw:continue (read-only) |
| `.develop-progress.json` | /nw:deliver | /nw:continue (read-only) |
