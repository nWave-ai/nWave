---
name: residuality-theory
description: Residuality Theory methodology for designing architectures that survive unknown stresses. Load when designing high-uncertainty, mission-critical, or complex socio-technical systems.
---

# Residuality Theory

Complexity science-based approach to designing architectures that survive unknown future stresses. Source: Barry M. O'Reilly (Former Microsoft Chief Architect, PhD Complexity Science).

Core paradigm: "Architectures should be trained, not designed."

## When to Apply

**Use for**: High-uncertainty environments, mission-critical systems, complex socio-technical systems, innovative products with uncertain adoption, rapidly evolving markets.

**Skip for**: Well-understood stable domains, short-lived MVPs/prototypes, simple few-component systems, resource-constrained environments unable to invest in iterative stress testing.

## Three Core Concepts

### 1. Stressors
Unexpected events challenging system operation. Categories: technical (failures, scaling, breaches), business model (pricing shifts, competitive disruption), economic (funding changes, market crashes), organizational (restructuring, skill gaps), regulatory (compliance changes), environmental (infrastructure failures).

Brainstorm extreme and diverse stressors. Goal is discovery, not risk assessment.

### 2. Residues
Design elements surviving after system breakdown under stress. Ask: "What's left of our architecture when [stressor] hits?"

Example -- e-commerce under payment outage: residue is browsing, cart, wishlist. Lost: checkout, payment. Residuality-informed design: allow "reserve order, pay later" to preserve more functionality.

### 3. Attractors
States complex systems naturally tend toward under stress. Often differ from designed intent. Discovered through stress testing, not predicted from requirements.

Example -- social media under growth stress: designed behavior is proportional scaling, but actual attractor is read-heavy CDN mode (reads survive, writes queue/fail). Design for this attractor.

## Process

### Step 1: Create Naive Architecture
Straightforward solution for functional requirements. No speculative resilience. Document as baseline.

### Step 2: Simulate Stressors
Brainstorm 20-50 stressors across all categories. Include extreme scenarios. Engage domain experts. Prioritize by impact (not probability).

### Step 3: Uncover Attractors
Walk through each stressor with domain experts. Ask: "What actually happens?" Identify emergent behaviors. Recognize cross-stressor patterns.

### Step 4: Identify Residues
For each attractor: which components remain functional? What is critical vs non-critical? What dependencies only appear under stress?

### Step 5: Modify Architecture
Reduce coupling, add degradation modes, introduce redundancy, apply resilience patterns (circuit breakers, queues, caching). Target coupling ratio < 2.0.

### Step 6: Empirical Validation
Generate second (different) stressor set. Apply to both naive and modified architectures. Modified must survive more unforeseen stressors. Prevents overfitting.

## Practical Tools

### Incidence Matrix
Rows: stressors. Columns: components. Mark cells where stressor affects component. Reveals: vulnerable components (high column count), high-impact stressors (high row count), coupling indicators (stressors affecting multiple components).

### Adjacency Matrix
Rows/columns: components. Mark direct connections. Coupling ratio = K/N (connections/components). Target: < 1.5 (loose), 1.5-3.0 (moderate), > 3.0 (tight, high cascade risk).

### Contagion Analysis
Model as directed graph. Simulate component failure. Trace cascade. Identify SPOFs. Add circuit breakers, timeouts, fallbacks.

### Architectural Walking
Select stressor, walk system behavior step-by-step with team, identify attractors/residues, propose modification, re-walk to validate, repeat.

## Design Heuristics

1. **Optimize for criticality, not correctness**: Prioritize ability to reconfigure over perfect spec adherence
2. **Embrace strategic failure**: Some parts fail so critical parts survive
3. **Solve random problems**: Diverse stress scenarios create more robust architectures than optimizing for predicted scenarios
4. **Minimize connections**: Default to loosely-coupled; tight coupling only when functionally essential
5. **Design for business model attractor**: Understand how revenue/cost constraints shape behavior under stress
6. **Train through iteration**: Iterative stress-test-modify beats upfront comprehensive planning
7. **Document stress context**: ADRs include stressor analysis and resilience rationale

## Integration with Other Practices

- **DDD**: Stressor analysis deepens domain understanding; stress Event Storming reveals richer bounded context boundaries
- **Microservices**: Incidence matrix validates service boundaries (low shared stressor impact = good boundaries)
- **Event-Driven**: Async communication naturally reduces coupling (Residuality goal)
- **Chaos Engineering**: Stressor brainstorming feeds chaos experiment design
- **ADRs**: Include stressor analysis, attractors discovered, resilience rationale

## Differentiation from Risk Management

Traditional risk management predicts and prevents specific failures. Residuality Theory designs for survival and reconfiguration against any stress. Question shifts from "What risks should we prepare for?" to "What happens when ANY stress hits?"
