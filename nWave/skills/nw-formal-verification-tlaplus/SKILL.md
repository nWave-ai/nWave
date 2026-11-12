---
name: nw-formal-verification-tlaplus
description: Load when writing a Quint or TLA+/PlusCal model to get runnable syntax, check commands and state-space limits; decision rules are in nw-solution-architect-formal-verification.
user-invocable: false
disable-model-invocation: true
---

# Model syntax and commands

## Choose

Quint for state machines and invariants (fast `quint run`). TLA+/TLC for liveness under fairness, PlusCal processes, or when Quint's backend cannot finish. Start with safety, add liveness after.

## Quint

```quint
module counter {
  var n: int
  action init = n' = 0
  action step = any { all { n < 3, n' = n + 1 }, all { n > 0, n' = n - 1 } }
  val inRange = n >= 0 and n <= 3
}
```

- `init` sets every variable with `x' = ...`; `any { a, b }` is a choice; `all { guard, update }` is one atomic step and assigns every variable.
- Invariant: a boolean `val`. Temporal: `temporal p = eventually(q)`; also `always`, `weakFair(action, vars)`, `strongFair(action, vars)`. Nondeterminism: `nondet x = oneOf(Set(1, 2))`.

| Purpose | Command |
|---|---|
| Typecheck | `quint typecheck M.qnt` |
| Counterexample search | `quint run M.qnt --invariant=inRange --max-steps=20 --max-samples=1000` |
| Exhaustive safety | `quint verify M.qnt --init=init --step=step --invariant=inRange` |
| Liveness | `quint verify M.qnt --init=init --step=step --temporal=PROP --backend tlc` |

If the sandbox refuses the backend server: `quint compile --target json M.qnt > M.qnt.json`, then `apalache-mc check --init=init --next=step --inv=inRange --length=10 M.qnt.json` (safety only).

## TLA+ / TLC

- `---- MODULE M ----` ... `====`; `VARIABLES x`; `Init == x = 0`; `Next == \/ A \/ B`; `Spec == Init /\ [][Next]_x /\ WF_x(A)`.
- `Inv == x \in 0..3`; `Live == <>(x = 3)`; `WF_x(A)` weak, `SF_x(A)` strong fairness.
- `M.cfg`: `SPECIFICATION Spec`, `INVARIANT Inv`, `PROPERTY Live`, `CONSTANT N = 2`, optional `SYMMETRY`, `CONSTRAINT`.
- Run: `java -jar tla2tools.jar -config M.cfg -workers auto M.tla`; large models: add `-simulate -depth 100`.
- PlusCal: labels are atomic steps, processes interleave only between labels; `fair process` is weakly fair; `either/or` chooses; `await` blocks. Example:

```
process Transfer \in 1..2
begin
  Debit:  accounts[from] := accounts[from] - amount;
  Credit: accounts[to] := accounts[to] + amount;
end process;
```
Invariant `accounts["a"] + accounts["b"] = 200` fails if a crash step is added between labels without compensation.

## State space

Use 2 processes and 2-4 messages, then grow; doubling a parameter roughly squares the states. Merge labels that need no interleaving, add `SYMMETRY` for interchangeable nodes, model the protocol not the transport, split into focused models. Use Apalache when TLC passes about 10M states.

## Modeling mistakes to avoid

Model each of these: spontaneous abort or crash (volatile state lost, persistent kept); message loss and duplication; lock state kept separate from a node's belief about it; compensation in reverse order; merge commutative, associative and idempotent; at most one leader per term.
