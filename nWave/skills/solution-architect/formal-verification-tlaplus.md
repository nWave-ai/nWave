---
name: formal-verification-tlaplus
description: TLA+ and PlusCal for specifying distributed system invariants. Decision heuristics for when formal verification adds value, key patterns, state explosion management, and alternatives comparison.
---

# Formal Verification with TLA+

## When to Recommend Formal Verification

### Decision Tree

```
Is the system distributed or concurrent?
|
+-- No --> Complex state machine with high failure cost?
|          +-- No --> NOT cost-effective. Use property-based testing.
|          +-- Yes --> CONSIDER TLA+
|
+-- Yes --> Consensus, coordination, or distributed transactions?
|           +-- Yes --> RECOMMEND TLA+
|           +-- No --> Could concurrency bug cause data loss or safety issues?
|                      +-- Yes --> RECOMMEND TLA+
|                      +-- No --> OFFER as option
```

### Strong Indicators (Recommend)

| Domain | Why TLA+ Adds Value | Evidence |
|--------|-------------------|----------|
| Distributed consensus (Paxos, Raft) | Subtle interleaving bugs in leader election | Raft TLA+ spec ~400 lines, found implementation bugs |
| Financial distributed transactions | Atomicity violations cause monetary loss | AWS DynamoDB replication verified |
| Leader election, distributed locking | Split-brain, deadlock, stale-lock | AWS lock manager verified |
| Eventual consistency / CRDTs | Convergence proofs required | TLA+ CRDT framework verifies SEC |
| Safety-critical state machines | Regulatory requirements | DO-178C, CENELEC recognize formal methods |
| Multi-party coordination (sagas, 2PC) | Compensation ordering, partial failure | 2PC is canonical TLA+ example |
| Data replication protocols | Ordering, consistency under failure | Elasticsearch, MongoDB, Cosmos DB verified |

### When NOT to Use

- Simple CRUD (bugs are in implementation, not design)
- Single-process without complex state machines
- Prototypes/MVPs (design will change before verification completes)
- Performance optimization (TLA+ models correctness, not performance)

### Cost-Benefit Reference

- Learning curve: 2-3 weeks to useful results (AWS engineers, all levels)
- Typical spec effort: 2-4 weeks part-time for a distributed protocol
- ROI highest when: bug cost is high, system is long-lived, protocol is novel, concurrency testing is impractical

## Core Concepts for Architects

### What TLA+ Specifies

TLA+ describes **what** a system should do (allowed behaviors), not **how** to implement it. Specifications are mathematical objects checked for correctness before any code exists.

### Safety vs. Liveness

| Property Type | Meaning | Expression | Example |
|--------------|---------|------------|---------|
| Safety | Nothing bad happens | Invariant: predicate true in every reachable state | "Two processes never hold same lock" |
| Liveness | Something good eventually happens | Temporal: `<>` (eventually), `[]<>` (infinitely often) | "Every request eventually gets response" |

Safety violations produce counterexample traces (the debugging artifact). Liveness requires fairness conditions.

### PlusCal vs. Raw TLA+

PlusCal compiles to TLA+ with programming-like syntax. Start with PlusCal for first 2-3 specs, then learn raw TLA+ for cases PlusCal cannot express.

Key PlusCal constructs: `variables` (state) | `labels` (atomic action boundaries) | `either/or` (nondeterministic choice) | `await` (blocking) | `process \in 1..N` (concurrent processes) | `fair process` (weak fairness)

Labels define concurrency granularity: everything between two labels is one atomic step. Two processes interleave only at label boundaries.

## State Explosion Management

State space grows exponentially: `(states per node)^(nodes) x (message permutations)`.

### Containment Strategies

| Strategy | Technique | Impact |
|----------|-----------|--------|
| Bound parameters | Start with 2-3 nodes, 2-4 messages | Most bugs appear at small N |
| Symmetry reduction | `SYMMETRY Permutations(Nodes)` | Up to N! reduction |
| Reduce labels | Merge labels where fine-grained atomicity unnecessary | Orders of magnitude |
| State constraints | `CONSTRAINT Len(log[n]) < MaxLogLength` | Prune uninteresting states |
| Abstraction | Model protocol not implementation (TCP -> message set) | Dramatic reduction |
| Decomposition | Multiple focused specs, not one monolith | Each independently checkable |
| Progressive refinement | 2 nodes -> 3 nodes -> add failures -> add liveness | Incremental verification |
| Simulation mode | `java -jar tla2tools.jar -simulate -depth 100` | Trades completeness for speed |

### Memory and Time Budgets

