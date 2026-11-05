---
name: nw-refactor
description: "Applies the Refactoring Priority Premise (RPP) levels L1-L6 for systematic code refactoring. Use when improving code quality through structured refactoring passes."
user-invocable: true
argument-hint: '[target-class-or-module] - Optional: --level=[1-6] --method=[extract|inline|rename|move] --scope=[method|class|module]'
---

> **Code facts** — resolve structural facts about code through `code-fact` CLI (vendor-neutral, bundled adapters: AST then TextSearch). Degrade LOUD. Never ad-hoc grep. Example: `code-fact query.callers-of SYMBOL --root ROOT`.

# NW-REFACTOR: Systematic Code Refactoring

**Wave**: CROSS_WAVE
**Agent**: Crafty (nw-software-crafter)
**Command**: `*refactor`

## Overview

Applies the Refactoring Priority Premise (RPP) — 6-level hierarchy L1 Readability|L2 Complexity|L3 Responsibilities|L4 Abstractions|L5 Design Patterns|L6 SOLID++. For complex multi-class refactorings, agent applies Mikado Method internally.

**Paradigm.** Smell classes and levels follow the declared paradigm: `functional` uses nw-code-design-fp, `object_oriented` uses nw-code-design-oo; `procedural` has no catalog and applies the general classes: long function, duplication, unclear names, mixed decision and effect.

## Execution Model — Batch-Then-Verify (default, unconditional)

`/nw-refactor` runs **batch-then-verify** by default, regardless of test-suite speed:

1. **Cascade governs PLANNING ORDER only** — analyze and plan lower levels before higher (L2 transformations build on L1, L3 on L2, etc.). The cascade is a planning discipline, not a test-gating sequence.
2. **Edits applied as one coherent batch** — apply all planned L1-L6 transformations in a single editing session. NO interleaved test runs between levels.
3. **Run the test suite exactly ONCE**, at the very end, after all L1-L6 edits.
4. **If RED after the batch**: diagnose the breakage and fix the **production** code. Do NOT modify tests to make them pass. A test that must change to pass means either (a) the refactor altered observable behavior — revert that transformation — or (b) the test encoded an implementation detail rather than behavior — flag this to the user explicitly before touching it. Tests changing during a refactor is a signal, not a step.

**Inside a managed delivery** (a crafter changing one ready batch): the declared mutable production targets are analysis (reuse, impact, prefactoring, review focus), not a permission. The crafter may change any lane file its slice needs, never the oracle, its supports or the feature records, and refactors only what that needs. The "test suite" run once at the end is the host-supplied verification command. A needed test change is reported to its owner instead of edited. The scope, context-file and configuration defaults below apply only to a standalone `/nw-refactor` request.

**Crafter latitude.** Refactor L1 to L4 in your slice's code, except oracle and feature records, when easier; commit each alone and green first via `nwdes commit --role ROLE --type refactor`. Craft template: Refactor latitude.

**Legacy incremental variant** (opt-in only): the incremental L1→test→L2→test cycle, running the tests after each level instead of once at the end. It is NOT the default — use it only when explicitly requested.

## Context Files Required

- src/\* - Production codebase
- tests/\* - Test codebase

## Agent Invocation

@nw-software-crafter

Execute \*refactor for {target-class-or-module}.

**Context Files:**
- src/\*
- tests/\*

**Configuration:**
- level: 3 # Shorthand: --from=1 --to=3 (RPP range)
- from: 1 # Start RPP level (default: 1)
- to: 3 # End RPP level (default: same as level)
- scope: module # file/module/project
- method: extract # extract/inline/rename/move
- mikado_planning: false # Use Mikado Method for complex refactorings


## Success Criteria

- [ ] Code quality metrics improved (measured before/after)
- [ ] L1-L6 transformations planned in cascade order, applied as one batch
- [ ] If RED after batch: production code fixed (tests NOT modified to pass)
- [ ] Technical debt reduced measurably

## Next Wave

**Handoff To**: {invoking-agent-returns-to-workflow}
**Deliverables**: Refactored codebase with quality improvements

## Examples

### Example 1: Module-level readability refactor
```
/nw-refactor src/auth/token_manager.py --level=2 --scope=module
```
Crafty applies RPP L1-L2: rename ambiguous variables|extract magic numbers into constants|remove dead code (L1), then simplify conditionals|extract long methods (L2).

### Example 2: SOLID-level design refactor
```
/nw-refactor src/billing/ --level=6 --scope=module --mikado_planning=true
```
Crafty uses Mikado Method for multi-class refactoring, applies dependency inversion|interface segregation across billing module.

### Example 3: RPP range sweep (L1-L3)
```
/nw-refactor src/billing/domain/ --from=1 --to=3 --scope=module
```
Sweeps L1 readability|L2 complexity|L3 responsibility smells. Cascade governs planning order (analyze L1 before L2 before L3); edits applied as one batch; suite run once at the end.

### Example 4: Targeted single-level refactor
```
/nw-refactor src/billing/checkout.py --level=3 --scope=file
```
Targets L3 responsibility smells only. Assumes L1-L2 already clean.

## Expected Outputs

- Refactored production code with measurable quality improvements.
- End-of-batch test-suite result; if RED, diagnose and correct production code as specified above.
- Standalone refactoring documentation only when explicitly requested by the user.
