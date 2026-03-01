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

General-purpose agents needing tool calling and iterative problem-solving.

**Loop**: Reason -> Select/execute action -> Observe result -> Repeat until done.
**When**: Default pattern. Most specialist agents.
**Examples**: software-crafter, researcher, troubleshooter.

## 2. Reflection

Agent must evaluate and iteratively improve its own output.

**Loop**: Generate -> Review against criteria -> Identify gaps -> Refine -> Validate threshold met.
**When**: Quality-critical outputs where first-draft insufficient (code review, architecture review, agent validation).
**Examples**: agent-builder-reviewer, solution-architect-reviewer, software-crafter-reviewer.

## 3. Router

Request classified and delegated to exactly one specialist.

**Loop**: Analyze request -> Classify -> Select specialist -> Delegate.
**When**: Task dispatching, single path execution. Low overhead, fast routing.
**Examples**: workflow-dispatcher, task-router.

## 4. Planning

Complex tasks requiring structured decomposition before execution.

**Loop**: Decompose into sub-tasks -> Sequence -> Allocate resources -> Execute with checkpoints.
**When**: Multi-step implementations, migrations, large refactoring.
**Examples**: project-planner, migration-coordinator.

## 5. Sequential Orchestration

Linear workflows with clear dependencies between stages.

**Structure**: Agent1 -> Output1 -> Agent2 -> Output2 -> Agent3 -> Result
**When**: Pipeline workflows where each stage transforms previous output.
**Example**: nWave waves: DISCUSS -> DESIGN -> DEVOPS -> DISTILL -> DELIVER.

## 6. Parallel Orchestration

Multiple independent analyses needed simultaneously.

**Structure**: Supervisor -> [Worker1, Worker2, Worker3] (concurrent) -> Aggregate results.
**When**: Independent analyses, multi-aspect reviews, parallel risk assessment.
**Example**: Multi-reviewer code review, parallel security + performance + correctness analysis.

## 7. Hierarchical

Supervisor coordinates multiple worker agents dynamically.

**Structure**: Supervisor manages workers, routing tasks and aggregating results.
**When**: Complex coordination where routing depends on intermediate results.
**Example**: feature-coordinator supervising frontend/backend/database/testing specialists.

## Pattern Combinations

- **ReAct + Reflection**: Reason/act then self-review (most reviewer agents)
- **Planning + Sequential**: Decompose then execute pipeline (devop)
- **Router + Hierarchical**: Route to supervisor who coordinates workers

## Choosing for nWave Agents

| Agent Role | Pattern | Rationale |
|-----------|---------|-----------|
| Specialist (single domain) | ReAct | Tool-using, iterative task completion |
| Reviewer (-reviewer suffix) | Reflection | Must self-evaluate and iterate on critique |
| Wave orchestrator | Sequential | Clear dependency chain between phases |
| Multi-agent coordinator | Hierarchical | Dynamic task routing to specialists |
| Task dispatcher | Router | Classification and single-path delegation |
