---
name: nw-refactor
description: Load after green to refactor changed code in small behaviour-preserving commits (RPP L1-L6) and apply the structure rules per unit.
user-invocable: true
argument-hint: '[target-class-or-module] - Optional: --level=[1-6] --method=[extract|inline|rename|move] --scope=[method|class|module]'
---

# Post-green refactor

## Preconditions
1. Start only when the required check is green on the current commit. Refactor only the code your slice changed; never the oracle, its supports or feature records.
2. Declared paradigm picks the smell catalogue: functional, object-oriented; procedural uses long function, duplication, unclear names, mixed decision and effect.

## Procedure
3. Work smallest level first: L1 readability (rename, constants, dead code), L2 complexity (extract, simplify conditionals), L3 responsibilities, L4 abstractions, L5 patterns, L6 SOLID. Start a level only when lower levels are clean in the changed code.
4. Inside a managed delivery slice, the default is one behaviour-preserving move per commit, and the same check you ran on the parent is green on each commit. A standalone `/nw-refactor` request follows the command's own batch-then-verify execution model (plan L1-L6, apply as one batch, run the suite once; nWave/tasks/nw/refactor.md).
5. Edit no test and no expected value; declared laws and expected values stay unchanged. A test that must change means the move altered behaviour: revert the move. A test that encodes an implementation detail: report it to its owner, do not edit it.
6. If red after a move, fix or revert the production code only.
7. Multi-class moves: list the dependency steps, do the leaf first, commit each green.
8. A structural move made before new behaviour leaves oracle content untouched. Probe once: re-inject a break at the moved code, confirm a test fails, then restore.

## Per changed unit apply, then record what was applied or why none was needed
9. Object-oriented domain and application classes (not adapters, DTOs, read models, config): apply the Object Calisthenics rules by their rule numbers in nw-code-design-oo, strictly; a deliberate break is recorded with its smell, benefit and cost. Functional and procedural code skip this rule and use the paradigm smell classes.
10. Apply the nw-code-design-oo rules on data-owner decisions and on sequence-only grouping to each changed unit.
11. Each agreed literal (limit, label, name) lives in one place that every use reads.
12. Judge in order: tests demonstrate behaviour; no semantic duplication; clarity; fewest elements. Remove a type only if the first three still hold; keep an element whose removal raises the whole-path burden.
13. Do not add a framework or abstraction for a single caller.

## Self-check before recording the step
1. Each commit one move, green on same check as parent.
2. No test, law or expected value edited.
3. Per unit: which rules applied, or why none was needed.
4. Closing line lists checks run with output and any not run.
