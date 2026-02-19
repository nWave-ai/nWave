# Jobs To Be Done Guide: nWave Framework

## Overview

This guide uses the **Outcome Driven Innovation (ODI)** framework to help you understand when and how to use the nWave agentic system based on your specific job context.

---

## The 6-Wave Sequence

The framework operates as a **sequential pipeline of 6 waves**:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                     THE 6-WAVE SEQUENCE                                 │
│                                                                         │
│   discover ──→ discuss ──→ design ──→ devops ──→ distill ──→ deliver    │
│      │           │           │          │          │           │        │
│   VALIDATE    WHAT are    HOW should  PLATFORM  WHAT does   BUILD &    │
│   the problem the needs?  it work?    ready?    "done"      SHIP it    │
│                                                 look like?             │
└─────────────────────────────────────────────────────────────────────────┘
```

**Skip waves you don't need** — brownfield work may start at `deliver`, bug fixes at `root-why` + `execute`.

### What `/nw:deliver` Automates

`/nw:deliver` orchestrates the full inner loop with DES (Deterministic Execution System):

```text
/nw:deliver = roadmap → execute → refactor → review → mutation-test → finalize
```

### Manual Inner Loop (Learning Mode)

If you are still learning the framework, run each step yourself instead of `/nw:deliver`:

```bash
/nw:execute @software-crafter "implement login endpoint" # Execute one task
/nw:refactor                                             # Improve structure
/nw:review @software-crafter task "implement login endpoint" # Quality check
/nw:mutation-test                            # Validate test effectiveness
/nw:finalize                                 # Archive and clean up
```

This gives you hands-on understanding of each step without DES orchestration. Graduate to `/nw:deliver` when the pattern feels natural.

**Cross-wave commands** (can be used anytime): `research`, `diagram`, `root-why`, `document`, `refactor`, `mikado`

---

## The Research Step (Cross-Wave)

Research is not a fixed step in a sequence - it's a capability you invoke **whenever you need evidence**:

| When to Research | Purpose |
|------------------|---------|
| Before discover | Understand market before validation |
| Before discuss | Understand domain before gathering requirements |
| Before design | Evaluate technology options with evidence |
| Before deliver | Gather measurements and quantitative data |
| When stuck | Gather information to unblock decisions |

**Example Commands**:

```bash
# Domain research before requirements
/nw:research "multi-tenant architecture patterns"

# Technology evaluation
/nw:research "compare OAuth2 providers for enterprise"

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
[discover] → discuss → design → devops → distill → deliver
```

**Why each step**:

| Step | Purpose |
|------|---------|
| `discover` | (Optional) Validate problem exists, market research |
| `discuss` | Gather requirements - you don't know what's needed yet |
| `design` | Make architecture decisions, select technology |
| `devops` | Platform readiness, CI/CD, infrastructure |
| `distill` | Define acceptance tests - what does "done" look like? |
| `deliver` | TDD implementation, execution, and delivery |

**Example Commands**:

```bash
/nw:research "authentication best practices for SaaS"
/nw:discuss "authentication requirements"
/nw:design --architecture=hexagonal
/nw:devops
/nw:diagram --format=mermaid --level=container
/nw:distill "user-login-story"
/nw:deliver
```

---

### JOB 2: Improve Existing System (Brownfield)

> *"I know what needs to change in our system"*

**Key Question**: How do I change it safely and incrementally?

**Sequence**:

```text
[research] → deliver
```

**Why skip discovery**: You already understand the system, problem is identified. Go straight to delivery.

**Example Commands**:

```bash
/nw:research "xUnit parallelization strategies"  # Optional: gather options
/nw:deliver
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
[research] → deliver
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
/nw:deliver
```

---

### JOB 4: Investigate & Fix Issue

> *"Something is broken and I need to find why"*

**Key Question**: What's the root cause?

**Sequence**:

```text
[research] → root-why → execute → review
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
| **Greenfield** | No | [discover] → discuss → design → devops → distill → deliver |
| **Brownfield** | Yes | [research] → deliver |
| **Refactoring** | Partially | [research] → mikado → deliver |
| **Bug Fix** | Yes (symptom) | [research] → root-why → execute → review |
| **Research** | No | research → (output informs next job) |
| **Documentation** | Varies | [research] → document |

*Note: Items in `[brackets]` are optional - use when needed.*

---

## Granular Jobs By Phase

This section breaks down what specific job each wave command fulfills.

