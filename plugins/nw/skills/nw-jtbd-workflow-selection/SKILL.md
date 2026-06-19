---
name: nw-jtbd-workflow-selection
description: JTBD workflow classification and routing - ODI two-phase framework, five job types with workflow sequences, baseline type selection, workflow anti-patterns, and common recipes
user-invocable: false
disable-model-invocation: true
---

# JTBD Workflow Selection

Classify incoming work by job type and recommend the appropriate nWave workflow entry point. Use during Phase 1 (GATHER) to triage before crafting stories.

## ODI Two-Phase Framework

Determine which phase applies before proceeding.

**Phase 1: Discovery** -- when you do not know what to build

```
[research] --> discuss --> design --> distill
    |            |           |          |
GATHER        WHAT are    HOW should  WHAT does
evidence      the needs?  it work?    "done" look like?
```

**Phase 2: Execution Loop** -- when you know what needs to change

```
[research] --> baseline --> roadmap --> split --> execute --> review
    |            |            |           |          |          |
GATHER        MEASURE      PLAN it     BREAK it   DO each    CHECK
evidence      first        completely  into atoms  task       quality
                                          |
                              <-----------+ (loop per task)
```

Key insight: `research` is a cross-wave capability invocable at any point for evidence-based decisions.

### When to Skip Discovery

Skip discovery and enter execution loop directly when ALL hold:
- User already understands the problem domain
- Problem is identified and scoped
- No stakeholder alignment needed
- User can articulate what "done" looks like

If any fail, start with discovery (DISCUSS wave).

## Five Job Types

### Job 1: Build Something New (Greenfield)

> "I need to create something that doesn't exist yet"

```
[research] -> discuss -> design -> [diagram] -> distill -> baseline -> roadmap -> split -> execute -> review
```

| Step | Purpose |
|------|---------|
| research | (Optional) Gather domain knowledge before requirements |
| discuss | Gather requirements -- you don't know what's needed yet |
| design | Architecture decisions, technology selection |
| diagram | (Optional) Visualize architecture for stakeholders |
| distill | Define acceptance tests -- what does "done" look like? |
| baseline | Measure starting point for tracking improvement |
| roadmap | Comprehensive plan while context is fresh |
| split | Break into atomic, self-contained tasks |
| execute | Do each task with clean context |
| review | Quality gate before proceeding |

### Job 2: Improve Existing System (Brownfield)

> "I know what needs to change in our system"

```
[research] -> baseline -> roadmap -> split -> execute -> review (repeat)
```

Skip discovery: system understood and problem identified. Baseline is blocking gate -- measure current state before planning. Prevents "optimizing the wrong thing."

### Job 3: Complex Refactoring

> "Code works but structure needs improvement"

Simple refactoring:
```
[root-why] -> mikado -> refactor (incremental)
```

Complex refactoring with tracking:
```
[research] -> baseline -> roadmap (methodology: mikado) -> split -> execute -> review
```

Mikado Method explores dependencies before committing. Reversible at every step.

### Job 4: Investigate and Fix Issue

> "Something is broken and I need to find why"

```
[research] -> root-why -> develop -> deliver
```

Minimal sequence -- focused intervention only.

### Job 5: Research and Understand

> "I need to gather information before deciding"

```
research -> [decision point: which job to pursue next]
```

No execution -- pure information gathering feeding into other jobs.

## Quick Reference Matrix

| Job | You Know What? | Sequence |
|-----|---------------|----------|
| Greenfield | No | [research] -> discuss -> design -> [diagram] -> distill -> baseline -> roadmap -> split -> execute -> review |
| Brownfield | Yes | [research] -> baseline -> roadmap -> split -> execute -> review |
| Refactoring | Partially | [research] -> baseline -> mikado/roadmap -> split -> execute -> review |
| Bug Fix | Yes (symptom) | [research] -> root-why -> develop -> deliver |
| Research | No | research -> (output informs next job) |

Items in `[brackets]` are optional. Cross-wave commands (usable anytime): research, diagram, root-why, git.

## Baseline Type Selection

When workflow includes a baseline step, advise on which type to create.

### Performance Optimization
Use when improving speed, reducing resource usage, or optimizing throughput.
Required: timing measurements with breakdown | bottleneck ranking | target metrics with evidence | quick wins identified.

### Process Improvement
Use when fixing workflow issues, preventing incidents, or improving reliability.
Required: incident references or failure modes | simplest alternatives considered (with why insufficient).

### Feature Development
Use when building new capabilities (greenfield or brownfield).
Required: current state analysis | requirements source and validation.

## Workflow Anti-Patterns

Operate at project/feature level, distinct from story-level anti-patterns in `leanux-methodology` skill.

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Skip research | Decisions without evidence | Research when unfamiliar with domain |
| Skip baseline | Optimize the wrong thing | Always baseline before roadmap |
| Monolithic tasks | Context degradation | Use split for atomic tasks |
| Skip review | Quality issues propagate | Review before each execute |
| Architecture before measurement | Over-engineering | Baseline identifies quick wins first |
| Forward references in tasks | Tasks not self-contained | Each task must have all context embedded |

## Common Workflow Recipes

| Situation | Entry Point | Key Characteristic |
|-----------|------------|-------------------|
| New feature on existing codebase | baseline (skip discovery) | Existing system, new capability |
| Performance optimization | baseline (type: performance) | Measurement-first |
| Legacy system modernization | research + root-why + baseline | Deep understanding first |
| Quick bug fix | root-why + develop + deliver | Minimal sequence |
| Pure research task | research | Output informs next job selection |
| Data-heavy project | research + baseline | Specialist agent involvement |

## Job Categories Summary

| Category | Core Job |
|----------|----------|
| Understanding | Know what to build and why |
| Planning | Break work into safe, trackable chunks |
| Executing | Do work without context degradation |
| Validating | Catch issues early with quality gates |
| Communicating | Share understanding via diagrams and docs |
| Investigating | Find truth before acting |

For deep opportunity analysis with ODI scoring, defer to product-discoverer agent. Product-owner applies simpler prioritization (MoSCoW, Value/Effort) for story-level ordering -- see `leanux-methodology` skill.
