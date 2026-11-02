---
name: nw-stress-analysis
description: Advanced architecture stress analysis methodology for designing systems that survive unknown stresses. Load on its semantic trigger — external/nondeterministic dependency, recovery/retry/compensation/degradation, contagion, infrastructure/substrate uncertainty, high-uncertainty socio-technical/business boundary — or on explicit --residuality (force-on).
user-invocable: false
---

# Advanced Architecture Stress Analysis

Complexity science-based approach for architectures surviving unknown future stresses. Based on residuality theory by Barry M. O'Reilly (Former Microsoft Chief Architect, PhD Complexity Science) — primary sources and the synthesis boundary: ADR-SSOT-002 §6a.

Core paradigm: "Architectures should be trained, not designed."

## When to Apply

Apply only on a semantic trigger, never as default ceremony: an external/
nondeterministic dependency; recovery/retry/compensation/degradation;
contagion across components; infrastructure/substrate uncertainty; a
high-uncertainty socio-technical/business boundary; or explicit
`--residuality` (force-on).

**Skip for**: stable, simple targets where none of the triggers above fire.

**Role application**: apply only the steps inside the invoking role's owned lane.
"Document" and "modify the architecture" mean supplying stressor rows and
resilience rationale as semantic inputs to that role's design or
operational authority; never edit a brief, ADR or Markdown file directly. Resilience
pattern and infrastructure selection (Step 5, contagion fixes) belongs to the
role that owns that infrastructure. A domain-only role contributes the Algebra
Bridge rows for its own observations — preserved observation, allowed
degradation, forbidden outcome — and returns any needed pattern or
infrastructure change to its owner instead of choosing it. A reviewer judges
these rows within its review lane and reports gaps as findings; it authors none.

### Stressor derivation (mechanical entry path)

A stressor is the negation of a declared assumption. Derive the stressor
list by enumerating the model's declared assumptions (fairness, atomic
steps, closed types) and negating each -- no creativity required. The
residue is measured by which laws fall after negation, and a tool answers
that. The only irreducibly human step is deciding which stressors matter
economically. Finds structural incoherence, never temporal holes -- a
temporal gap needs the model checker (`nw-review` design-review question
set, T5), not stressor negation.

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
Brainstorm the smallest diverse set that covers the categories, under an explicit budget (time-box or count agreed up front). Include extremes. Engage domain experts. Prioritize by impact, not probability. Expand only when a new stressor yields a genuinely new residue/attractor — stop once additions repeat known findings. No fixed quota.

### Step 3: Uncover Attractors
Walk each stressor with experts. Ask "What actually happens?" Identify emergent behaviors. Recognize cross-stressor patterns.

### Step 4: Identify Residues
Per attractor: which components remain? Critical vs non-critical? Stress-only dependencies?

### Step 5: Modify Architecture
Reduce coupling, add degradation modes, introduce redundancy, apply resilience patterns (circuit breakers, queues, caching) only where the residues found justify them — no universal threshold or default pattern; the fit is evidenced per system.

### Step 6: Empirical Validation
Generate a second, unseen stressor set. Apply to both naive and modified. Modified must survive more unforeseen stressors — this evidences generalization, prevents overfitting to the discovery set, and is never skipped.

## Practical Tools

### Incidence Matrix
Rows: stressors. Columns: components. Mark affected cells. Reveals vulnerable components (high column count), high-impact stressors (high row count) and coupling indicators. Not a new persisted artifact — a working aid folded into the existing design authority (heuristic 7).

### Adjacency Matrix
Rows/columns: components. Mark direct connections. Coupling ratio = K/N is a relative indicator across this system's own stressor runs, not a universal threshold — compare naive vs modified architecture, never against a fixed cross-system number.

### Contagion Analysis
Model as directed graph. Simulate failure. Trace cascade. Identify SPOFs. Add circuit breakers, timeouts, fallbacks.

### Architectural Walking
Select stressor, walk behavior step-by-step with team, identify attractors/residues, propose modification, re-walk to validate, repeat.

## Design Heuristics

1. **Correctness and criticality are complementary, not alternatives**: the accepted observable contract must hold, and the system must reconfigure toward what matters most when it cannot hold everything — optimize for both, never trade one for the other
2. **Embrace strategic failure**: some parts fail so critical parts survive
3. **Solve random problems**: diverse scenarios create more robust architectures than predicted-scenario optimization
4. **Minimize connections**: default loosely-coupled; tight only when essential
5. **Design for business model attractor**: how revenue/cost constraints shape behavior under stress
6. **Train through iteration**: iterative stress-test-modify beats upfront planning
7. **Document stress context**: the existing design authority (ADR-SSOT-002 §6a) carries the owning role's stressor analysis and resilience rationale — no separate stressor field or matrix artifact

## Integration with Other Practices

- **DDD**: stressor analysis deepens domain understanding; stress Event Storming reveals richer bounded contexts
- **Microservices**: incidence matrix validates service boundaries (low shared stressor impact = good)
- **Event-Driven**: async communication naturally reduces coupling
- **Chaos Engineering**: stressor brainstorming feeds chaos experiment design
- **ADRs**: include stressor analysis, attractors, resilience rationale

## Algebra Bridge (ADR-SSOT-002 §6a)

Residuality discovers plausible behavior under uncertainty; algebra
(`nw-algebraic-design-protocol`) owns observations, equality and laws within
and across the residues found here. Per stressor `s`, a residue names its
row: `stressor | preserved observation | allowed degradation | forbidden
outcome | recovery | boundary`. The cross-residue kernel is the NAMED set of
properties intentionally required across the selected residues — never a
blind intersection. A transformation between residues is a
structure-preserving morphism/refactoring only when its named preservation
map is stated; partial preservation is controlled degradation; a changed
user observation is a product/design change owned by its SSOT; absent
preservation is replacement, not refactoring. Correctness of the accepted
contract and criticality across stressors are complementary outcomes, never
alternatives. Keep rows in their durable design authority and derive tests from
them — no new field or persisted matrix. On the trigger, load `nw-algebraic-design-protocol`
alongside this skill.

## Differentiation from Risk Management

Traditional: predict and prevent specific failures. This: discover candidate residues under a diverse, budgeted stressor set and validate them against a second, unseen set — evidence of broader survival, never a guarantee against any stress. Question shifts from "What risks to prepare for?" to "What happens when this stressor hits, and does the residue generalize?"
