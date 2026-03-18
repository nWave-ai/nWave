---
name: nw-stress-analysis
description: Advanced architecture stress analysis methodology for designing systems that survive unknown stresses. Load when --residuality flag is used or when designing high-uncertainty, mission-critical systems.
disable-model-invocation: true
---

# Advanced Architecture Stress Analysis

Complexity science-based approach for architectures surviving unknown future stresses. Based on residuality theory by Barry M. O'Reilly (Former Microsoft Chief Architect, PhD Complexity Science).

Core paradigm: "Architectures should be trained, not designed."

## When to Apply

**Use for**: high-uncertainty environments | mission-critical systems | complex socio-technical systems | innovative products | rapidly evolving markets

**Skip for**: well-understood stable domains | short-lived MVPs | simple few-component systems | resource-constrained environments

## Three Core Concepts

### 1. Stressors
Unexpected events challenging operation. Categories: technical (failures, scaling, breaches) | business model (pricing shifts, competitive disruption) | economic (funding, market crashes) | organizational (restructuring, skill gaps) | regulatory (compliance changes) | environmental (infrastructure failures)

Brainstorm extreme and diverse. Goal = discovery, not risk assessment.

### 2. Residues
Design elements surviving after breakdown. Ask: "What's left when [stressor] hits?"

Example -- e-commerce under payment outage: residue = browsing, cart, wishlist. Lost: checkout, payment. Stress-informed: allow "reserve order, pay later."

### 3. Attractors
States systems naturally tend toward under stress. Differ from designed intent. Discovered through testing, not predicted.

Example -- social media under growth: designed = proportional scaling, actual attractor = read-heavy CDN mode (reads survive, writes queue/fail). Design for this.

## Process

### Step 1: Create Naive Architecture
Straightforward solution for functional requirements. No speculative resilience. Document as baseline.

### Step 2: Simulate Stressors
Brainstorm 20-50 across all categories. Include extremes. Engage domain experts. Prioritize by impact (not probability).

### Step 3: Uncover Attractors
Walk each stressor with experts. Ask "What actually happens?" Identify emergent behaviors. Recognize cross-stressor patterns.

### Step 4: Identify Residues
Per attractor: which components remain? Critical vs non-critical? Stress-only dependencies?

### Step 5: Modify Architecture
Reduce coupling, add degradation modes, introduce redundancy, apply resilience patterns (circuit breakers, queues, caching). Target coupling ratio < 2.0.

### Step 6: Empirical Validation
Generate second (different) stressor set. Apply to both naive and modified. Modified must survive more unforeseen stressors. Prevents overfitting.

## Practical Tools

### Incidence Matrix
Rows: stressors. Columns: components. Mark affected cells. Reveals: vulnerable components (high column count) | high-impact stressors (high row count) | coupling indicators.

### Adjacency Matrix
Rows/columns: components. Mark direct connections. Coupling ratio = K/N. Target: <1.5 (loose) | 1.5-3.0 (moderate) | >3.0 (tight, cascade risk).

### Contagion Analysis
Model as directed graph. Simulate failure. Trace cascade. Identify SPOFs. Add circuit breakers, timeouts, fallbacks.

### Architectural Walking
Select stressor, walk behavior step-by-step with team, identify attractors/residues, propose modification, re-walk to validate, repeat.

## Design Heuristics

1. **Optimize for criticality, not correctness**: prioritize reconfiguration over perfect spec adherence
2. **Embrace strategic failure**: some parts fail so critical parts survive
3. **Solve random problems**: diverse scenarios create more robust architectures than predicted-scenario optimization
4. **Minimize connections**: default loosely-coupled; tight only when essential
5. **Design for business model attractor**: how revenue/cost constraints shape behavior under stress
6. **Train through iteration**: iterative stress-test-modify beats upfront planning
7. **Document stress context**: ADRs include stressor analysis and resilience rationale

## Integration with Other Practices

- **DDD**: stressor analysis deepens domain understanding; stress Event Storming reveals richer bounded contexts
- **Microservices**: incidence matrix validates service boundaries (low shared stressor impact = good)
- **Event-Driven**: async communication naturally reduces coupling
- **Chaos Engineering**: stressor brainstorming feeds chaos experiment design
- **ADRs**: include stressor analysis, attractors, resilience rationale

## Differentiation from Risk Management

Traditional: predict and prevent specific failures. This: design for survival against any stress. Question shifts from "What risks to prepare for?" to "What happens when ANY stress hits?"
