---
name: nw-test-optimization
description: Methodology for minimizing test count while maximizing behavioral coverage - lean core composing behavior-counting, anti-patterns, consolidation, paradigm-match, coverage-validation, scope-selection modules
user-invocable: false
disable-model-invocation: true
---

# Test Optimization Methodology (core)

## Mission

> Minimize tests, maximize value, reduce feedback time, maintain quality.
> (Ale, 2026-04-28: "Bisogna minimizzare i test, massimizzare il valore per ridurre il tempo di feedback, mantenendo la qualità.")

This skill operationalizes that mission for `/nw-optimize-tests` invocations and scheduled test audits. An optimization is judged by preserved observable behavior and coverage under the same command and environment, never by a universal test-count budget or a commit artifact.

Budgets, per-feature derogations, the default CI suite ceiling (300 s unless a repository ADR sets another) and the infrastructure suite follow `test:feedback-loop-budget` in `nw-cross-cutting-invariants`; an optimization never moves a test into the infrastructure suite to meet a budget.

This is a lean core. The methodology is split into 6 one-job modules: two ship as separate skills and are loaded by name; the other four are summarised below so the core stands alone. Apply the job whose trigger matches the situation.

## Module loading table (module → trigger)

| Module | Kind | Trigger — load when |
|--------|------|---------------------|
| `nw-test-optimization-consolidation` | KNOWLEDGE | "I have redundant tests — how do I collapse them without losing coverage" |
| `nw-test-optimization-paradigm-match` | KNOWLEDGE | "which test paradigm fits this test shape — before authoring/migrating" |

Path form: `~/.claude/skills/{module}/SKILL.md`.

## Jobs summarised in this core

| Job | Kind | Trigger — apply when | Rule |
|-----|------|----------------------|------|
| Behavior counting | KNOWLEDGE | "what counts as a behavior here / how many distinct behaviors does this scope expose" | A behavior is one observable outcome through a public port; count distinct observations, never tests, functions or lines. |
| Anti-pattern review | KNOWLEDGE | "is this test an anti-pattern — block at review" | Block language-guarantee, AST-shape and trivial-dataclass tests, mock-asserting-mock, parametrize-inflation, and never-collapsing migration nets. |
| Coverage validation | PROCEDURE | "before declaring an optimization done, prove no coverage was lost" | Run the same native selection before and after; every distinct observation and falsifier must survive. A lower test count is not lost coverage; a lost promised observation is. |
| Scope selection | KNOWLEDGE | "invoked without a specific scope — what do I attack first" | Rank by leverage: byte-identical file pairs, files with hundreds of collected tests, expensive per-test setup with read-only assertions, closed-world finite domains, language-guarantee or AST-shape files, aging migration paths. |

## Composition

- COMPOSES (KNOWLEDGE): `nw-test-optimization-consolidation`, `nw-test-optimization-paradigm-match`.

## What This Methodology Does NOT Cover

- Test infrastructure (fixtures, conftest, plugins) — that is platform-architect or troubleshooter scope
- Production code refactoring — `/nw-refactor` and the crafter scope
- New test authoring — crafter scope (DELIVER wave)
- Adapter integration tests — different rules apply (real I/O, no parametrize-collapse there); see `nw-tdd-methodology-walking-skeleton` (adapter real-I/O strategy)

## Cross-References

- `nw-tdd-methodology` — Mandate 1 (Observable Behavioral Outcomes), Mandate 5 (Parametrize Input Variations)
- `nw-mutation-test` — coverage-preserving validation via mutation kill rate (DEPRECATED/opt-in, FR-1 — not a default step; green ATs + EXAMINE are the truth)
- `nw-property-based-testing` — PBT paradigm, falsifier-gate for closed-world domains
- `nw-test-design-mandates` — universe-per-layer, state-delta + Universe matrix (§263-270)
- `nw-test-refactoring-catalog` — refactoring patterns for test code structure
- Overtesting investigation, 2026-04-28 — empirical evidence (~580 removable tests, 18% of unit suite, the gap is enforcement decay + loose behavior definition). Findings restated here in full; the write-up itself was an nWave-internal analysis note and is not part of any shipped or published tree, so do not look for a file.
- Empirical speedup commits 2026-05-18: `c2637f6c8` (parametrize-collapse 8.9×), `defc07f0d` (single-lifecycle 2.4×), `e97c94663`+`a90606d6b` (CVE+timeout+tiktoken)
