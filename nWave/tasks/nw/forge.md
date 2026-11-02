---
description: Creates new specialized agents using the 5-phase workflow (ANALYZE > DESIGN > CREATE > VALIDATE > REFINE). Use when building a new AI agent or validating an existing agent specification.
argument-hint: '[agent-name] - Optional: --type=[specialist|reviewer|orchestrator] --pattern=[react|reflection|router]'
---

# NW-FORGE: Agent Builder Router

**Wave**: CROSS_WAVE | **Agent**: Zeus (`nw-agent-builder`)

## Overview

Routes the existing `forge` surface to one owning procedure. The procedure creates and tracks its own task list.

## Routes

| Request condition | Internal procedure | Result |
|---|---|---|
| Create a new agent | `nw-ab-create-agent` | New agent and only needed skills |
| Validate only an existing agent | `nw-ab-validate-spec` | Per-item checklist verdict |
| Migrate an existing agent monolith | `nw-ab-migrate-monolith` | Lean agent core plus routed skills |
| Optimize one existing skill | `nw-ab-optimize-skill` | Measured optimization result or `NOT_ELIGIBLE` |

## Agent invocation

@nw-agent-builder

1. **Classify** — Select exactly one route from the table. Stop: request intent or target is ambiguous.
2. **Execute** — Load and run the selected `nw-ab-*` procedure. Preserve established public command and agent names. Stop: the target is not eligible for that procedure.
3. **Handoff** — Return the procedure's terminal evidence. Stop: it reports unresolved preservation or behavior risk.

## Contract

- `forge` remains the public command; this task owns only routing.
- Existing behavioral projections are immutable. Do not create a command, validator, grammar, compiler, hook, or gate for this change.
- Safety by construction first; hooks last resort with a recorded reason (GDP-0).
- Creation follows the five-phase `nw-ab-create-agent` workflow; validation runs `nw-ab-validate-spec` over the `nw-ab-validation-checklist` items.
- Skill optimization is internal routing, not a new public command.

## Success Criteria

- [ ] Exactly one route selected.
- [ ] Established command and agent names preserved.
- [ ] The selected procedure returns its terminal evidence.
