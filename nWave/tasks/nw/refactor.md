---
description: "Applies the Refactoring Priority Premise (RPP) levels L1-L6 for systematic code refactoring. Use when improving code quality through structured refactoring passes."
argument-hint: "[target-class-or-module] - Optional: --level=[1-6] --method=[extract|inline|rename|move] --scope=[method|class|module]"
---


# NW-REFACTOR: Systematic Code Refactoring

**Wave**: CROSS_WAVE
**Agent**: Crafty (nw-software-crafter)
**Command**: `*refactor`

## Overview

Applies the Refactoring Priority Premise (RPP) — 6-level hierarchy L1 Readability|L2 Complexity|L3 Responsibilities|L4 Abstractions|L5 Design Patterns|L6 SOLID++. For complex multi-class refactorings, agent applies Mikado Method internally.

## Execution Model — Batch-Then-Verify (default, unconditional)

`/nw-refactor` runs **batch-then-verify** by default, regardless of test-suite speed:

1. **Cascade governs PLANNING ORDER only** — analyze and plan lower levels before higher (L2 builds on L1, etc.). Not a test-gating sequence.
2. **Edits applied as one coherent batch** — all planned L1-L6 transformations in a single editing session, NO interleaved test runs.
3. **Run the test suite exactly ONCE**, at the very end, after all L1-L6 edits.
4. **If RED after the batch**: diagnose and fix the **production** code. Do NOT modify tests to make them pass. A test that must change means either (a) the refactor altered observable behavior — revert it — or (b) the test encoded an implementation detail — flag to the user before touching it. Tests changing during a refactor is a signal, not a step.

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
- [ ] Test suite run exactly once, at the end — GREEN
- [ ] If RED after batch: production code fixed (tests NOT modified to pass)
- [ ] Technical debt reduced measurably

## Next Wave

**Handoff To**: {invoking-agent-returns-to-workflow}
**Deliverables**: Refactored codebase with quality improvements

Worked examples: `~/.claude/skills/nw-refactor/SKILL.md` ## Examples (verbatim copy removed here, 2026-08-09 token-hot-path cut).

## Expected Outputs

```
src/*                              (refactored production code)
tests/*                            (refactored test code)
docs/refactoring/
  refactoring-log.md
  quality-metrics.md
```
