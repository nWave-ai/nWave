---
name: nw-ab-validate-spec
description: "PROCEDURE — validate an EXISTING agent spec against the nw-ab-validation-checklist. Trigger: checking a spec for compliance (also the shared composition target create/migrate/merge invoke). One job: run the checklist, report pass/fail."
user-invocable: false
---

# nw-ab-validate-spec (PROCEDURE)

**Kind**: PROCEDURE | **One job**: validate an agent spec | **One trigger**: an existing agent spec must be checked for compliance (standalone, or composed by create/migrate/merge after a write).

This is the SHARED composition target. `nw-ab-create-agent`, `nw-ab-migrate-monolith`, and `nw-ab-merge-agents` all invoke this skill after writing — never re-inline the checklist.

## Deterministic step-sequence (run every time, in order)

Run these steps in order:

1. **Checklist** — run every item defined in `nw-ab-validation-checklist`, in table order, against the spec. Gate: each defined item reported pass/fail with evidence (line, count or quote); no item is claimed beyond those the checklist defines.

2. **Anti-patterns** — run the anti-pattern scan (`nw-ab-anti-patterns`). Gate: zero anti-patterns.

## Composition

- COMPOSES (KNOWLEDGE): `nw-ab-validation-checklist` (the item definitions), `nw-ab-anti-patterns`, `nw-ab-critique-dimensions`, `nw-agent-testing`.
- Note: the validator script `scripts/validation/validate_framework_templates.py` checks frontmatter, identity and declared-skill references. Reviewer artifact ownership is a role obligation, not a ban on native messaging tools.

## Success Criteria

- [ ] Every checklist item run in order
- [ ] Anti-pattern scan run
- [ ] Pass/fail reported per item
