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
│   [research] ──→ discuss ──→ design ──→ [devops] ──→ distill            │
│       │            │           │           │            │               │
│   GATHER        WHAT are    HOW should  PLATFORM     WHAT does          │
│   evidence      the needs?  it work?    ready?       "done" look like?  │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PHASE 2: EXECUTION LOOP                             │
│              (When you KNOW what needs to change)                       │
│                                                                         │
│   [research] ──→ roadmap ──→ execute ──→ [refactor] ──→ review           │
│       │            │           │            │              │            │
│   GATHER        PLAN it     DO each    IMPROVE          CHECK           │
│   evidence      completely  task       structure         quality        │
│                                │                                        │
│                    ◄───────────┘ (loop per task)                         │
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
| Before roadmap | Gather measurements and quantitative data |
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
[research] → discuss → design → [devops] → [diagram] → distill → roadmap → execute → [refactor] → review
```

**Why each step**:

| Step | Purpose |
|------|---------|
| `research` | (Optional) Gather domain knowledge before requirements |
| `discuss` | Gather requirements - you don't know what's needed yet |
| `design` | Make architecture decisions, select technology |
| `devops` | (Optional) Platform readiness, CI/CD, infrastructure |
| `diagram` | (Optional) Visualize architecture for stakeholder communication |
| `distill` | Define acceptance tests - what does "done" look like? |
| `roadmap` | Create comprehensive plan while context is fresh |
| `execute` | Do each task with clean context |
| `refactor` | (Optional) Improve structure after each task |
| `review` | Quality gate before proceeding |

**Example Commands**:

```bash
/nw:research "authentication best practices for SaaS"
/nw:discuss "authentication requirements"
/nw:design --architecture=hexagonal
/nw:devops                                    # Platform readiness
/nw:diagram --format=mermaid --level=container # Visualize architecture
/nw:distill "user-login-story"
/nw:roadmap @solution-architect "implement authentication"
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
[research] → roadmap → execute → [refactor] → review (repeat)
```

**Why skip discovery**:

- You already understand the system
- Problem is identified
- Go straight to **measured, incremental execution**

**Example Commands**:

```bash
/nw:research "xUnit parallelization strategies"  # Optional: gather options
/nw:roadmap @solution-architect "optimize test execution time"
/nw:execute @researcher "docs/workflow/optimize-test-execution-time/steps/01-01.json"
/nw:review @software-crafter task "docs/workflow/optimize-test-execution-time/steps/02-01.json"
/nw:execute @software-crafter "docs/workflow/optimize-test-execution-time/steps/02-01.json"
# ... repeat execute → review for each task
/nw:finalize @platform-architect "optimize-test-execution-time"
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
[research] → roadmap (methodology: mikado) → execute → [refactor] → review
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
/nw:roadmap @software-crafter "replace legacy authentication"
/nw:execute @software-crafter "docs/workflow/replace-legacy-authentication/steps/01-01.json"
```

---

### JOB 4: Investigate & Fix Issue

> *"Something is broken and I need to find why"*

**Key Question**: What's the root cause?

**Sequence**:

```text
[research] → root-why → execute → [refactor] → review
```

**Minimal sequence** - focused intervention only.

**Example Commands**:

```bash
/nw:research "JWT token expiration edge cases"  # Optional: if unfamiliar with area
/nw:root-why "authentication timeout errors in production"
/nw:execute @software-crafter "fix-auth-timeout"
/nw:review @software-crafter implementation "src/auth/"
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

---

## Quick Reference Matrix

| Job | You Know What? | Sequence |
|-----|---------------|----------|
| **Greenfield** | No | [research] → discuss → design → [devops] → [diagram] → distill → roadmap → execute → [refactor] → review |
| **Brownfield** | Yes | [research] → roadmap → execute → [refactor] → review |
| **Refactoring** | Partially | [research] → mikado/roadmap → execute → [refactor] → review |
| **Bug Fix** | Yes (symptom) | [research] → root-why → execute → [refactor] → review |
| **Research** | No | research → (output informs next job) |
| **Documentation** | Varies | [research] → design → diagram |

*Note: Items in `[brackets]` are optional - use when needed.*

**Cross-wave commands** (can be used anytime):

- `research` - Gather evidence
- `diagram` - Visualize architecture
- `root-why` - Investigate issues
- `document` - DIVIO-compliant documentation

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

#### DEVOP Wave

| Job | Command | Outcome |
|-----|---------|---------|
| Platform readiness | `/nw:devops` | CI/CD and infrastructure design |
| Deployment strategy | `/nw:devops` | Production deployment plan |

