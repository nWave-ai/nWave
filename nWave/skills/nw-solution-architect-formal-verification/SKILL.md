---
name: nw-solution-architect-formal-verification
description: Load in the model step to decide which design claims need a formal model, pick Quint or TLA+, and write, check and mutate-test it.
user-invocable: false
---

# Formal model step

## 1. Decide before writing

1. List every design claim about state, protocol, ordering, concurrency, retry, crash recovery, progress (liveness), refinement (implementation matches spec) or reachability. Mark each "model" or "no model".
2. Model when: several actors can change the same state; a protocol has more than one step; a retry, crash or restart must leave state consistent; something must eventually happen; an implementation must refine a spec.
3. No model when the claim names no shared state, no multi-step protocol, no concurrency or crash window, and examples cover its transitions. A pure function with a stated law (totality, round trip, canonical form, ordering) is still a claim: check it (Quint over the transition function, or Agda).
4. Write the reason as `No model for <claim>: <the specific state, protocol, concurrency or crash window that is absent>`. "Simple", "small", "no tool" or "timed out" is never a reason; a missing checker, or a timed-out checker with its repair attempts recorded (item 12), is `INDETERMINATE`.
5. Choose the checker per claim: Quint (default: `quint run`, then `quint verify`); TLA+ with TLC when the claim needs liveness under fairness, PlusCal processes, or Quint's backend cannot finish; Agda only for proofs over types. Use two checkers when one cannot cover the claim. Reuse an existing model of the same protocol.
6. The closing statement maps every modelled claim to the checker that ran on it.

## 2. Write the model

7. One file per model in the repository at the path the design names (`<name>.qnt`, or `<name>.tla` plus `<name>.cfg`), complete; never paste it into the design text.
8. Declare state variables, `init`, one action per atomic step, every invariant, every liveness property. Model only the concurrency, failure and crash steps the claim needs, two processes first; leave out logging, serialization, UI.
9. Name each atom after one runtime symbol (class, function, field). Closing statement: atom -> symbol, atoms with none as `model-only`, and what the model does not cover (timing, throughput, unbounded scheduling). A step count is not time; claim no latency or availability from a model.

## 3. Check it

10. Check the tool exists (`quint --version`, `java -version`). Run from a copy outside the repository so `_apalache-out` and `_build` stay out of the tree. `quint typecheck`, then each invariant. Fix syntax errors and rerun.
11. Use the real checker even on a tiny state space; a Python enumerator or hand trace is not a check.
12. Budget each run at 180 seconds. Start with two processes and the fewest steps reaching the seam; grow to three, then failures, then liveness. A timed-out bound is not verified and is not a stopping point: diagnose it before any outcome - reduce the model to a narrower slice recorded as its own claim (never presented as the original claim) or change the checker strategy or configuration, and record each attempt with its bound and result. Never rerun a timed-out bound unchanged.
13. After the recorded repair attempts, a claim the checker still cannot verify within the budget is `INDETERMINATE` with the tool name and the bounds tried, never PASS. A missing or unexecuted check is `INDETERMINATE` with the tool name; there is no run to diagnose. Continue the other claims.
14. Commit the model only, not output, logs or traces.

## 4. One witness per invariant

15. Per invariant, copy the model and remove the exact behaviour it guards (lock check, idempotency guard, rollback). Leave invariant and flags unchanged.
16. Run `quint run MODEL.qnt --invariant=INV` on the mutant (a counterexample is a kill); run `quint verify` only if none is found. The invariant must fail. A tool error or timeout is not a kill.
17. One mutant per invariant. An invariant no mutant breaks may be vacuous: strengthen it.
18. Delete the mutant after the run.
19. Each invariant also gets a default-suite unit or property test of the same rule on the pure core, including the sad path (repeated step, interrupted step, refused stale write). Faults the projection cannot reach stay in the model.

## 5. Liveness

20. Per liveness property give an executable witness (a test or model run reaching the good state) or `no liveness claim: <concrete reason>`.
21. Declare fairness only where the result depends on it: `weakFair(action, vars)` or `strongFair(action, vars)` on the real action, naming whose scheduling you assume.
22. A fairness-dependent property needs three TLC runs (`quint verify MODEL.qnt --init=init --step=step --temporal=PROP --backend tlc`): without fairness it fails with a stuttering counterexample; with fairness it passes; with fairness on a mutant removing the progress or release step it fails.
23. A property that holds without fairness: state which step is always enabled and why.
24. Slice finitely but keep the state the property needs; name what the slice drops.

## 6. Self-check

1. Each claim has a named checker or a `No model for` reason naming the absent window.
2. Model files complete in the repository, no run output.
3. Each invariant failed on its own mutant and has a default-suite test.
4. Each liveness property has a witness or reason; fairness only where needed.
5. No timed-out or unexecuted check is called a pass; every timed-out check shows its recorded repair attempts.
6. Closing statement lists claim -> checker, atom -> symbol, `model-only` atoms, and what is not covered.
