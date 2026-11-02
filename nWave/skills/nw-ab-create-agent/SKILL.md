---
name: nw-ab-create-agent
description: "PROCEDURE — create a NEW agent via the 5-phase workflow (ANALYZE→DESIGN→CREATE→VALIDATE→REFINE). Trigger: build a new AI agent. Composes nw-ab-validate-spec."
user-invocable: false
---

# nw-ab-create-agent (PROCEDURE)

**Kind**: PROCEDURE | **One job**: create one new agent | **One trigger**: a new AI agent must be built.

## Deterministic step-sequence (run every time, in order)

Run these steps in order:

1. **ANALYZE** — Apply the resident `nw-agent-creation-workflow`, including its source-aware Skill addressing procedure. Identify single clear responsibility. Check overlap with existing agents (Glob `nWave/agents/`). Classify specialist | reviewer | orchestrator. Determine minimum tools. Gate: responsibility defined, no overlap, classification chosen.
2. **DESIGN** — Apply the resident `nw-design-patterns`. Select design pattern. Define role, goal, divergent principles. Plan skills extraction. Draft frontmatter. Gate: pattern selected, principles drafted, frontmatter ready.
3. **CREATE** — Apply the resident `nw-ab-agent-template` and `nw-ab-house-style`. Write agent `.md` from the template, caveman-curated. Inject the Reasoning Mandate verbatim. Extract skills if domain knowledge >50 lines. Gate: file written and identity metadata present.
4. **VALIDATE** — compose ▶ `nw-ab-validate-spec` (every `nw-ab-validation-checklist` item + anti-pattern scan). Gate: every checklist item passes, zero anti-patterns.
5. **REFINE** — Address failures. Add instructions only for observed failure modes. Re-validate. Gate: all items pass.

## Composition

- COMPOSES (KNOWLEDGE): `nw-agent-creation-workflow`, `nw-design-patterns`, `nw-ab-agent-template`, `nw-ab-house-style`.
- COMPOSES (PROCEDURE): `nw-ab-validate-spec` (phase 4).

## Success Criteria

- [ ] Agent invoked via the 5-phase sequence, no phase skipped
- [ ] `nw-ab-validate-spec` composed at phase 4 (not re-inlined)
- [ ] Under 400 lines, anchors + Reasoning Mandate present, before/after lines reported