#### DISTILL Wave

| Job | Command | Outcome |
|-----|---------|---------|
| Define what "done" looks like | `/nw:distill` | Acceptance tests (Given-When-Then) |

### Execution Loop Jobs

#### ROADMAP

| Job | Command | Outcome |
|-----|---------|---------|
| Plan while context is fresh | `/nw:roadmap` | Comprehensive plan |
| Capture dependencies | `/nw:roadmap` | Sequenced steps |
| Enable parallel work | `/nw:roadmap` | Independent task identification |

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
| Implement with TDD | `/nw:execute` | Test-first code |
| Refactor safely | `/nw:refactor` | Improved structure |
| Handle complex dependencies | `/nw:mikado` | Reversible change path |

#### Operations

| Job | Command | Outcome |
|-----|---------|---------|
| Validate production readiness | `/nw:deliver` | Deployment confidence |
| Archive completed work | `/nw:finalize` | Clean project closure |
| Create documentation | `/nw:document` | DIVIO-compliant docs |

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

Go straight to the **execution loop** with roadmap as the entry point.

---

## The Execution Loop (Core Workflow)

The execution loop is the workhorse of brownfield work:

```text
[research] → roadmap → execute → [refactor] → review
                          │         │
                          └────────►│ (repeat per task)
```

### Why It Works

| Step | Benefit |
|------|---------|
| **research** | (Optional) Gather evidence to inform roadmap |
| **roadmap** | Captures full plan while context is fresh |
| **execute** | Each task runs with clean context (max LLM quality) |
| **refactor** | (Optional) Improve code structure after implementation |
| **review** | Quality gate before proceeding |

### Key Principles

1. **Evidence Before Decisions**: Research when you need data to decide
2. **Atomic Tasks**: Each task is self-contained with all context embedded
3. **Clean Context**: Each execute starts fresh (no accumulated confusion)
4. **Quality Gates**: Review before moving to next task

---

## Agent Selection

For complete agent specifications and selection guidance, see the [nWave Commands Reference](../reference/nwave-commands-reference.md).

**Quick Overview**:
- **Core Wave Agents**: product-owner, solution-architect, acceptance-designer, software-crafter, platform-architect
- **Cross-Wave Specialists**: researcher, troubleshooter, data-engineer, product-discoverer, agent-builder, documentarist
- **Reviewer Agents**: Every agent has a `*-reviewer` variant for quality assurance

---

## Common Workflows

### New Feature on Existing Codebase

```bash
/nw:research "best practices for {feature-domain}"  # Optional
/nw:roadmap @solution-architect "add multi-tenant support"
# execute → review loop
```

### Performance Optimization

```bash
/nw:research "profiling techniques for {technology}"  # Optional
/nw:roadmap @solution-architect "optimize API response time"
# execute → review loop
```

### Legacy System Modernization

```bash
/nw:research "strangler fig pattern"
/nw:root-why "current system limitations"
/nw:roadmap @solution-architect "migrate to microservices"
# execute → review loop with mikado for complex refactoring
```

### Quick Bug Fix

```bash
/nw:root-why "users cannot login after password reset"
/nw:execute @software-crafter "fix-password-reset-flow"
/nw:review @software-crafter implementation "src/auth/"
```

### Pure Research Task

```bash
/nw:research "event sourcing vs CRUD for audit requirements"
# Output: docs/research/{category}/{topic}.md
# Decision: proceed with JOB 1, 2, or 3 based on findings
```

### Architecture with Visual Documentation

```bash
/nw:design --architecture=hexagonal
/nw:diagram --format=mermaid --level=container
```

### Data-Heavy Project

```bash
/nw:research "compare PostgreSQL vs MongoDB for {use-case}"
# Invoke data-engineer agent for specialized guidance
/nw:roadmap @data-engineer "implement data pipeline"
# execute → review loop
```

### Creating a New Agent

```bash
/nw:forge  # Uses agent-builder to create new agent from template
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Skip research | Decisions without evidence | Research when unfamiliar with domain |
| Monolithic tasks | Context degradation | Use roadmap for atomic tasks |
| Skip review | Quality issues propagate | Review before each execute |
| Architecture before measurement | Over-engineering | Research identifies quick wins first |
| Forward references in tasks | Tasks not self-contained | Each task must have all context embedded |

---

## Command and File Reference

For complete command specifications, agent selection, and file locations, see the [nWave Commands Reference](../reference/nwave-commands-reference.md).
