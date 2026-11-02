---
name: nw-ab-optimize-skill
description: "PROCEDURE — optimize one requested existing skill. Measures multi-trigger, duplication, and resident-context debt before editing; preserves its name as the lean core and behavioral projections."
user-invocable: false
---

# nw-ab-optimize-skill (PROCEDURE)

**Kind**: PROCEDURE | **One job**: optimize one existing skill | **One trigger**: an existing skill is requested for optimization.

## Eligibility

1. **Measure debt** — Record source lines, words, bytes; classify every rule and firing condition; identify duplication and resident-context cost. Compute `static_resident`; compute `expected_runtime` only from evidenced trigger probabilities, otherwise `INDETERMINATE`; compute `worst_runtime`. Use “tokens” only for exact compatible token measurements, otherwise report `INDETERMINATE`. Stop: a small coherent single-trigger skill; return `NOT_ELIGIBLE` without edits.
2. **Protect behavior** — Inventory the skill's public name, global invariants, referenced callers, textual pins, public/private fan-out, and existing behavioral projections. Stop: baseline red, a pin cannot be preserved, or a public fan-out is missing.

## Deterministic workflow

Run these steps in order:

1. **Map ownership** — Assign every original rule exactly one owner: original lean core, existing reused skill, or one extracted skill. Reuse first. Stop: duplicate or unowned rule.
2. **Partition triggers** — State a concrete trigger for every extracted procedure or knowledge skill. The triggers together cover the original trigger-space, without overlap. Keep one-job/one-trigger skills intact. Stop: trigger gap or overlap.
3. **Construct first** — Apply this order: remove, relax, route, construct, then consider an existing check. When an LLM still authors formal bytes, templates, grammars, reviewers, and validators are checks, not construction; prefer a deterministic sole-writer constructor or compiler that accepts semantic input once. Do not add enforcement machinery (validator, hook, gate, test, or mandatory artifact) through this procedure; a deterministic constructor/compiler that replaces LLM formal-byte authoring is allowed.
4. **Recompose** — Preserve the original skill name as the lean core. Keep its routing, global invariants, and public contract there; extract only distinct-trigger procedures or knowledge. Wire every extracted skill from the core; no orphan or name change.
5. **Measure outcome** — Re-measure core lines, words, bytes, `static_resident`, `expected_runtime` when evidenced, and `worst_runtime`. Retain a step only with evidence that it improves speed, resident/expected context cost, or outcome quality without silently worsening another; otherwise remove or skip it. Claim improvement only for a measured reduction; otherwise label the result `STRUCTURAL_ONLY` and name no efficiency gain. Stop: resident cost worsens without an explicit decision.
6. **Verify once** — Batch edits, run the existing relevant validation once, and execute the existing behavioral projections once. Do not create new validation. Stop: behavior changes or an existing projection is red.
7. **Handoff** — Return compact evidence only: ownership map; trigger partition; before/after metrics; executed projections; `independent-review-needed`; residual `INDETERMINATE`. Do not create a mandatory report artifact.

## Invariants

- Original skill name, public contract, and behavioral projections are preserved.
- A small coherent skill is `NOT_ELIGIBLE`; line count alone never justifies extraction.
- Resident metrics name their scope. Static resident is always measured; expected runtime is `INDETERMINATE` without probability evidence.
- This procedure creates no ceremony. Construction changes the producer; a later formal-byte authoring step is not construction.
- Prefer deletion over new machinery. Structural-only benefit is never sold as token saving.

## Success criteria

- [ ] Eligibility evidence recorded, or `NOT_ELIGIBLE` returned with no edits.
- [ ] Ownership is one-to-one; triggers are disjoint and exhaustive.
- [ ] Original skill is a lean recomposing core; extracted skills have distinct triggers and no orphans.
- [ ] Before/after core and resident metrics are present; any gain is measured or labeled `STRUCTURAL_ONLY`.
- [ ] Existing validation and behavioral projections ran once after the batch; handoff names independent review need and residual `INDETERMINATE`.
