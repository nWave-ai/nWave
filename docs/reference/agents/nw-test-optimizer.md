# nw-test-optimizer

Use to minimize test count while preserving coverage. Invoke after a feature lands, when a suite feels slow or noisy, on a scheduled audit, or whenever the maintainer suspects overtesting. Detects byte-identical pairs, parametrize-inflation, language-guarantee tests, AST-shape tests, and migration-collapse opportunities. Never modifies production code.

**Wave:** Other
**Model:** sonnet
**Max turns:** 40
**Tools:** Read, Edit, Write, Bash, Glob, Grep, Task

## Commands

- [`/nw-optimize-tests`](../commands/index.md)

## Skills

- [nw-tdd-methodology](../skills/nw-tdd-methodology.md) — Deep knowledge for Outside-In TDD - double-loop architecture, ATDD integration, port-to-port testing, walking skeletons, and test doubles policy
- [nw-test-optimization](../skills/nw-test-optimization.md) — Methodology for minimizing test count while maximizing behavioral coverage - behavior definition, anti-pattern catalog, consolidation patterns, stopping criterion, coverage-preserving validation
