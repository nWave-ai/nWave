---
name: nw-ab-migrate-monolith
description: "PROCEDURE — migrate one legacy monolithic agent to a lean core plus routed skills. Trigger: an existing agent has measured size, embedded-configuration, duplication, aggressive-language, or multi-responsibility debt. Composes agent validation and requested skill optimization."
user-invocable: false
---

# nw-ab-migrate-monolith (PROCEDURE)

**Kind**: PROCEDURE | **One job**: migrate one existing agent monolith | **One trigger**: a legacy agent has measured size, embedded-configuration, duplication, aggressive-language, or multi-responsibility debt.

## Deterministic workflow

Run these steps in order:

1. **Baseline** — Measure the agent's lines, words, bytes, responsibilities, monolith debt, and existing behavioral projections. Stop: baseline is red, the target is not an agent, or a textual pin cannot be preserved.
2. **Extract configuration** — Move semantic configuration into frontmatter while preserving `name`, `model`, `tools`, `maxTurns`, `skills`, and public behavior. Stop: a field cannot be represented without behavior change.
3. **Map** — Reuse existing skills first. Map each original rule to one owner: lean agent core, one existing skill, or one extracted skill. Define disjoint, exhaustive triggers for extracted skills. Stop: an owner overlaps, a trigger gaps/overlaps, or public fan-out is missing.
4. **Simplify** — Preserve the agent name, public contract, tool surface, model, and `maxTurns`; retain only routing and global invariants in the core. Remove duplication and route distinct-trigger knowledge/procedures. Safety by construction first (frontmatter tool surface, typed grammar); hooks last resort with a recorded reason (GDP-0). Prefer remove, relax, route, or construct over a new check. Stop: preservation would change behavior or require added ceremony.
5. **De-escalate language** — Replace aggressive language with direct calm language; retain `MUST` only for skill-loading instructions. Stop: a required textual pin cannot be preserved.
6. **Optimize referenced skills** — For each referenced skill selected for optimization, invoke `nw-ab-optimize-skill`. Continue agent migration when it returns `NOT_ELIGIBLE`. Stop: a preservation risk, or a worsened resident cost without an explicit decision.
7. **Validate once** — Batch the planned edits, run existing agent validation once through `nw-ab-validate-spec`, and execute the existing behavioral projections. Do not create validators or tests. Stop: validation or a projection is red.
8. **Handoff** — Report ownership map, trigger partition, before/after measurements, executed projections, independent-review-needed, and residual `INDETERMINATE`. Stop: any required fact remains unmeasured.

## Composition

| Kind | Skill | Use |
|---|---|---|
| PROCEDURE | `nw-ab-validate-spec` | Step 7, agent validation only |
| PROCEDURE | `nw-ab-optimize-skill` | Step 6, for a referenced skill selected for optimization |
| KNOWLEDGE | `nw-ab-house-style` | Steps 2, 4, and 5; preserve lean core and literal protections |

## Boundaries

- Input is one existing agent; skill optimization remains the composed procedure's job.
- `nw-ab-validate-spec` validates the agent result only.
- Existing behavioral projections are evidence, never permission to change behavior.
- No public command, agent, or artifact is created by migration.

## Success criteria

- [ ] Agent name, public contract, model, tools, and `maxTurns` preserved.
- [ ] Every original rule has exactly one owner; extracted triggers are disjoint and exhaustive.
- [ ] Referenced skills are optimized only through `nw-ab-optimize-skill` when eligible.
- [ ] Existing validation runs once after batched edits; existing behavioral projections remain green.
- [ ] Terminal handoff contains measurements, ownership, trigger partition, review need, and residual `INDETERMINATE`.
