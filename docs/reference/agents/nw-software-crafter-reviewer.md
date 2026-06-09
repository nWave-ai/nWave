# nw-software-crafter-reviewer

Use for review and critique tasks. Classic mode → code-quality + TDD-discipline review primary. ATDD-pure mode (workflow_mode=atdd_pure) → AT-density-completeness audit PRIMARY at Phase C_REVIEWER_AUDIT and Phase F_FINAL_REVIEW per ADR-027; code review secondary. Runs on Haiku for cost efficiency.

**Wave:** DELIVER
**Model:** haiku
**Max turns:** 0
**Tools:** Read, Glob, Grep, Task

## Commands

- [`/nw-deliver`](../commands/index.md)
- [`/nw-review`](../commands/index.md)

## Skills

- [nw-at-completeness-check](../../../nWave/skills/nw-at-completeness-check/SKILL.md) — Canonical AT completeness gate — research-anchored 7-category taxonomy (C1-C7) + 15-item mechanical checklist. Paradigm-neutral. Drives acceptance-designer reviewer verdict deterministically.
- [nw-sc-review-dimensions](../../../nWave/skills/nw-sc-review-dimensions/SKILL.md) — Reviewer critique dimensions for peer review - implementation bias detection, test quality validation, completeness checks, and priority validation
- [nw-tdd-methodology](../../../nWave/skills/nw-tdd-methodology/SKILL.md) — Deep knowledge for Outside-In TDD - double-loop architecture, ATDD integration, port-to-port testing, walking skeletons, and test doubles policy
- [nw-tdd-review-enforcement](../../../nWave/skills/nw-tdd-review-enforcement/SKILL.md) — Test design mandate enforcement, test budget validation, TDD phase validation (3-phase canon per ADR-025), and external validity checks for the software crafter reviewer
