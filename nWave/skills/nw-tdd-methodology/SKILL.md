---
name: nw-tdd-methodology
description: Deep knowledge for Outside-In TDD - double-loop architecture, ATDD integration, port-to-port testing, walking skeletons, and test doubles policy
user-invocable: false
disable-model-invocation: true
---

# Outside-In TDD Methodology

Lean composing core. The deep knowledge is decomposed into seven one-job-one-trigger modules; five ship as skills under the `nw-tdd-methodology-*` prefix and the other two are summarised in this core. This core keeps the name (shared — the crafters, acceptance-designer, distill, and the test-optimizer all reference it) and routes to the module whose trigger fires. Load the module(s) for the job in play; do not re-inline their content here.

## Composition — module → trigger

| Module | Job | Trigger (when to load) |
|--------|-----|------------------------|
| _(summarised below)_ | the full TDD cycle | the invocation owns test authoring and runs RED→GREEN→COMMIT; production-only craft against an immutable oracle does not trigger this job |
| _(summarised below)_ | workflow shape | deciding the development-workflow shape — double-loop, Outside-In vs Inside-Out, lightweight ATDD, BDD, Bache workflow, unit-of-behavior framing |
| `nw-tdd-methodology-port-to-port` | test boundary | deciding what a test enters/asserts on — port-to-port discipline, the layer-specific Universe, refactoring-resilience, hexagonal per-layer strategy |
| `nw-tdd-methodology-test-doubles` | choose a double | choosing/building a test double — Meszaros taxonomy, classical-vs-mockist, mock-only-at-port-boundaries policy, doubles-must-validate-inputs contract |
| `nw-tdd-methodology-walking-skeleton` | build a WS | building/validating a walking skeleton — WS protocol, feature-level skeleton with incremental slice coverage, Mandate 5 adapter-strategy decision tree, Mandate 6 adapter real-I/O, adapter-integration RED-phase semantics |
| `nw-tdd-methodology-paradigm` | write a unit/acceptance test | writing a unit or acceptance test — property-based + state-delta mandate, applicability matrix, debt-payoff curve, delta-first trigger/bypass |
| `nw-tdd-methodology-pbt-deep` | write a PBT (deep) | writing a property-based test needing deep mechanics — A13/P6 stateful preconditions, four property-finding strategies, two shrinking mechanisms, targeted/search-based PBT |

## How to use

1. Identify the job in play (which trigger fires).
2. Read `~/.claude/skills/nw-tdd-methodology-{module}/SKILL.md` for that job unless its body is already preloaded or the job is summarised below.
3. For an invocation owning the full test-authoring cycle, apply the cycle summary + `-paradigm`; add other modules when their triggers apply. Managed production-only crafters implement against the immutable ATD-owned oracle and report oracle defects to its owner; the cycle summary grants no test-authoring or commit authority.

The seven modules together cover the full methodology. <!-- mode-ref-ok -->

## Jobs summarised in this core

- **Cycle** — 3-phase RED/GREEN/COMMIT canon. A new test must fail for the right reason before any production code is written; GREEN matches the public contract; no production code without a requiring test; after GREEN verify the new code is wired into the real driving port. Code examples follow the project's own language.
- **Workflow shape** — double-loop TDD: an outer acceptance test through the driving port stays red while inner unit-level cycles drive the implementation green. Choose Outside-In (acceptance first, collaborators discovered) or Inside-Out (domain first) by how much of the design is known; keep the unit of behavior an observable outcome, not a function or class.
