---
name: mikado-method
description: Enhanced Mikado Method for complex architectural refactoring - systematic dependency discovery, tree-based planning, and bottom-up execution
---

# Mikado Method

Use for complex refactoring where direct implementation causes cascading failures across multiple classes/modules.

## When to Use

- Refactoring goal affects multiple classes/modules
- Direct implementation attempt causes cascade of failures
- Dependencies are not immediately clear
- Risk of breaking existing functionality is high

## Core Process

Cycle: Set Goal > Experiment > Visualize prerequisites > Revert to working state.

Treat compilation/test failures as valuable information — each failure reveals a prerequisite node in the dependency graph. Revert keeps codebase shippable at all times.

## Discovery-Tracking Protocol

Commit immediately after each dependency discovery to preserve exploration history and enable interrupt/resume.

### Commit Formats

- Dependency: `Discovery: [Class.Method(params)] requires [Prerequisite] in [File:Line]`
- False leaf: `Discovery: False leaf - [Node] blocked by [Dependency]`
- Exploration complete: `Discovery: No new dependencies found - exploration complete for [GoalArea]`
- Ready: `Ready: True leaves identified - [Count] leaves ready for execution`

## Exhaustive Exploration Algorithm

Sequence: EXPERIMENT > LEARN > GRAPH > COMMIT GRAPH > REVERT

1. **Experiment**: Attempt naive implementation of stated goal
2. **Learn**: Capture ALL compilation and test failures immediately
3. **Graph**: Create concrete prerequisite nodes with exact specifications
4. **Commit Graph**: Commit discovery with mandatory format
5. **Revert**: Revert ALL code changes to maintain clean state

### Termination Criteria

- Every apparent leaf candidate systematically attempted
- No new dependencies emerge from leaf implementation attempts
- Tree structure remains stable across multiple exploration cycles
- True leaves confirmed with zero prerequisites

## Concrete Node Specification

Nodes require method-level specificity:

- Method signatures: `ClassName.MethodName(parameter types) -> ReturnType`
- File locations: `src/Services/UserService.cs, line 45`
- Access modifiers: public, private, internal, protected
- Refactoring technique: Extract Method, Move Method, etc.
- Atomic transformation: Rename, Extract, Inline, Move, Safe Delete
- Code smell target: Long Method, Feature Envy, etc.

## Tree File Management

### File Structure

- Directory: `docs/mikado/`
- Filename: `<goal-name>.mikado.md`
- Format: `- [ ]` pending, `- [x]` completed
- Indentation: 4 spaces per nesting level
- Dependencies indented deeper than dependents

### Tree Structure Rules

1. Root goal at 0 indentation
2. Direct dependencies at 4-space indentation
3. Sub-dependencies at 8-space indentation, continuing per level
4. Child nodes must complete before parent nodes
5. Nodes at same indentation level are independent (parallelizable)

## Two-Mode Operation

### Exploration Mode

1. Attempt naive implementation of refactoring goal
2. Capture compilation/test failures with full details
3. Create concrete prerequisite nodes with method-level specificity
4. Add dependencies to tree file with proper indentation nesting
5. Commit tree discovery only (specific format)
6. Revert code changes completely except tree file
7. Repeat until no new dependencies discovered

### Execution Mode

1. Identify deepest indentation level with incomplete nodes
2. Select only true leaves (most nested, zero prerequisites)
3. Execute one leaf at a time for safety
4. Complete all nodes at current level before moving up
5. Never attempt parent node until all children complete
6. Implement minimal possible change per leaf
7. Validate with full test execution
8. Commit implementation, update tree marking node complete
9. Proceed bottom-up to next true leaf

## Tree Example

```markdown
- [ ] Goal: Replace direct DB calls in OrderController with repository pattern
    - [ ] Update OrderController constructor to use IOrderRepository
        - [ ] Implement SqlOrderRepository : IOrderRepository
            - [ ] Create IOrderRepository interface
                - [ ] Define GetOrderById(int orderId) -> Order? method signature
                - [ ] Define SaveOrder(Order order) -> Task method signature
            - [ ] Add constructor SqlOrderRepository(IDbContext context)
                - [ ] Verify IDbContext is registered in DI container
        - [ ] Implement GetOrderById method
            - [ ] Handle null order case with OrderNotFoundException
                - [x] Create OrderNotFoundException class
    - [ ] Register IOrderRepository in DI container
    - [ ] Remove IDbContext _context field from OrderController
```

Execution order: deepest leaves first, working up level by level.

## Timeboxed Experimentation

10-minute timebox per attempt. If change can't be made in 10 min, it's too complex — break down further.

- Success: commit, check off node, move to next
- Fail: revert, identify missing prerequisites, write subgoals

## Goal Definition

Convert technical goals to stakeholder-understandable business value:

- Correct: "Customer address is retrieved using the latest version of the third-party API for improved reliability"
- Incorrect: "Update third-party API to version X"

## Integration with TDD

- All Mikado execution steps maintain passing tests (green bar)
- Each leaf execution = one atomic commit with tests passing
- If any step breaks tests, revert immediately and reassess dependencies
- Baby steps rhythm: test-commit-integrate every small change
