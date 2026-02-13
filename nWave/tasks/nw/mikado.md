---
description: "[EXPERIMENTAL] Complex refactoring roadmaps with visual tracking"
argument-hint: "[refactoring-goal] - Optional: --complexity=[simple|moderate|complex] --visualization=[tree|graph]"
---

# NW-MIKADO: Complex Refactoring with Mikado Method

> **EXPERIMENTAL**: This command is still under active development. Behavior and output format may change between versions.

**Wave**: CROSS_WAVE
**Agent**: Crafty (nw-software-crafter)
**Command**: `*mikado`

## Overview

Plan and execute complex refactoring operations using the Mikado Method. Builds a dependency graph through iterative exploration, tracks discoveries via commits, and executes leaf-to-goal bottom-up. For architectural changes spanning multiple classes where simple refactoring is insufficient.

## Context Files Required

- src/\* - Codebase to refactor
- docs/architecture/architecture-design.md - Target architecture (if available)

## Agent Invocation

@nw-software-crafter

Execute \*mikado for {refactoring-goal}.

**Context Files:**

- src/\*
- docs/architecture/architecture-design.md

**Configuration:**

- refactoring_goal: "{goal description with business value}"
- complexity: complex # simple/moderate/complex

## Success Criteria

- [ ] Mikado graph persisted at docs/mikado/{goal-name}.mikado.md
- [ ] Discovery commits capture each exploration attempt
- [ ] All leaf nodes implemented bottom-up
- [ ] Goal node achieved with all tests passing
- [ ] Graph stable (no new dependencies emerging)

## Next Wave

**Handoff To**: {invoking-agent-returns-to-workflow}
**Deliverables**: Refactored codebase + Mikado graph documentation

## Examples

### Example 1: Extract shared domain model
```
/nw:mikado "Extract shared domain model from monolithic service layer"
```
Crafty builds a Mikado dependency graph through iterative exploration, discovers 12 leaf nodes across 4 modules, executes bottom-up from leaves to goal with discovery commits at each step.

## Expected Outputs

```
docs/mikado/{goal-name}.mikado.md
src/*                                (refactored implementation)
Discovery-tracking commits in git log
```
