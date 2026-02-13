---
name: design-patterns
description: 7 agentic design patterns with decision tree for choosing the right pattern for each agent type
---

# Agentic Design Patterns

## Pattern Decision Tree

```
Is the agent doing a single focused task?
  YES -> Does it need self-evaluation?
    YES -> Reflection
    NO  -> ReAct (default for most agents)
  NO -> Is it coordinating multiple agents?
    YES -> Are tasks independent?
      YES -> Parallel Orchestration
      NO  -> Are tasks sequential with dependencies?
        YES -> Sequential Orchestration
        NO  -> Hierarchical (supervisor + workers)
    NO -> Is it routing to one of several specialists?
      YES -> Router
      NO  -> Does it need structured task decomposition?
        YES -> Planning
        NO  -> ReAct (default)
```

## 1. ReAct (Reason + Act)

Use for general-purpose agents needing tool calling and iterative problem-solving.

**Loop**: Reason about situation -> Select and execute action -> Observe result -> Repeat until done.

**When to use**: Default pattern. Most specialist agents (software-crafter, researcher, acceptance-designer).

**Example agents**: software-crafter, researcher, troubleshooter.

## 2. Reflection

Use when the agent must evaluate and iteratively improve its own output.

**Loop**: Generate output -> Review against criteria -> Identify gaps -> Refine -> Validate quality threshold met.

**When to use**: Quality-critical outputs where first-draft is insufficient (code review, architecture review, agent validation).

**Example agents**: agent-builder-reviewer, solution-architect-reviewer, software-crafter-reviewer.

## 3. Router

Use when a request must be classified and delegated to exactly one specialist.

**Loop**: Analyze request -> Classify task type -> Select appropriate specialist -> Delegate.

**When to use**: Task dispatching where only one path should execute. Low overhead, fast routing.

**Example agents**: workflow-dispatcher, task-router.

## 4. Planning

Use for complex tasks requiring structured decomposition before execution.

**Loop**: Decompose into sub-tasks -> Sequence logically -> Allocate resources -> Execute with validation checkpoints.

**When to use**: Multi-step implementations, migrations, large refactoring.

**Example agents**: project-planner, migration-coordinator.

## 5. Sequential Orchestration

Use for linear workflows with clear dependencies between stages.

**Structure**: Agent1 -> Output1 -> Agent2 -> Output2 -> Agent3 -> Result

**When to use**: Pipeline workflows where each stage transforms the previous output.

**Example**: nWave waves: DISCUSS -> DESIGN -> DEVOP -> DISTILL -> DELIVER.

## 6. Parallel Orchestration

Use when multiple independent analyses are needed simultaneously.

**Structure**: Supervisor -> [Worker1, Worker2, Worker3] (concurrent) -> Aggregate results.

**When to use**: Independent analyses, multi-aspect reviews, parallel risk assessment.

**Example**: Multi-reviewer code review, parallel security + performance + correctness analysis.

## 7. Hierarchical

Use when a supervisor agent coordinates multiple worker agents dynamically.

**Structure**: Supervisor manages [Worker1, Worker2, Worker3], routing tasks and aggregating results.

**When to use**: Complex coordination where task routing depends on intermediate results.

**Example**: feature-coordinator supervising frontend/backend/database/testing specialists.

## Pattern Combinations

Agents can combine patterns:
- **ReAct + Reflection**: Agent reasons and acts, then self-reviews (most reviewer agents)
- **Planning + Sequential**: Decompose then execute pipeline (devop)
- **Router + Hierarchical**: Route to supervisor who coordinates workers

## Choosing for nWave Agents

| Agent Role | Recommended Pattern | Rationale |
|-----------|-------------------|-----------|
| Specialist (single domain) | ReAct | Tool-using, iterative task completion |
| Reviewer (-reviewer suffix) | Reflection | Must self-evaluate and iterate on critique |
| Wave orchestrator | Sequential | Clear dependency chain between phases |
| Multi-agent coordinator | Hierarchical | Dynamic task routing to specialists |
| Task dispatcher | Router | Classification and single-path delegation |
