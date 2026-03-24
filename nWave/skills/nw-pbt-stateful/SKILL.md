---
name: nw-pbt-stateful
agent: nw-functional-software-crafter
description: "Stateful property-based testing patterns, model-based testing, and anti-patterns. Load when testing stateful systems, mutable state sequences, or designing model-based property tests."
user-invocable: false
disable-model-invocation: true
---

# Stateful PBT

Stateful property-based testing for systems with mutable state. Language-agnostic concepts; load language skills for framework syntax.

## When to Use Stateful vs Stateless PBT

```
Is the system under test a pure function?
  Yes -> Use stateless PBT (pbt-fundamentals skill)
  No -> Does it have mutable state that affects behavior?
    Yes -> Does the state change through a sequence of operations?
      Yes -> Use stateful PBT (this skill)
      No  -> Use stateless PBT with setup/teardown
    No  -> Use stateless PBT
```

Use stateful PBT for: databases | APIs | caches | queues | state machines | protocols | connection pools | file systems.

## Core Concepts

### The Model

Simplified representation of system's expected state. Drives test generation and verification.

Rules for model design:
- Simpler than system under test (key-value store model is just a dict)
- Captures observable behavior, not implementation details
- Pure -- no side effects in model code
- Source of authority during both generation and shrinking

### Commands

Each command defines four things:

| Component | Purpose | When It Runs |
|-----------|---------|-------------|
| Precondition | Is this command valid in current state? | Generation + shrinking |
| Execution | Run operation on real system | Execution phase only |
| State transition | Update model | Both phases |
| Postcondition | Does real result match model? | Execution phase only |

### Two-Phase Execution

**Phase 1 -- Generation (abstract)**: Build command sequence using model only. No real system code runs. Return values are symbolic placeholders.

**Phase 2 -- Execution (concrete)**: Run commands against real system. Replace symbolic values with real values. Check postconditions after each step.

### Symbolic References

During generation, commands returning values produce symbolic placeholders, resolved to real values during execution.

Rule: Treat all values from real system as opaque in model code. Store and pass them, never inspect during generation.

## Command Design Patterns

### Basic CRUD Model

```
Model: dictionary/map
Commands: create (adds to model + system), read (compare), update (modify both), delete (remove from both)
Invariant: model size == system size
```

### Resource Lifecycle

```
Model: set of active resources
Commands: acquire (add to set), use (precondition: in set), release (remove from set)
Invariant: no use-after-release
```

### Transaction Model

```
Model: committed state + pending state + in_transaction flag
Commands: begin, write (update pending), commit (pending->committed), rollback (discard pending)
Invariant: reads outside transaction see committed state only
```

### CRUD Command Structure (Pseudocode)

```pseudocode
command CreateItem:
  Precondition:
    model.count < MAX_ITEMS
  Execution:
    result = system.create(random_item())
  StateTransition:
    model.items[result.id] = item
  Postcondition:
    assert result.id in system.list_all()
    assert model.count == system.count()
```

## Linearizability Testing

Tests that concurrent execution is equivalent to some valid sequential execution.

1. Define sequential model (same as above)
2. Generate sequential prefix to establish state
3. Generate parallel command branches
4. Execute branches concurrently
5. Check if results match any valid sequential interleaving

Supported by: PropEr (`parallel_commands`) | CsCheck (`SampleConcurrent`) | Hedgehog | fast-check (`scheduler`) | ScalaCheck.
NOT supported by: Hypothesis.

Use linearizability testing only when concurrent correctness is primary risk. Sequential stateful testing catches most bugs at lower cost.

## Anti-Patterns (8 Documented)

### 1. Model Too Complex
Making model as complex as system. If model bugs mirror system bugs, test is worthless.
**Fix**: Model the what (interface contract), not the how (implementation).

### 2. Insufficient Action Coverage
Not monitoring which commands execute. Tests "pass" while never exercising critical paths.
**Fix**: Collect distribution statistics. Weight commands to ensure coverage.

### 3. Weak Preconditions
Missing preconditions allowing invalid commands, producing spurious failures.
**Fix**: Preconditions should precisely capture system's documented contract.

### 4. State Explosion
Too many state variables creating combinatorial explosion (N booleans = 2^N states).
**Fix**: Start minimal. Add complexity incrementally. Use preconditions to prune unreachable states.

### 5. Side Effects in Model Code
I/O or external mutations in preconditions or state transitions.
**Fix**: Model code must be pure. Only command execution touches real system.

### 6. Inspecting Opaque Values During Generation
Pattern-matching symbolic placeholders without real values yet.
**Fix**: Never inspect values from real system in `next_state`. Store and pass, don't transform.

### 7. Not Shrinking-Aware
Commands that work during generation but break during shrinking due to incomplete preconditions.
**Fix**: Every command using a resource must have precondition verifying resource exists in model.

### 8. Testing Implementation Details
Modeling internal structure (e.g., tree rotations) instead of observable behavior.
**Fix**: Model the interface contract. For sorted set, model is sorted list.

## Debugging Failed Stateful Tests

### Reading a Failing Command Sequence

When a stateful test fails, framework reports command sequence and failing postcondition. Read as a story:

1. **Identify failing command**: Last command is where postcondition failed
2. **Trace model state**: Walk through each command, tracking model expectations
3. **Find divergence**: Where does real system diverge from model?
4. **Check if test bug or system bug**: Is model wrong, or system wrong?

### Common Failure Patterns

| Symptom | Likely Cause |
|---------|-------------|
| Failure only with 3+ commands | State-dependent bug triggered by specific sequence |
| Failure involves create-then-use | Resource lifecycle bug or symbolic reference issue |
| Non-deterministic failures | Race condition or external dependency |
| Failure disappears after shrinking removes commands | Missing precondition |
| Model and system disagree on count/size | Off-by-one or missing cleanup |

### Shrinking Interpretation

Shrunk sequence is minimal reproduction. If shrinking removes a command and test still fails, that command was irrelevant. Remaining commands are all necessary.

If shrinking produces unexpectedly long sequence, check for missing preconditions -- shrinker can't remove commands when removal would violate later preconditions.

If minimal failing sequence needs 6+ commands, shrinking removed many dependencies -- check for missing preconditions.

## Oracle Design

### Building a Model

1. Start with simplest possible data structure (usually dict or list)
2. Add only state needed to express postconditions
3. Keep model transitions obvious and trivial
4. If model gets complex, you may be modeling too much

### Handling Non-Determinism

- **Acceptable non-determinism** (UUID generation): Track generated values in model, compare by stored reference
- **Timing-dependent behavior**: Model set of acceptable outcomes, assert real result is in that set
- **Random internal choices**: Use seeded system, or assert invariants rather than exact values

### Model Completeness

Model doesn't need to capture every system behavior. Focus on:
- Operations you want to test
- State those operations depend on
- Postconditions that verify correctness

A partial model testing 5 operations well beats a complete model testing 20 operations poorly.
