# ADR-001: Wizard Commands as Markdown Task Files

## Status

Accepted

## Context

The wizard commands (/nw:new, /nw:continue, /nw:ff) need a runtime mechanism. Options include Python scripts, new agent definitions, or markdown task files. The project has 18 existing commands, all implemented as markdown task files under `nWave/tasks/nw/`. The constraint is explicit: no new agents, no new Python code.

## Decision

Implement all three wizard commands as markdown task files (`new.md`, `continue.md`, `ff.md`) under `nWave/tasks/nw/`, following the existing frontmatter and body conventions.

## Alternatives Considered

- **Python CLI scripts**: Would allow unit testing of wave detection and ID derivation logic. Rejected because the explicit constraint forbids new Python code, and the logic is simple enough to express as prose instructions for the Claude instance.
- **New agent definitions**: Would allow the wizard to run as a specialized subagent with its own system prompt. Rejected because the constraint requires the wizard to run as the main Claude instance, and creating an agent would add unnecessary indirection.

## Consequences

- **Positive**: Zero configuration, consistent with all existing commands, no build/install step, discoverable via `/nw:` command listing.
- **Negative**: Wave detection rules and project ID derivation logic are duplicated across files (no include mechanism). Changes to detection rules require updating multiple files.
- **Mitigation**: The requirements document (`docs/requirements/requirements.md`) serves as the single source of truth for detection rules. Task files copy from it.
