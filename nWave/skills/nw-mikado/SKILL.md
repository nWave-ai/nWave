---
name: nw-mikado
description: "[EXPERIMENTAL] Complex refactoring roadmaps with visual tracking"
user-invocable: true
argument-hint: '[refactoring-goal] - Optional: --complexity=[simple|moderate|complex] --visualization=[tree|graph]'
---

# NW-MIKADO: Complex Refactoring with Mikado Method

> **EXPERIMENTAL**: Under active development. Behavior and output format may change between versions.

**Wave**: CROSS_WAVE
**Agent**: Crafty (nw-software-crafter)
**Command**: `*mikado`

## Overview

Plan and execute complex refactoring using the Mikado Method. Builds dependency {visualization} through iterative exploration|tracks discoveries via commits|executes leaf-to-goal bottom-up. For architectural changes spanning multiple classes where simple refactoring is insufficient.

## Context Files Required

- src/\* - Codebase to refactor
- docs/product/architecture/brief.md - Target architecture (if available)

## Agent Invocation

@nw-software-crafter

Execute \*mikado for {refactoring-goal}.

**Context Files:**
- src/\*
- docs/product/architecture/brief.md

**Configuration:**
- refactoring_goal: "{goal description with business value}"
- complexity: complex # simple/moderate/complex
- visualization: {tree|graph} # tree = indented markdown checklist, graph = Mermaid dependency diagram

## Success Criteria

- [ ] Mikado {visualization} persisted at docs/mikado/{goal-name}.mikado.md
- [ ] Discovery commits capture each exploration attempt
- [ ] All leaf nodes implemented bottom-up
- [ ] Goal node achieved with all tests passing
- [ ] {visualization_label} stable (no new dependencies emerging)

**Visualization labels**: tree → "Tree", graph → "Graph". Use the selected visualization type in all output messages (e.g., "Wrote the Mikado tree" or "Wrote the Mikado graph").

## Next Wave

**Handoff To**: {invoking-agent-returns-to-workflow}
**Deliverables**: Refactored codebase + Mikado {visualization} documentation

## Examples

### Example 1: Extract shared domain model
```
/nw-mikado "Extract shared domain model from monolithic service layer"
```
Crafty builds Mikado dependency {visualization} through iterative exploration, discovers 12 leaf nodes across 4 modules, executes bottom-up from leaves to goal with discovery commits at each step.

## Expected Outputs

```
docs/mikado/{goal-name}.mikado.md
src/*                                (refactored implementation)
Discovery-tracking commits in git log
```
