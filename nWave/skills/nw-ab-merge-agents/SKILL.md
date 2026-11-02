---
name: nw-ab-merge-agents
description: "PROCEDURE — merge agent B into agent A, relocating skills and cleaning up all references. Trigger: two agents must become one. Composes nw-ab-validate-spec."
user-invocable: false
---

# nw-ab-merge-agents (PROCEDURE)

**Kind**: PROCEDURE | **One job**: merge agent B into agent A | **One trigger**: two agents must be consolidated into one.

## Deterministic step-sequence (run every time, in order)

Run these steps in order:

1. **INVENTORY** — Read both agent definitions and all skills. List capabilities, principles, skills, commands from both. Identify overlaps + B's unique contributions. Gate: inventory table produced.
2. **MERGE DEFINITION** — Rewrite A to absorb B's unique capabilities. Consolidate principles (no duplicates), merge workflows, update examples. Add B's skill references to A's frontmatter. Stay under 400 lines. Gate: merged A written, under 400 lines.
3. **RELOCATE SKILLS** — Copy skill files from B's directory to A's. If B has a reviewer, copy its skills too. Update frontmatter skill references. Gate: all skills relocated, frontmatter updated.
4. **CLEAN UP** — Delete deprecated agent file `nWave/agents/nw-{agent-b}.md`, deprecated reviewer, deprecated skill directories, deprecated command task files. Gate: zero deprecated files remain.
5. **UPDATE REFERENCES** — Update `nWave/framework-catalog.yaml`, `nWave/README.md`, `nWave/templates/*.yaml`. Grep for remaining references to B's name. Gate: zero references remain (legacy/ exempt).
6. **VALIDATE** — compose ▶ `nw-ab-validate-spec` on merged A. Gate: every checklist item passes, zero anti-patterns.

## Composition

- COMPOSES (PROCEDURE): `nw-ab-validate-spec` (step 6).
- No domain knowledge skill — this is a pure relocation/reference-update procedure.

## Success Criteria

- [ ] Inventory table produced
- [ ] Merged A under 400 lines; skills relocated; zero deprecated files; zero dangling references
- [ ] `nw-ab-validate-spec` composed (not re-inlined)
