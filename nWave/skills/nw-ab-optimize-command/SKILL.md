---
name: nw-ab-optimize-command
description: "PROCEDURE — optimize a bloated command file to a lean declarative definition (forge.md pattern). Trigger: a command file over its size target with reducible content."
user-invocable: false
---

# nw-ab-optimize-command (PROCEDURE)

**Kind**: PROCEDURE | **One job**: optimize one command file | **One trigger**: a command file exceeds its size target (dispatchers 40-150L, orchestrators 100-300L) or carries reducible duplication.

## Deterministic step-sequence (run every time, in order)

Run these steps in order:

1. **CLASSIFY** — Apply `nw-command-design-patterns`, supplied by the selected command route's generated trigger under the canonical Skill addressing procedure. Classify dispatcher | orchestrator. Gate: classification chosen.
2. **MEASURE + FLAG** — Apply `nw-command-optimization-workflow` supplied through that same generated route, without a second load directive. `wc -l`; flag reducible content (the duplication triangle: command-to-command, command-to-agent, command-to-self). Gate: before-count + reducible-list recorded.
3. **EXTRACT** — Remove boilerplate, move domain knowledge to the owning agent/skill, delete dead/deprecated references. Gate: extractions listed.
4. **RESTRUCTURE** — Rewrite as a declarative dispatcher/orchestrator (forge.md 40-line gold standard for dispatchers). Gate: declarative structure, size within target.
5. **VALIDATE** — Confirm the command keeps its invocation contract + success criteria; numbered-task-list workflow, checkbox success criteria. Gate: structure confirmed.
6. **REPORT** — before/after line counts. Gate: both numbers reported.

## Composition

- COMPOSES (KNOWLEDGE): `nw-command-design-patterns`, `nw-command-optimization-workflow`.
- Note: this procedure restructures a command DEFINITION; it does not execute the command.

## Success Criteria

- [ ] Command classified, reducible content flagged
- [ ] Size within target (dispatcher 40-150L / orchestrator 100-300L)
- [ ] Before/after line counts reported; invocation contract preserved
