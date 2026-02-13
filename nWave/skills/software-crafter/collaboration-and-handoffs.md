---
name: collaboration-and-handoffs
description: Cross-agent collaboration protocols, workflow handoff patterns, and commit message formats for TDD/Mikado/refactoring workflows
---

# Collaboration and Handoffs

## Cross-Agent Collaboration

### Receives From

- **acceptance_designer** (DISTILL): E2E acceptance tests, business validation requirements, production integration patterns
- **solution_architect** (DESIGN): architecture patterns, component boundaries, technology constraints, port definitions

### Hands Off To

- **feature_completion_coordinator** (DELIVER): working implementation, complete test coverage, quality metrics, refactored codebase, validated business value

### Collaborates With

- **architecture_diagram_manager**: visual validation of implementation against architecture, diagram updates during refactoring

## 4 Workflow Handoff Patterns

### 1. TDD to Mikado

- **Trigger**: complex architectural refactoring requirements emerge during TDD
- **Content**: working implementation with test coverage, identified architectural complexity, business value articulation
- **Transition**:
  1. Pause TDD at stable green state
  2. Activate Mikado exploration mode
  3. Define business-value-focused refactoring goal
  4. Execute exhaustive exploration with discovery-tracking commits
  5. Build complete dependency tree
  6. Resume through Mikado execution or transition to refactoring

### 2. TDD to Refactoring

- **Trigger**: feature implementation complete, code quality improvements needed
- **Content**: working implementation with test coverage, code smells identified, all tests passing
- **Transition**:
  1. Commit TDD implementation with all tests green
  2. Activate progressive refactoring mode
  3. Execute comprehensive code smell detection
  4. Apply Level 1-6 refactoring in mandatory sequence
  5. Maintain 100% test pass rate throughout
  6. Commit after each successful atomic transformation

### 3. Mikado to Systematic Execution

- **Trigger**: Mikado exploration complete, true leaves identified
- **Content**: complete dependency tree with annotations, true leaves with zero prerequisites, refactoring mechanics per node
- **Transition**:
  1. Validate exploration completeness (no new dependencies)
  2. Confirm tree structure with proper nesting
  3. Activate systematic execution mode
  4. Execute leaves bottom-up using embedded refactoring knowledge
  5. Maintain shared progress tracking
  6. Ensure test-driven safety throughout

### 4. Integrated Workflow Patterns

```yaml
tdd_with_continuous_refactoring:
  pattern: "TDD -> L1-L2 Refactoring -> TDD (continuous cycle)"
  timing: "After each GREEN phase in inner TDD loop"
  scope: "Level 1-2 only during active TDD"

tdd_with_mikado_planning:
  pattern: "TDD -> Mikado Exploration -> TDD Continuation"
  timing: "When architectural complexity blocks TDD progress"
  scope: "Full Mikado Method with return to TDD"

mikado_with_systematic_execution:
  pattern: "Mikado Exploration -> Systematic Refactoring Execution"
  timing: "After exploration identifies true leaves"
  scope: "Full systematic refactoring with tree-guided execution"
```

## 4 Commit Message Formats

### 1. TDD Implementation

```
feat(<component>): <business-value-description>

- Implemented: <specific feature or capability>
- Tests: <test coverage details>
- Architecture: <architectural layer(s) touched>
- E2E Status: <enabled/disabled with reason>

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 2. Mikado Discovery

```
Discovery: [SpecificClass.Method(parameters)] requires [ExactPrerequisite] in [FilePath:LineNumber]

- Tree: docs/mikado/<goal-name>.mikado.md updated
- Dependencies: <count> new dependencies discovered
- Exploration: <status of exploration phase>

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 3. Mikado Implementation

```
feat(mikado): Implement leaf node - <node-description>

- Mikado Node: <specific node from tree>
- Tree Progress: <completed-count>/<total-count> leaves complete
- Tests: All passing

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 4. Refactoring Transformation

```
refactor(level-N): <atomic-transformation-description>

- Applied: <specific refactoring technique>
- Target: <code smell(s) addressed>
- Files: <list of modified files>
- Tests: All passing
- Mikado: <mikado-node-reference> (when applicable)

Co-Authored-By: Claude <noreply@anthropic.com>
```
