# nw-software-crafter

DELIVER wave - SLIM scope (implementation + refactor expert). Crafter implements production code to satisfy ATs authored by acceptance-designer (DISTILL). Does NOT author tests. In atdd_pure mode follows the 7-phase protocol (A_GREEN_ATS, B_COVERAGE_CLEANUP, E_BATCH_REFACTOR); in classic mode follows the 3-phase RED -> GREEN -> COMMIT cycle (ADR-025).

**Wave:** DELIVER
**Model:** inherit
**Max turns:** 0
**Tools:** Read, Write, Edit, Bash, Glob, Grep, Task

## Commands

- [`/nw-bugfix`](../commands/index.md)
- [`/nw-deliver`](../commands/index.md)
- [`/nw-design`](../commands/index.md)
- [`/nw-distill`](../commands/index.md)
- [`/nw-execute`](../commands/index.md)
- [`/nw-finalize`](../commands/index.md)
- [`/nw-mikado`](../commands/index.md)
- [`/nw-mutation-test`](../commands/index.md)
- [`/nw-refactor`](../commands/index.md)
- [`/nw-review`](../commands/index.md)
- [`/nw-roadmap`](../commands/index.md)
- [`/nw-spike`](../commands/index.md)

## Skills

- [nw-collaboration-and-handoffs](../../../nWave/skills/nw-collaboration-and-handoffs/SKILL.md) — Cross-agent collaboration protocols, workflow handoff patterns, and commit message formats for TDD/Mikado/refactoring workflows
- [nw-crafter-discipline-atdd-pure](../../../nWave/skills/nw-crafter-discipline-atdd-pure/SKILL.md) — Crafter discipline contract for the ATDD-pure 7-phase workflow — what the slim crafter does in Phase A (GREEN-the-ATs), Phase B (coverage-driven dead-code elimination), and Phase E (batch L1-L6 refactor), plus hard prohibitions and the Phase B common-cuts taxonomy
- [nw-hexagonal-testing](../../../nWave/skills/nw-hexagonal-testing/SKILL.md) — 5-layer agent output validation, I/O contract specification, vertical slice development, and test doubles policy with per-layer examples
- [nw-legacy-refactoring-ddd](../../../nWave/skills/nw-legacy-refactoring-ddd/SKILL.md) — DDD-guided legacy refactoring patterns -- strangler fig, bubble context, ACL migration, 14 tactical/strategic/infrastructure patterns, and incremental monolith-to-microservices methodology
- [nw-mikado-method](../../../nWave/skills/nw-mikado-method/SKILL.md) — Enhanced Mikado Method for complex architectural refactoring - systematic dependency discovery, tree-based planning, and bottom-up execution
- [nw-mutation-test](../../../nWave/skills/nw-mutation-test/SKILL.md) — Runs feature-scoped mutation testing to validate test suite quality. Use after implementation to verify tests catch real bugs (kill rate >= 80%).
- [nw-production-safety](../../../nWave/skills/nw-production-safety/SKILL.md) — Agent safety boundaries - input validation, output filtering, scope constraints, and document creation policy
- [nw-progressive-refactoring](../../../nWave/skills/nw-progressive-refactoring/SKILL.md) — Progressive L1-L6 refactoring hierarchy, 22 code smell taxonomy, atomic transformations, test code smells, and Fowler refactoring catalog
- [nw-quality-framework](../../../nWave/skills/nw-quality-framework/SKILL.md) — Quality gates - 11 commit readiness gates, build/test protocol, validation checkpoints, and quality metrics
- [nw-refactor](../../../nWave/skills/nw-refactor/SKILL.md) — Applies the Refactoring Priority Premise (RPP) levels L1-L6 for systematic code refactoring. Use when improving code quality through structured refactoring passes.
- [nw-sc-review-dimensions](../../../nWave/skills/nw-sc-review-dimensions/SKILL.md) — Reviewer critique dimensions for peer review - implementation bias detection, test quality validation, completeness checks, and priority validation
- [nw-tdd-methodology](../../../nWave/skills/nw-tdd-methodology/SKILL.md) — Deep knowledge for Outside-In TDD - double-loop architecture, ATDD integration, port-to-port testing, walking skeletons, and test doubles policy
