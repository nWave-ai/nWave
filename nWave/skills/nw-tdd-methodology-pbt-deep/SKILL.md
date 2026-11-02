---
name: nw-tdd-methodology-pbt-deep
description: Deep property-based-testing mechanics (Hebert) - stateful PBT command-precondition anti-patterns (A13/P6), the four property-finding strategies, the two shrinking mechanisms, and targeted/search-based PBT with its hard limitations
user-invocable: false
disable-model-invocation: true
---

# Property-Based Testing — Deep Mechanics (Hebert)

**Trigger**: writing a property-based test and needing the deep mechanics — finding a property when none is obvious, stateful-PBT preconditions, shrinking, or targeted/search-based PBT.

## PBT Anti-Patterns

- **A13: Stateful PBT without command-precondition encoding** — encode command validity in the chosen framework's state-machine precondition mechanism, not only inside the generator. `precondition/2` is PropEr syntax; use the native equivalent on other stacks. Shrinking must preserve command validity, or counter-examples can point at ghost bugs (Hebert ch.10 bookstore case study).

## PBT Priorities

- **P6: Stateful command preconditions** — When the SUT is a state machine (per Hebert ch.11 framing: model-shape-is-state-machine, not user-perceived states), encode command validity through the framework-native precondition mechanism (`precondition/2` in PropEr). Verify generated and shrunk traces remain valid. Without P6, A13 fires.

## PBT Thinking — Property-Finding Strategies

### Hebert's four strategies (ch.3)

When you don't know what property to write, walk Hebert's ch.3 catalogue first. These are the **Tier 1 (Hebert ch.3 core)** strategies:

- **Modeling** — SUT vs simpler-but-obviously-correct reference (maps to skill's "Oracle" pattern). Build a simpler reference implementation, compare outputs.
- **Generalizing example tests** — parameterizing existing example tests with strategies; take a known correct answer, embed it in the input, predict where it should appear in the output.
- **Invariants** — output property holds regardless of input (maps to skill's "Invariant" pattern). Combine multiple — a single invariant is rarely enough.
- **Symmetric properties** — reversible sequence of actions: applying both yields the original input (maps to skill's "Roundtrip" pattern, e.g., encode/decode, push/pop).

Other patterns commonly cited (Commutativity, Idempotence, Hard-to-compute-easy-to-verify, Induction, Metamorphic relation, Test oracle as standalone) are **Tier 2 (Link extension)**, not Hebert. Keep them as a supplemental pattern library; Tier 1 is the minimum.

## Shrinking — Hebert's Two Mechanisms (ch.7)

Hebert ch.7 documents only TWO shrinking mechanisms:

- `?SHRINK(Generator, FallbackGenerators)` — re-center on a smaller value. Provides simpler-but-domain-relevant alternative generators used during shrinking. Hypothesis equivalent: explicit `min_value=`, `min_size=`, or `st.from_regex` constraining to the domain's natural range.
- `?LETSHRINK([Generators])` — divide-and-shrink each independently. Use to enable structural pruning of recursive generators; `?LET` shrinks contents but not structure.

Any other shrinking mechanism mentioned elsewhere (e.g., adaptive shrinking, integrated shrinkers as a separate concept) is **community-extension, not core Hebert**.

## Targeted PBT (Hebert ch.8)

Search-based PBT replaces random search with simulated annealing: report a *utility value* per test case, and the framework biases the next input toward inputs that improved the utility.

- `?USERNF(Generator, Next)` custom-neighbor function — controls how the search moves between samples. Hebert ch.8 sidebar "Considering Temperature" reports temperature-scaled custom neighbors are *"almost fifty times more effective"* than the same neighbor without temperature on tree-skewing search. The 50× claim is conditional on temperature usage, not on raw custom neighbors.
- `?EXISTS(Vars, Generator, Property)` and `?NOT_EXISTS(Vars, Generator, Property)` — search-macro family underlying `?FORALL_TARGETED`.

**Two hard limitations** (Hebert ch.8):

1. No recursive generators with `?LAZY` under targeted (infinite loops).
2. No `collect/2` / `aggregate/2` statistics under targeted (instrumentation incompatible with the search loop).

**Tuning parameter** (not a limitation): default search budget for targeted properties is 1000 steps (vs 100 for regular `?FORALL`); configurable via `-s` / `--search_steps`.

Hypothesis equivalent: `target()` registers a quantity; the engine biases toward maximising it. Same limitations apply in spirit (recursive strategies + statistics interplay poorly with `target()`).
