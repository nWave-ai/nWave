---
name: nw-forge
description: "Backward-compatible router for creating agents, validating existing agents, migrating existing agent monoliths, or optimizing one existing skill."
user-invocable: true
argument-hint: '[target] - New agent, existing agent, or existing SKILL.md; optional type/pattern hints'
---

# NW-FORGE: Agent Builder Router

**Wave**: CROSS_WAVE | **Agent**: Zeus (`nw-agent-builder`)

## Routes

| Request condition | Internal procedure | Output |
|---|---|---|
| Create a new agent | `nw-ab-create-agent` | New agent and only needed skills |
| Validate only an existing agent | `nw-ab-validate-spec` | Per-item checklist verdict |
| Migrate an existing agent monolith | `nw-ab-migrate-monolith` | Lean agent core plus routed skills |
| Optimize one existing skill | `nw-ab-optimize-skill` | Measured optimization result or `NOT_ELIGIBLE` |

## Routing workflow

1. **Classify** — Match the request to exactly one route above. Stop: ambiguous request; request the missing target or intent.
2. **Delegate** — Load and run the selected internal procedure. Preserve public command and agent names. Stop: the target is not eligible for the selected procedure.
3. **Handoff** — Return that procedure's terminal evidence without re-stating its workflow. Stop: the procedure reports an unresolved preservation or behavior risk.

## Contract

- `forge` remains the public command. This file owns routing only; procedure details remain in the selected `nw-ab-*` skill.
- Existing behavioral projections are immutable. Do not create a command, validator, grammar, compiler, hook, or gate for a route.
- Safety by construction first; hooks last resort with a recorded reason (GDP-0).
- Use `nw-ab-create-agent` for creation, `nw-ab-validate-spec` for validation, `nw-ab-migrate-monolith` for agent migration, and `nw-ab-optimize-skill` for skill optimization.
- The validation route uses `nw-ab-validation-checklist`; do not restate its items or count here.

## Existing surfaces

- Route by the target and request condition, not a mandatory operation flag.
- `*forge`, `*validate`, and `*migrate` retain their existing public meanings.
- Internal procedure names do not create a public command.
- The selected procedure owns detailed output and verification.
- A rejected route returns its own compact reason.
