# Requirements: Wizard Commands (/nw:new, /nw:continue, and /nw:ff)

**Epic**: wizard-commands
**Date**: 2026-02-21
**Status**: Draft

## Problem Statement

Developers using nWave face two recurring friction points:

1. **Starting**: nWave has 18 commands across 6 waves. A developer with a feature idea must understand the wave pipeline to pick the right entry point. New users default to guessing (often `/nw:discuss`) when they might need `/nw:discover` or could skip to `/nw:design`. This wastes an entire agent conversation when they pick wrong.

2. **Resuming**: After stepping away for hours or days, developers lose context on which wave they completed last. They manually inspect `docs/feature/{id}/` directories, cross-reference artifact names against wave expectations, and sometimes re-run completed waves because they cannot tell what is done. The DELIVER wave has built-in resume via `.develop-progress.json`, but no equivalent exists for the outer pipeline.

Both problems stem from the same root cause: **the user must hold the wave pipeline model in their head**. The wizard commands externalize that model.

## Scope

### In Scope
- `/nw:new` command: conversational wizard that asks what the user wants to build and launches the right wave
- `/nw:continue` command: artifact scanner that detects current wave progress and resumes step-by-step
- `/nw:ff` command: fast-forward that chains remaining waves end-to-end without stopping for review
- Project ID derivation from natural language descriptions
- Wave detection logic based on artifact file presence
- Multi-project selection when multiple features are in progress
- Error handling: vague descriptions, name conflicts, corrupted artifacts, skipped waves

### Out of Scope
- Changes to existing wave commands (discover, discuss, design, devops, distill, deliver)
- New agent definitions (wizard runs as main Claude instance, not a subagent)
- Modifications to artifact formats or directory structures
- GUI or TUI rendering (interaction is conversational text in Claude Code)

## Functional Requirements

### FR-01: Feature Description Intake
The `/nw:new` command shall accept a natural language feature description from the user and classify it into a feature type (user-facing, backend, infrastructure, cross-cutting).

### FR-02: Project State Detection
Both commands shall scan the filesystem under `docs/feature/` to detect existing project directories and determine which wave artifacts are present.

### FR-03: Wave Recommendation
The `/nw:new` command shall recommend a starting wave based on:
- Artifact presence (greenfield vs. brownfield)
- User-stated requirements readiness
- Feature type classification

### FR-04: Wave Progress Display
The `/nw:continue` command shall display a per-wave completion status (complete, in progress, not started) based on artifact presence rules defined in the journey schema.

### FR-05: Command Dispatch
Both commands shall dispatch to the appropriate `/nw:{wave}` command with the correct project ID and configuration parameters after user confirmation.

### FR-06: Project ID Derivation
The `/nw:new` command shall derive a kebab-case project ID from the feature description, show it to the user for confirmation, and allow overrides.

### FR-07: Multi-Project Selection
When `/nw:continue` detects multiple projects, it shall list them ordered by last modification timestamp and prompt the user to select one.

### FR-08: DELIVER Resume Integration
When `/nw:continue` detects a DELIVER wave in progress, it shall read `execution-log.yaml` and `.develop-progress.json` to show step-level progress and pass resume context to the deliver command.

### FR-10: Fast-Forward Execution
The `/nw:ff` command shall chain remaining waves end-to-end after a single user confirmation. It reuses wave detection from `/nw:continue` to determine the starting point, then dispatches each subsequent wave automatically, passing artifacts between waves.

### FR-11: Fast-Forward Failure Handling
If a wave fails during fast-forward, execution shall stop immediately, display the error, and suggest `/nw:continue` to resume after fixing the issue.

### FR-12: Fast-Forward Wave Selection
The `/nw:ff` command shall support an optional `--from={wave}` flag to start from a specific wave, validating that prerequisite artifacts exist. DISCOVER is skipped by default.

### FR-09: Error Handling
- Vague descriptions: ask follow-up questions before proceeding
- Name conflicts: offer continue, rename, or archive options
- No projects found: suggest `/nw:new`
- Corrupted artifacts: flag and recommend re-running the affected wave
- Skipped waves: warn and offer gap-fill or continue options

## Non-Functional Requirements

### NFR-01: Conversational Interaction
Both commands run as the main Claude instance (no subagent delegation for the wizard itself). The interaction is conversational text, not structured menus.

### NFR-02: Convention Compliance
Both command files must follow existing nWave task file conventions: YAML frontmatter with `description` and `argument-hint`, markdown body with Overview, Agent Invocation, Success Criteria, Examples, and Expected Outputs sections.

### NFR-03: Zero Configuration
The user should not need to configure anything before using either command. All detection is based on filesystem state.

### NFR-04: Emotional Coherence
The wizard interaction should progress from uncertainty/disorientation to confidence/relief. No step should make the user feel like they chose wrong or wasted effort.

## Wave Detection Rules

The following artifact-to-wave mapping is the single source of truth for both commands:

| Wave | Required Artifacts for "Complete" Status |
|------|----------------------------------------|
| DISCOVER | `docs/discovery/problem-validation.md` AND `docs/discovery/lean-canvas.md` |
| DISCUSS | `docs/feature/{id}/discuss/requirements.md` AND `docs/feature/{id}/discuss/user-stories.md` |
| DESIGN | `docs/feature/{id}/design/architecture-design.md` |
| DEVOP | `docs/feature/{id}/deliver/platform-architecture.md` |
| DISTILL | `docs/feature/{id}/distill/test-scenarios.md` |
| DELIVER | `docs/feature/{id}/execution-log.yaml` with all roadmap steps at COMMIT/PASS |

"In progress" is detected when a wave's directory exists but required artifacts are missing or incomplete.

## Recommendation Logic (/nw:new)

| Condition | Recommended Wave | Rationale |
|-----------|-----------------|-----------|
| No prior artifacts + unclear problem space | DISCOVER | Validate the problem first |
| No prior artifacts + clear requirements in user's head | DISCUSS | Formalize requirements |
| DISCUSS artifacts exist + no DESIGN | DESIGN | Requirements ready, design next |
| DESIGN artifacts exist + no DEVOP | DEVOP | Architecture ready, platform next |
| DEVOP artifacts exist + no DISTILL | DISTILL | Platform ready, acceptance tests next |
| All prior waves complete | DELIVER | Ready for implementation |

## Constraints

- All three commands produce task files under `nWave/tasks/nw/` (new.md, continue.md, ff.md)
- No new agent definitions required
- No modifications to existing wave commands or artifact formats
- Must be compatible with the existing project ID derivation logic in deliver.md

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Existing wave commands (discover through deliver) | Stable | Commands must accept project ID as argument |
| docs/feature/ directory convention | Stable | Standard artifact layout across all waves |
| .develop-progress.json format | Stable | DELIVER wave resume state |
| execution-log.yaml format | Stable | DELIVER wave execution state |
| Task file frontmatter format | Stable | description + argument-hint YAML |
