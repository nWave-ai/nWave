---
name: nw-property-based-testing
description: Load when a design law holds over a broad input, state or sequence domain and needs a generated property test.
user-invocable: false
---

# Property tests for broad laws

A property states "for all valid inputs this observation holds". It searches for counterexamples; it is not proof and not a substitute for a real-boundary test. Use the project's native generator with shrinking and replay.

## 1. Choose the smallest falsifying boundary first

A property does not choose its own scope: generation is a technique for exploring a law, not a decision about which boundary a test exercises. Before choosing generators, case counts or timeouts:

1. State the law in one sentence ("transfers keep the total balance").
2. Choose the smallest production boundary that can falsify it, and name it in the test: a pure function or component for broad business-rule exploration (exercising production behavior, not a duplicated test model), a focused real integration boundary for claims smaller tests cannot prove (persistence, serialization, delivery, runtime replay, deduplication, concurrency), and a broad-stack/E2E journey only for a critical journey or an important failure class. Never repeat the full business-rule matrix through the whole stack by default.
3. Pick generators and case count for that boundary. The framework default is a starting point, not an adequacy target: fast-check's `numRuns` defaults to 100 (not 500), and neither value is universally adequate or inadequate. Choose the count from the law's falsification power and the budget, not from habit.
4. Question scope before raising time. A property timeout does not cancel a running Promise (fast-check reports the timeout and ignores the late result; the work still runs), and shrinking can require further executions. A larger timeout or a higher case count is a cost increase, never evidence that the scope is right.
5. Framework capability is not a scope mandate. Async predicates and model-based stateful command sequences are supported (fast-check properties and model-based testing), which establishes capability — not a requirement to run broad generation at full-stack scope. Broad generated execution at a broad boundary needs an explicit boundary-sensitive reason; the tool's support for it is not that reason.
6. When splitting a broad test, map its existing obligations to lower-level tests and to the retained boundary evidence before editing: do not merely lower the count, shard the same expensive loop, replace runtime proof with a fake, or remove safety assertions.

Sources: [fast-check properties](https://fast-check.dev/docs/core-blocks/properties/) and [model-based testing](https://fast-check.dev/docs/advanced/model-based-testing/) (async/stateful capability); [fast-check parameters](https://fast-check.dev/docs/api/interfaces/Parameters/) (`numRuns` default 100) and [timeouts](https://fast-check.dev/docs/configuration/timeouts/) (timeout cannot cancel a running Promise; shrinking needs further runs); Ham Vocke, [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html#AvoidTestDuplication) (push tests down, avoid duplication across levels); Google, [What Makes a Good End-to-End Test?](https://testing.googleblog.com/2016/09/testing-on-toilet-what-makes-good-end.html) (E2E for what smaller tests cannot reliably evaluate; one per important use case and error class, total count low).

## 2. Decide: property or example

1. A law over a broad domain (unbounded inputs, state transitions, sequences, serialization, business rules) gets a property. A table of examples never stands in for it.
2. A closed finite domain gets native examples or an exhaustive loop over every member; no property.
3. Write one property per distinct law. Combine laws only when one generated observation falsifies each.
4. Pick the pattern: invariant (holds for every input), roundtrip (`decode(encode(x)) == x`), oracle (compare with a simple reference), metamorphic (a known input change gives a known output change), idempotence (`f(f(x)) == f(x)`), commutativity (order of operands or operations does not matter). When none is obvious, start from a known example, embed its answer in a generated input, and predict where it appears in the output.
5. Write no property for a layer that declares no law.

## 3. Write the generator

1. Declare domain and size bounds in the test code. Never narrow a boundary to suit the storage engine or the generator.
2. Make every generated component influence the input, the call or the oracle; delete any that does not.
3. For a branching law, generate the case tag first from a closed sum, then build inputs that satisfy that case by construction. Never reach rare branches by filtering, assume/discard or a larger example count.
4. Build structured data from the valid-input type or constructor, so invalid states are never generated unless the law is about rejecting them.
5. Keep it bounded: case count and size so the property fits the default-suite budget (about 10 ms per case). Failures print a replayable seed.

```python
@given(st.lists(st.integers(1, 10**6), min_size=1), st.data())
def test_transfers_keep_total_balance(amounts, data):  # law id in docstring
    acct = Ledger.open(sum(amounts))
    for a in amounts: acct.transfer(a % acct.max_move() or 1)
    assert acct.total() == sum(amounts)
```

## 4. Write the observation and oracle

1. Compute the expected result independently (reference model, inverse operation, algebraic relation). Never copy the production algorithm into the oracle.
2. Assert the promised observation, not "returns a collection", "has the type" or "never raises", unless that is the law.
3. Name the property in domain words ("transfers keep the total balance"); put the design law id in the docstring.

## 5. Stateful and sequence laws

1. Model the observable contract with the simplest pure structure (dict, set, list); never mirror the implementation.
2. Each command has a precondition on the model, a transition on the model, an execution on the real system and a postcondition comparing real result to model.
3. Put every precondition in the framework's precondition mechanism, not only in the generator, so shrunk sequences stay valid. A missing precondition makes shrinking leave long or ghost failures.
4. Treat values returned by the real system as opaque in model code: store and pass, never inspect.
5. Weight commands so every critical command runs; a sequence that never reaches the law's commands proves nothing.
6. Test concurrency (linearizability) only when concurrent correctness is the stated risk.
7. A partial model covering the promised operations well beats a complete model covering all of them weakly.

## 6. Where it runs

1. A broad state or sequence law gets at least one property at integration level: through the real port with real adapter I/O, or at the nearest law-bearing seam with a stated map from its observation to the real-port observation. A model without that map is a proxy.
2. Adapter and recovery properties inject deterministic faults; keep the representative real journey and persistent-storage tests beside them.
3. When no honest seam exists or the tool lacks the capability, report an EVIDENCE_GAP with its cause; never reduce the law to examples.

## 7. Prove it can fail

1. A property for newly promised behaviour must fail on the pre-change code for the promised observation, not for a setup reason. If it passes there, fix or delete it. A property that pins existing behaviour needs only to pass.
2. On a deliberate defect, confirm shrinking yields a small failing case and the seed replays it. If the tool cannot shrink or replay, say so in the test file.

## 8. Self-check before recording the step

1. The law is stated, and the chosen boundary is the smallest production boundary that can falsify it; the scope tier (unit/component property, focused integration, E2E) is named with its boundary-sensitive reason.
3. One law per property, named in domain words, id in docstring.
4. Generator declares domain and size bounds; invalid states not generated by accident.
5. Every generated component is used; rare branches built by construction.
6. Oracle is independent of the production algorithm.
7. Finite domains use examples or an exhaustive loop; broad laws never use a table alone.
8. Stateful: model pure, preconditions in the framework, critical commands exercised.
9. New-behaviour property failed on pre-change code for the promised observation.
10. Broad state law has an integration-level property with its real-port map.
11. The property fits its time budget; if a broad test was split, every obligation maps to a lower-level test or retained boundary evidence.
