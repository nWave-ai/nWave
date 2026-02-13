# Jobs To Be Done Guide: nWave Framework

## Overview

This guide uses the **Outcome Driven Innovation (ODI)** framework to help you understand when and how to use the nWave agentic system based on your specific job context.

---

## Two Distinct Phases

The framework operates in **two fundamentally different phases** that can be used independently:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: DISCOVERY                               │
│           (When you DON'T KNOW what to build)                           │
│                                                                         │
│   [research] ──→ discuss ──→ design ──→ distill                         │
│       │            │           │          │                             │
│   GATHER        WHAT are    HOW should  WHAT does                       │
│   evidence      the needs?  it work?    "done" look like?               │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PHASE 2: EXECUTION LOOP                             │
│              (When you KNOW what needs to change)                       │
│                                                                         │
│   [research] ──→ baseline ──→ roadmap ──→ split ──→ execute ──→ review  │
│       │            │            │           │          │          │     │
│   GATHER        MEASURE      PLAN it     BREAK it   DO each    CHECK    │
│   evidence      first!       completely  into atoms  task       quality │
│                                              │                          │
│                                  ◄───────────┘ (loop per task)          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Note**: `research` is a **CROSS_WAVE** capability - it can be invoked at any point when evidence-based decision making is needed.

---

## The Research Step (Cross-Wave)

Research is not a fixed step in a sequence - it's a capability you invoke **whenever you need evidence**:

| When to Research | Purpose |
|------------------|---------|
| Before discuss | Understand domain before gathering requirements |
| Before design | Evaluate technology options with evidence |
| Before baseline | Gather measurements and quantitative data |
| During roadmap execution | Research tasks as part of the plan |
| When stuck | Gather information to unblock decisions |

**Example Commands**:

```bash
# Domain research before requirements
/nw:research "multi-tenant architecture patterns"

# Technology evaluation
/nw:research "compare OAuth2 providers for enterprise"

# Performance research (quantitative)
/nw:research "analyze test execution bottlenecks"

# Research with embed for agent knowledge
/nw:research "Residuality Theory" --embed-for=solution-architect
```

---

## Jobs To Be Done

### JOB 1: Build Something New (Greenfield)

> *"I need to create something that doesn't exist yet"*

**Key Question**: What should we build?

**Sequence**:

```text
[research] → discuss → design → [diagram] → distill → baseline → roadmap → split → execute → review
```

**Why each step**:

| Step | Purpose |
|------|---------|
| `research` | (Optional) Gather domain knowledge before requirements |
| `discuss` | Gather requirements - you don't know what's needed yet |
| `design` | Make architecture decisions, select technology |
| `diagram` | (Optional) Visualize architecture for stakeholder communication |
| `distill` | Define acceptance tests - what does "done" look like? |
| `baseline` | Measure starting point for tracking improvement |
| `roadmap` | Create comprehensive plan while context is fresh |
| `split` | Break into atomic, self-contained tasks |
| `execute` | Do each task with clean context |
| `review` | Quality gate before proceeding |

**Example Commands**:

```bash
/nw:research "authentication best practices for SaaS"
/nw:start "Build user authentication system"
/nw:discuss "authentication requirements"
/nw:design --architecture=hexagonal
/nw:diagram --format=mermaid --level=container  # Visualize architecture
/nw:distill "user-login-story"
/nw:baseline "implement authentication"
/nw:roadmap @solution-architect "implement authentication"
/nw:split @devop "implement-authentication"
/nw:execute @software-crafter "docs/workflow/implement-authentication/steps/01-01.json"
/nw:review @software-crafter task "docs/workflow/implement-authentication/steps/01-02.json"
# After implementation, update diagrams if architecture evolved
/nw:diagram --format=mermaid --level=component
```

---

### JOB 2: Improve Existing System (Brownfield)

> *"I know what needs to change in our system"*

**Key Question**: How do I change it safely and incrementally?

**Sequence**:

```text
[research] → baseline → roadmap → split → execute → review (repeat)
```

**Why skip discovery**:

- You already understand the system
- Problem is identified
- Go straight to **measured, incremental execution**

**The baseline is CRITICAL**:

- Blocks roadmap creation until you MEASURE current state
- Prevents "optimizing the wrong thing" anti-pattern
- Forces evidence-based planning

**Example Commands**:

```bash
/nw:research "xUnit parallelization strategies"  # Optional: gather options
/nw:baseline "optimize test execution time"
/nw:roadmap @solution-architect "optimize test execution time"
/nw:split @devop "optimize-test-execution-time"
/nw:execute @researcher "docs/workflow/optimize-test-execution-time/steps/01-01.json"
/nw:review @software-crafter task "docs/workflow/optimize-test-execution-time/steps/02-01.json"
/nw:execute @software-crafter "docs/workflow/optimize-test-execution-time/steps/02-01.json"
# ... repeat execute → review for each task
/nw:finalize @devop "optimize-test-execution-time"
```

---

### JOB 3: Complex Refactoring

> *"Code works but structure needs improvement"*

**Key Question**: How do I restructure without breaking things?

**Sequence (simple refactoring)**:

```text
[root-why] → mikado → refactor (incremental)
```

**Sequence (complex refactoring with tracking)**:

```text
[research] → baseline → roadmap (methodology: mikado) → split → execute → review
```

**Why Mikado Method**:

- Explores dependencies BEFORE committing to changes
- Reversible at every step
- Discovery tracking for audit trail

**Example Commands**:

```bash
# Simple refactoring
/nw:mikado "extract payment processing module"
/nw:refactor --target="PaymentService" --level=3

# Complex refactoring with full tracking
/nw:research "strangler fig pattern for legacy replacement"
/nw:baseline "replace legacy authentication"
/nw:roadmap @software-crafter "replace legacy authentication"  # Sets methodology: mikado
/nw:split @devop "replace-legacy-authentication"
/nw:execute @software-crafter "docs/workflow/replace-legacy-authentication/steps/01-01.json"
```

---

### JOB 4: Investigate & Fix Issue

> *"Something is broken and I need to find why"*

**Key Question**: What's the root cause?

**Sequence**:

```text
[research] → root-why → develop → deliver
```

**Minimal sequence** - focused intervention only.

**Example Commands**:

```bash
/nw:research "JWT token expiration edge cases"  # Optional: if unfamiliar with area
/nw:root-why "authentication timeout errors in production"
/nw:develop "fix-auth-timeout"
/nw:deliver
```

---

### JOB 5: Research & Understand

> *"I need to gather information before deciding"*

**Key Question**: What are my options?

**Sequence**:

```text
research → [decision point: which job to pursue next]
```

**No execution** - pure information gathering that feeds into other jobs.

**Example Commands**:

```bash
# Technology evaluation
/nw:research "compare OAuth2 providers for enterprise use"

# Domain understanding
/nw:research "event sourcing patterns for audit trails"

# Research with knowledge embedding for future use
/nw:research "Hexagonal Architecture" --embed-for=solution-architect
```

**Research Output Locations**:

- Research files: `docs/research/{category}/{topic}.md`
- Embedded knowledge: `nWave/data/embed/{agent}/{topic}.md`

---

## Quick Reference Matrix

| Job | You Know What? | Sequence |
|-----|---------------|----------|
| **Greenfield** | No | [research] → discuss → design → [diagram] → distill → baseline → roadmap → split → execute → review |
| **Brownfield** | Yes | [research] → baseline → roadmap → split → execute → review |
| **Refactoring** | Partially | [research] → baseline → mikado/roadmap → split → execute → review |
| **Bug Fix** | Yes (symptom) | [research] → root-why → develop → deliver |
| **Research** | No | research → (output informs next job) |
| **Documentation** | Varies | [research] → design → diagram |

*Note: Items in `[brackets]` are optional - use when needed.*

**Cross-wave commands** (can be used anytime):

- `research` - Gather evidence
- `diagram` - Visualize architecture
- `root-why` - Investigate issues
- `git` - Version control operations

---

## Granular Jobs By Phase

This section breaks down what specific job each command fulfills.

### Discovery Phase Jobs

#### DISCUSS Wave

| Job | Command | Outcome |
|-----|---------|---------|
| Capture stakeholder needs | `/nw:discuss` | Requirements documented |
| Align business and tech | `/nw:discuss` | Shared understanding |
| Define acceptance criteria | `/nw:discuss` | Testable requirements |

#### DESIGN Wave

| Job | Command | Outcome |
|-----|---------|---------|
| Choose architecture pattern | `/nw:design` | Architecture decision |
| Select technology stack | `/nw:design` | Technology rationale |
| Define component boundaries | `/nw:design` | Clear module separation |
| Communicate architecture visually | `/nw:diagram` | Stakeholder-ready diagrams |

#### DISTILL Wave

| Job | Command | Outcome |
|-----|---------|---------|
| Define what "done" looks like | `/nw:distill` | Acceptance tests (Given-When-Then) |

### Execution Loop Jobs

#### BASELINE

| Job | Command | Outcome |
|-----|---------|---------|
| Measure current state | `/nw:baseline` | Quantified starting point |
| Identify biggest bottleneck | `/nw:baseline` | Prioritized problem |
| Find quick wins | `/nw:baseline` | Low-effort high-impact options |
| Prevent wrong-problem syndrome | `/nw:baseline` | Evidence-based focus |

#### ROADMAP

| Job | Command | Outcome |
|-----|---------|---------|
| Plan while context is fresh | `/nw:roadmap` | Comprehensive plan |
| Capture dependencies | `/nw:roadmap` | Sequenced steps |
| Enable parallel work | `/nw:roadmap` | Independent task identification |

#### SPLIT

| Job | Command | Outcome |
|-----|---------|---------|
| Prevent context degradation | `/nw:split` | Atomic self-contained tasks |
| Enable clean execution | `/nw:split` | Each task has full context |
| Track progress granularly | `/nw:split` | Individual task state |

#### EXECUTE

| Job | Command | Outcome |
|-----|---------|---------|
| Do work with max LLM quality | `/nw:execute` | Clean context per task |
| Track state transitions | `/nw:execute` | TODO → IN_PROGRESS → DONE |
| Capture execution results | `/nw:execute` | Evidence of completion |

#### REVIEW

| Job | Command | Outcome |
|-----|---------|---------|
| Catch issues before they propagate | `/nw:review` | Quality gate |
| Get expert critique | `/nw:review` | Domain-specific feedback |
| Validate acceptance criteria | `/nw:review` | APPROVED / NEEDS_REVISION |

### Cross-Wave Jobs

#### Research & Investigation

| Job | Command | Outcome |
|-----|---------|---------|
| Gather evidence before deciding | `/nw:research` | Cited findings |
| Evaluate technology options | `/nw:research` | Comparison analysis |
| Understand unfamiliar domain | `/nw:research` | Knowledge base |
| Find root cause (not symptoms) | `/nw:root-why` | 5 Whys analysis |
| Understand failure patterns | `/nw:root-why` | Multi-causal map |

#### Development

| Job | Command | Outcome |
|-----|---------|---------|
| Implement with TDD | `/nw:develop` | Test-first code |
| Refactor safely | `/nw:refactor` | Improved structure |
| Handle complex dependencies | `/nw:mikado` | Reversible change path |

#### Operations

| Job | Command | Outcome |
|-----|---------|---------|
| Commit with quality | `/nw:git` | Clean commits |
| Validate production readiness | `/nw:deliver` | Deployment confidence |
| Archive completed work | `/nw:finalize` | Clean project closure |

### Job Categories Summary

| Category | Core Job |
|----------|----------|
| **Understanding** | Know what to build and why |
| **Planning** | Break work into safe, trackable chunks |
| **Executing** | Do work without context degradation |
| **Validating** | Catch issues early with quality gates |
| **Communicating** | Share understanding via diagrams and docs |
| **Investigating** | Find truth before acting |

---

## When to Skip Discovery Phase

Skip `discuss → design → distill` when:

- You already understand the domain
- Requirements are clear
- Architecture is established
- Problem is well-defined

Go straight to the **execution loop** with baseline as the gate.

---

## The Execution Loop (Core Workflow)

The execution loop is the workhorse of brownfield work:

```text
[research] → baseline → roadmap → split → execute → review
                │                           │         │
                │                           └────────►│ (repeat per task)
                │                                      │
                └──────────────────────────────────────┘ (new baseline if scope changes)
```

### Why It Works

| Step | Benefit |
|------|---------|
| **research** | (Optional) Gather evidence to inform baseline and roadmap |
| **baseline** | Forces measurement before planning (prevents wrong-problem anti-pattern) |
| **roadmap** | Captures full plan while context is fresh |
| **split** | Creates atomic, self-contained tasks (prevents context degradation) |
| **execute** | Each task runs with clean context (max LLM quality) |
| **review** | Quality gate before proceeding |

### Key Principles

1. **Evidence Before Decisions**: Research when you need data to decide
2. **Measure Before Plan**: Baseline is a BLOCKING gate for roadmap
3. **Atomic Tasks**: Each task is self-contained with all context embedded
4. **Clean Context**: Each execute starts fresh (no accumulated confusion)
5. **Quality Gates**: Review before moving to next task

---

## Baseline Types

The `/nw:baseline` command supports three types:

### 1. Performance Optimization

Use when improving speed, reducing resource usage, or optimizing throughput.

**Required**:

- Timing measurements with breakdown
- Bottleneck ranking
- Target metrics with evidence
- Quick wins identified

### 2. Process Improvement

Use when fixing workflow issues, preventing incidents, or improving reliability.

**Required**:

- Incident references OR failure modes
- Simplest alternatives considered (with why insufficient)

### 3. Feature Development

Use when building new capabilities (greenfield or brownfield development).

**Required**:

- Current state analysis
- Requirements source and validation

---

## Agent Selection

For complete agent specifications and selection guidance, see the [nWave Commands Reference](../reference/nwave-commands-reference.md).

**Quick Overview**:
- **Core Wave Agents**: product-owner, solution-architect, acceptance-designer, software-crafter, devop
- **Cross-Wave Specialists**: researcher, troubleshooter, visual-architect, data-engineer, product-discoverer, agent-builder, illustrator, documentarist
- **Reviewer Agents**: Every agent has a `*-reviewer` variant for quality assurance

---

## Common Workflows

### New Feature on Existing Codebase

```bash
/nw:research "best practices for {feature-domain}"  # Optional
/nw:baseline "add multi-tenant support"
/nw:roadmap @solution-architect "add multi-tenant support"
/nw:split @devop "add-multi-tenant-support"
# execute → review loop
```

### Performance Optimization

```bash
/nw:research "profiling techniques for {technology}"  # Optional
/nw:baseline "optimize API response time"  # Type: performance_optimization
/nw:roadmap @solution-architect "optimize API response time"
/nw:split @devop "optimize-api-response-time"
# execute → review loop
```

### Legacy System Modernization

```bash
/nw:research "strangler fig pattern"
/nw:root-why "current system limitations"
/nw:baseline "migrate to microservices"
/nw:roadmap @solution-architect "migrate to microservices"
/nw:split @devop "migrate-to-microservices"
# execute → review loop with mikado for complex refactoring
```

### Quick Bug Fix

```bash
/nw:root-why "users cannot login after password reset"
/nw:develop "fix-password-reset-flow"
/nw:deliver
```

### Pure Research Task

```bash
/nw:research "event sourcing vs CRUD for audit requirements"
# Output: docs/research/architecture-patterns/event-sourcing-vs-crud.md
# Decision: proceed with JOB 1, 2, or 3 based on findings
```

### Architecture with Visual Documentation

```bash
/nw:design --architecture=hexagonal
/nw:diagram --format=mermaid --level=container
# Output: docs/architecture/diagrams/*.svg
```

### Data-Heavy Project

```bash
/nw:research "compare PostgreSQL vs MongoDB for {use-case}"
# Invoke data-engineer agent for specialized guidance
/nw:baseline "implement data pipeline"
/nw:roadmap @data-engineer "implement data pipeline"
/nw:split @devop "implement-data-pipeline"
# execute → review loop
```

### Git Workflow Integration

```bash
# After completing a task
/nw:git commit  # Auto-generates commit message
/nw:git branch "feature/auth-upgrade"
/nw:git push
```

### Creating a New Agent

```bash
/nw:forge  # Uses agent-builder to create new agent from template
# Output: nWave/agents/{new-agent}.md
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Skip research | Decisions without evidence | Research when unfamiliar with domain |
| Skip baseline | Optimize wrong thing | Always baseline before roadmap |
| Monolithic tasks | Context degradation | Use split for atomic tasks |
| Skip review | Quality issues propagate | Review before each execute |
| Architecture before measurement | Over-engineering | Baseline identifies quick wins first |
| Forward references in tasks | Tasks not self-contained | Each task must have all context embedded |

---

## Command and File Reference

For complete command specifications, agent selection, and file locations, see the [nWave Commands Reference](../reference/nwave-commands-reference.md).
