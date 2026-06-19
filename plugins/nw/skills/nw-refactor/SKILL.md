---
name: nw-refactor
description: "Applies the Refactoring Priority Premise (RPP) levels L1-L6 for systematic code refactoring. Use when improving code quality through structured refactoring passes."
user-invocable: true
argument-hint: '[target-class-or-module] - Optional: --level=[1-6] --method=[extract|inline|rename|move] --scope=[method|class|module]'
---

# NW-REFACTOR: Systematic Code Refactoring

**Wave**: CROSS_WAVE
**Agent**: Crafty (nw-software-crafter)
**Command**: `*refactor`

## Overview

Applies the Refactoring Priority Premise (RPP) — 6-level hierarchy L1 Readability|L2 Complexity|L3 Responsibilities|L4 Abstractions|L5 Design Patterns|L6 SOLID++. For complex multi-class refactorings, agent applies Mikado Method internally.

## Execution Model — Batch-Then-Verify (default, unconditional)

`/nw-refactor` runs **batch-then-verify** by default, regardless of test-suite speed:

1. **Cascade governs PLANNING ORDER only** — analyze and plan lower levels before higher (L2 transformations build on L1, L3 on L2, etc.). The cascade is a planning discipline, not a test-gating sequence.
2. **Edits applied as one coherent batch** — apply all planned L1-L6 transformations in a single editing session. NO interleaved test runs between levels.
3. **Run the test suite exactly ONCE**, at the very end, after all L1-L6 edits.
4. **If RED after the batch**: diagnose the breakage and fix the **production** code. Do NOT modify tests to make them pass. A test that must change to pass means either (a) the refactor altered observable behavior — revert that transformation — or (b) the test encoded an implementation detail rather than behavior — flag this to the user explicitly before touching it. Tests changing during a refactor is a signal, not a step.

**Legacy incremental variant** (opt-in only): the `nw-progressive-refactoring` skill documents the incremental L1→test→L2→test cycle. It is NOT the default — use it only when explicitly requested. Anchor: `feedback_refactor_batch_when_test_suite_slow_2026_05_19` (the prior "only batch when suite slow" conditional is removed — batch is now unconditional).

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

## Progress Tracking

The invoked agent MUST create a task list from its workflow phases at the start of execution using TaskCreate. Each phase becomes a task with the gate condition as completion criterion. Mark tasks in_progress when starting each phase and completed when the gate passes. This gives the user real-time visibility into progress.

## Success Criteria

- [ ] Code quality metrics improved (measured before/after)
- [ ] L1-L6 transformations planned in cascade order, applied as one batch
- [ ] Test suite run exactly once, at the end — GREEN
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
/nw-refactor src/des/domain/ --from=1 --to=3 --scope=module
```
Sweeps L1 readability|L2 complexity|L3 responsibility smells. Cascade governs planning order (analyze L1 before L2 before L3); edits applied as one batch; suite run once at the end.

### Example 4: Targeted single-level refactor
```
/nw-refactor src/des/cli/verify.py --level=3 --scope=file
```
Targets L3 responsibility smells only (Large Class, Feature Envy, Shotgun Surgery). Assumes L1-L2 already clean.

## Expected Outputs

```
src/*                              (refactored production code)
tests/*                            (refactored test code)
docs/refactoring/
  refactoring-log.md
  quality-metrics.md
```