### DISCOVER Wave

| Job | Command | Outcome |
|-----|---------|---------|
| Validate problem exists | `/nw:discover` | Evidence-based validation |
| Market research | `/nw:discover` | Competitive analysis |

### DISCUSS Wave

| Job | Command | Outcome |
|-----|---------|---------|
| Capture stakeholder needs | `/nw:discuss` | Requirements documented |
| Align business and tech | `/nw:discuss` | Shared understanding |
| Define acceptance criteria | `/nw:discuss` | Testable requirements |

### DESIGN Wave

| Job | Command | Outcome |
|-----|---------|---------|
| Choose architecture pattern | `/nw:design` | Architecture decision |
| Select technology stack | `/nw:design` | Technology rationale |
| Define component boundaries | `/nw:design` | Clear module separation |
| Communicate architecture visually | `/nw:diagram` | Stakeholder-ready diagrams |

### DEVOPS Wave

| Job | Command | Outcome |
|-----|---------|---------|
| Platform readiness | `/nw:devops` | CI/CD and infrastructure design |
| Deployment strategy | `/nw:devops` | Production deployment plan |

### DISTILL Wave

| Job | Command | Outcome |
|-----|---------|---------|
| Define what "done" looks like | `/nw:distill` | Acceptance tests (Given-When-Then) |

### DELIVER Wave

| Job | Command | Outcome |
|-----|---------|---------|
| Plan and execute with TDD | `/nw:deliver` | Working, tested code |
| Track progress | `/nw:deliver` | TODO → IN_PROGRESS → DONE |
| Quality gates | `/nw:deliver` | Review at each step |

### Cross-Wave Jobs

#### Research & Investigation

| Job | Command | Outcome |
|-----|---------|---------|
| Gather evidence before deciding | `/nw:research` | Cited findings |
| Evaluate technology options | `/nw:research` | Comparison analysis |
| Understand unfamiliar domain | `/nw:research` | Knowledge base |
| Find root cause (not symptoms) | `/nw:root-why` | 5 Whys analysis |
| Understand failure patterns | `/nw:root-why` | Multi-causal map |

#### Development (standalone)

| Job | Command | Outcome |
|-----|---------|---------|
| Execute single task | `/nw:execute` | Clean context per task |
| Refactor safely | `/nw:refactor` | Improved structure |
| Handle complex dependencies | `/nw:mikado` | Reversible change path |
| Expert critique | `/nw:review` | Domain-specific feedback |

#### Operations

| Job | Command | Outcome |
|-----|---------|---------|
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

## When to Skip Waves

Skip early waves when:

- You already understand the domain → skip `discover`, `discuss`
- Architecture is established → skip `design`
- Platform is ready → skip `devops`
- Acceptance tests exist → skip `distill`
- Go straight to `/nw:deliver`

---

## Agent Selection

For complete agent specifications and selection guidance, see the [nWave Commands Reference](../reference/nwave-commands-reference.md).

**Quick Overview**:
- **Core Wave Agents**: product-discoverer, product-owner, solution-architect, platform-architect, acceptance-designer, software-crafter
- **Cross-Wave Specialists**: researcher, troubleshooter, data-engineer, documentarist, agent-builder
- **Reviewer Agents**: Every agent has a `*-reviewer` variant for quality assurance

---

## Common Workflows

### Full Greenfield Feature

```bash
/nw:discover "feature market research"
/nw:discuss "feature requirements"
/nw:design --architecture=hexagonal
/nw:devops
/nw:distill "acceptance tests"
/nw:deliver
```

### New Feature on Existing Codebase

```bash
/nw:research "best practices for {feature-domain}"  # Optional
/nw:deliver
```

### Legacy System Modernization

```bash
/nw:research "strangler fig pattern"
/nw:root-why "current system limitations"
/nw:deliver
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

### Creating a New Agent

```bash
/nw:forge  # Uses agent-builder to create new agent from template
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Skip research | Decisions without evidence | Research when unfamiliar with domain |
| Skip distill | No definition of "done" | Define acceptance tests before deliver |
| Monolithic execution | Context degradation | Let deliver break work into atomic tasks |
| Skip review | Quality issues propagate | Review at each step |
| Architecture before research | Over-engineering | Research identifies quick wins first |

---

## Command and File Reference

For complete command specifications, agent selection, and file locations, see the [nWave Commands Reference](../reference/nwave-commands-reference.md).
