---
description: "Applies the Refactoring Priority Premise (RPP) levels L1-L6 for systematic code refactoring. Use when improving code quality through structured refactoring passes."
argument-hint: "[target-class-or-module] - Optional: --level=[1-6] --method=[extract|inline|rename|move] --scope=[method|class|module]"
---

# NW-REFACTOR: Systematic Code Refactoring

**Wave**: CROSS_WAVE
**Agent**: Crafty (nw-software-crafter)
**Command**: `*refactor`

## Overview

Applies the Refactoring Priority Premise (RPP) — a cascading 6-level hierarchy where lower levels must be completed before higher. The six levels: L1 Readability, L2 Complexity, L3 Responsibilities, L4 Abstractions, L5 Design Patterns, L6 SOLID++. Each level builds on the previous. For complex refactorings spanning multiple classes, the agent applies Mikado Method planning internally.

## Context Files Required

- src/\* - Production codebase to refactor
- tests/\* - Test codebase to refactor

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
- [ ] All tests passing after refactoring
- [ ] Refactoring levels applied in sequence (L1 before L2, etc.)
- [ ] Technical debt reduced measurably

## Next Wave

**Handoff To**: {invoking-agent-returns-to-workflow}
**Deliverables**: Refactored codebase with quality improvements

## Examples

### Example 1: Module-level readability refactor
```
/nw:refactor src/auth/token_manager.py --level=2 --scope=module
```
Crafty applies RPP L1-L2: rename ambiguous variables, extract magic numbers into named constants, remove dead code (L1), then simplify conditionals and extract long methods (L2).

### Example 2: SOLID-level design refactor
```
/nw:refactor src/billing/ --level=6 --scope=module --mikado_planning=true
```
Crafty uses Mikado Method to plan a multi-class refactoring, applies dependency inversion and interface segregation across the billing module.

### Example 3: RPP range sweep (L1-L3)
```
/nw:refactor src/des/domain/ --from=1 --to=3 --scope=module
```
Crafty sweeps L1 readability, L2 complexity, and L3 responsibility smells. Cascade rule applies: L2 only after L1 clean, L3 only after L2 clean.

### Example 4: Targeted single-level refactor
```
/nw:refactor src/des/cli/verify.py --level=3 --scope=file
```
Crafty targets L3 responsibility smells only (Large Class, Feature Envy, Shotgun Surgery). Assumes L1-L2 already clean.

## Expected Outputs

```
src/*                              (refactored production code)
tests/*                            (refactored test code)
docs/refactoring/
  refactoring-log.md
  quality-metrics.md
```