| Unique States | Expected Time | Memory | Approach |
|--------------|---------------|--------|----------|
| < 10K | Seconds | < 1 GB | Exhaustive, single thread |
| 10K - 1M | Minutes | 1-4 GB | Exhaustive, `-workers auto` |
| 1M - 100M | Hours | 4-32 GB | Exhaustive with constraints |
| 100M - 1B | Days | 32-64 GB | Large instance or simulation |
| > 1B | Weeks | 60+ GB | Simulation, TLAPS, or decompose |

### Estimation Before Running

1. Count distinct variable values in model
2. Multiply domains together for baseline
3. Start TLC with smallest parameters, observe state count
4. Extrapolate: doubling a parameter typically squares or cubes the space

## Key Specification Patterns

### Two-Phase Commit (2PC)
- Variables: rmState, tmState, tmPrepared, msgs
- Safety: no RM commits while another aborts (`Consistency`)
- State space: 3 RMs ~718 states, 5 RMs ~21,488 states
- Common mistake: not modeling RM spontaneous abort or unreliable network

### Distributed Consensus (Raft)
- Variables: currentTerm, votedFor, log, state, votesGranted, msgs
- Safety: at most one leader per term (`ElectionSafety`)
- Safety: logs with same index+term are identical (`LogMatching`)
- State space: 3 nodes, MaxTerm=2 ~10K-100K states

### Saga (Compensating Transactions)
- Variables: stepState, sagaState, compensateIdx
- Safety: steps execute in order, compensations in reverse (`OrderInvariant`)
- Safety: no completed steps remain after abort (`CompensationComplete`)
- Common mistake: not enforcing reverse compensation order

### Distributed Lock with Lease
- Variables: lockHolder, leaseExpiry, clock, nodeState
- Safety: at most one holder (`MutualExclusion`)
- Models crash (node loses awareness) and lease expiry
- Common mistake: not distinguishing server-side lock state from node belief

### CRDT Convergence (G-Counter)
- Variables: counters (vector per node)
- Safety: counters monotonically non-decreasing
- Liveness: all nodes eventually converge after merge
- Common mistake: merge not commutative, associative, and idempotent

## Alternatives Comparison

| Tool | Best For | Learning | Distributed Systems | Temporal Properties |
|------|----------|----------|--------------------|--------------------|
| TLA+/PlusCal | Distributed protocols, consensus | 2-3 weeks | Excellent | Native |
| Alloy | Data models, structural properties | 1-2 weeks | Adequate | Limited (Alloy 6) |
| Property-Based Testing | Implementation correctness | Hours-days | With stateful testing | None |
| XState/Statecharts | UI workflows, single-process | Days | Not applicable | None |
| Session Types/Scribble | Communication patterns | Moderate | Good (message patterns) | Implicit |
| TLAPS (proofs) | Critical certification | Months | Excellent | Full |

### Combined Workflow (TLA+ + PBT)

1. Write TLA+ spec during DESIGN wave; identify invariants
2. Model-check with TLC to verify design
3. Implement code during DELIVER wave
4. Reuse TLA+ invariants as PBT properties
5. PBT verifies implementation conforms to verified design

## Architecture Decision Record Template

```markdown
## Decision: Use TLA+ for [Component Name]

### Context
[Component] implements [protocol] with [N] participants
and [concurrency/distribution characteristics].

### Problem
Informal reasoning about [failure/interleaving scenario]
is insufficient because [reason].

### Decision
Formally specify [component] in TLA+/PlusCal and verify:
- Safety: [specific invariants]
- Liveness: [specific temporal properties]

### Model Parameters
- Nodes: [2-3 for initial verification]
- Messages: [bounded to N]
- Failure modes: [crash, partition, message loss]

### Estimated Effort
- Specification: [1-2 weeks]
- Model checking: [hours to days]

### Not Modeling (out of scope)
- [performance, serialization, UI, etc.]
```

## Architect's Checklist

1. Identify components with concurrency, distribution, or complex state machines
2. Determine safety properties (what must NEVER happen)
3. Determine liveness properties (what must EVENTUALLY happen)
4. Estimate model parameters and state space
5. Assess cost-effectiveness vs. alternatives (decision tree above)
6. Document decision in ADR with specific invariants and properties
7. Scope verification: focused specs per subsystem, not one monolith

## Industry Precedent

| Organization | Systems Verified | Outcome |
|-------------|-----------------|---------|
| AWS | 14 projects across 10 systems (DynamoDB, S3, EBS) | Found subtle bugs in every system; management actively encourages adoption |
| Azure Cosmos DB | All 5 consistency levels | Specs became authoritative reference, replaced ambiguous docs |
| MongoDB | Replication, reconfiguration, transactions | Logless reconfig deployed since 4.4, no protocol bugs |
| Elasticsearch | Cluster coordination, data replication | 4 TLA+ specs + Isabelle proofs, open-sourced |
| CockroachDB | Transaction layer | TLA+ specs in repository under docs/tla-plus/ |
