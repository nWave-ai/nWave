---
name: nw-test-optimization-paradigm-match
description: Decision rule matching test SHAPE to the right paradigm before authoring/migrating - closed-world vs multi-step-setup vs state-mutation vs unbounded-invariant vs few-examples, plus the falsifier-gate that blocks PBT on finite domains
user-invocable: false
disable-model-invocation: true
---

# Paradigm-Match Decision (KNOWLEDGE)

**Kind**: KNOWLEDGE (decision rule / taste). **One trigger**: "which test paradigm fits this test shape — before I author or migrate" — fires at the recon stage of any optimization/authoring where the paradigm is not yet fixed. Mismatched paradigm = ceremony without value (or correctness loss). Composed by `nw-test-optimization`.

## Decision table

| Test shape | Paradigm | Empirical anchor |
|---|---|---|
| **Closed-world finite input** (N known files, M known event types, K known skill names) — assertion shape identical across instances | Native finite-case/table facility collapse → consolidation §3.1 / Dict-iteration → §3.2 | `c2637f6c8` set-difference 155-test → 1 (8.9× faster) |
| **Multi-step contract on shared expensive setup** — independent assertions on post-setup read-only state | Single-lifecycle consolidation → §3.7 | `defc07f0d` 24-test 152s → 63s (2.4× faster) |
| **User-observable state mutation** (installer/uninstaller/sync/hooks/settings) — N tests verifying same lifecycle's side effects | State-delta paradigm → §3.8 | Task #12 pilot (13% compression / 17% wall-clock) |
| **Unbounded input domain** with universal invariant (algorithm, serialization, business rule) — "for all X in DOMAIN, P(X) holds" | Property-based testing with the project's native property engine — see `nw-property-based-testing` | Standard PBT literature; nWave-internal scope = unbounded ONLY |
| **Single happy-path + 1-3 sad paths** with distinct error messages | Example-based unit tests, no consolidation needed | n/a — already minimal |

## Falsifier-gate before adopting PBT

Closed-world finite input is NOT PBT territory. A property engine's startup and per-example bookkeeping is **slower** than the language's native finite-case/table facility when the input set is finite + enumerable. The facility is whatever the project already uses (illustrations only: Python `pytest.mark.parametrize`, Go table-driven subtests, Rust `rstest`/macro-generated cases, JUnit `@ParameterizedTest`, .NET xUnit `[Theory]`, TS `test.each`, C/C++ data-driven/parameterized test macros); the property engine likewise (Hypothesis, `testing/quick`/rapid, proptest/quickcheck, jqwik, FsCheck, fast-check, RapidCheck, ...). If neither exists natively, record an EVIDENCE_GAP with cause; never change the stack. Apply the gate:

1. **Enumerate the input domain**. Is it finite + listable (`SKILL_NAMES_149`, `EVENT_TYPES_5`, `SUPPORTED_RUNTIMES_3`)? → finite-case collapse, NOT PBT.
2. **Is the invariant value-independent** (holds for ANY valid X, not specific Xs)? → PBT candidate.
3. **Run cost-benefit**: if domain ≤ 10× the typical PBT example budget (100), the native finite-case facility wins on wall-clock + readability + shrinking-from-trivial-counterexamples cost.

**Empirical anchor 2026-05-18** (Python project): PBT migration attempt on 155-file closed-world skill registry was correctly aborted at recon stage by the falsifier-gate. Solution was set-difference finite-case collapse (`c2637f6c8`, 5.42s → 0.71s, 8.9× faster). Documented in memory `feedback_state_transition_test_paradigm` (revised 2026-05-05).

## Decision tree (concise)

```
Test shape?
├─ Same assertion, varying inputs from finite known set?
│   └─ native finite-case/table collapse (§3.1) OR dict/map-iteration (§3.2)
├─ N independent assertions on same post-setup read-only state?
│   └─ single-lifecycle consolidation (§3.7)
├─ State-mutation lifecycle with delta assertions?
│   └─ state-delta paradigm (§3.8)
├─ Universal invariant over unbounded domain?
│   └─ PBT (nw-property-based-testing)
└─ Few specific examples with distinct outcomes?
    └─ example-based, no consolidation
```

The consolidation mechanics (§3.x) live in `nw-test-optimization-consolidation`; PBT lives in `nw-property-based-testing`.
