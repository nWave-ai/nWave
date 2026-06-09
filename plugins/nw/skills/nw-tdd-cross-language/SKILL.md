---
name: nw-tdd-cross-language
description: Port the state-delta + property-based testing paradigm to languages other than Python. DIY recipes per language; canonical Python ref shipped in nwave_ai.state_delta.
user-invocable: false
disable-model-invocation: true
---

# Cross-Language Paradigm Porting Guide

The state-delta + property-based testing paradigm (see `nw-tdd-methodology::Paradigm Mandate`) is shipped natively in Python via `nwave_ai.state_delta`. This skill documents how to apply the same paradigm in other languages with idiomatic adaptations.

**Open source positioning** (nwave-ai master): Python canonical + DIY porting guide. Users in other languages port the pattern using their language's PBT library + a small state-delta shim (~70-150 LOC).

**Enterprise positioning** (nwave-pro bundle, deferred): pre-built language packages with tested implementations, kept consistent across versions.

---

## Per-language framework + PBT library matrix

| Language | Test framework | PBT library | State-delta port size | Idiomatic notes |
|---|---|---|---|---|
| **Python** | pytest | Hypothesis | shipped (`nwave_ai.state_delta`, ~250 LOC) | Reference implementation. Closure-over-parameters predicates, frozen dataclass `Violation`. |
| **TypeScript / JS** | vitest, jest, mocha | `fast-check` | ~80 LOC | Generics over `Old, New`. Predicate = `(old: O, new: N) => boolean`. Use `expect.fail()` for AssertionError equivalent. |
| **Java** | JUnit 5 | `jqwik` | ~120 LOC | Verbose generics (`Predicate<O, N>`). Builder pattern for `assertStateDelta(...)` fluent API. Use `AssertionError`. |
| **Kotlin** | kotest (built-in PBT) | native | ~80 LOC | DSL idiomatic — `assertStateDelta { universe(...) ; expected(...) }`. Lambda predicates fit naturally. |
| **F# / .NET** | xUnit, NUnit | `FsCheck` | ~70 LOC | Functional fit naturale. Discriminated unions for `Violation`, partial application for predicate factories. |
| **Rust** | cargo test | `proptest` | ~100 LOC | `Fn` traits for predicates. `struct Violation` with derive(Clone, Debug). Returns `Result<(), AssertionError>`. |
| **Go** | testing | `gopter`, `quick` | ~150 LOC | More verbose due to lack of closures over generics. Predicate = function accepting `interface{}`. Use `t.Errorf` for assertion. |
| **OCaml** | alcotest | `qcheck` | ~70 LOC | Functional fit naturale. Variant types for `Violation`, partial application natural. |
| **Scala** | ScalaTest | `ScalaCheck` | ~80 LOC | Pattern matching for `Violation`, implicit conversions for fluent predicate composition. |

---

## Canonical Python reference

**API contract** (locked at pilot, see `nwave_ai.state_delta.matcher`):

```python
def assert_state_delta(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    universe: set[str],
    expected: Mapping[str, Predicate],
    *,
    strict: bool = False,
) -> None: ...

Predicate = Callable[[Any, Any], bool]

# 8 predicate factories:
def prepended_with(prefix: str, sep: str = ":") -> Predicate: ...
def appended_with(suffix: str, sep: str = ":") -> Predicate: ...
def unchanged() -> Predicate: ...
def set_to(value: Any) -> Predicate: ...
def containing(substring: str) -> Predicate: ...
def normalized_to(normalizer: Callable[[Any], Any]) -> Predicate: ...
def idempotent_after(prefix: str, sep: str = ":") -> Predicate: ...
def legacy_healed(detector: Callable[[Any], bool], healed_check: Callable[[Any], bool]) -> Predicate: ...
```

**Semantics**:
- For each key in `universe`:
  - If in `expected`: predicate must return True
  - If NOT in `expected`: implicit-unchanged (`before[k] == after[k]`)
- `strict=True`: keys in `(before|after) - universe` raise `kind=strict_universe_mismatch`
- Multi-violation: ALL violations collected, ONE AssertionError raised

---

## Porting recipe (language-agnostic)

For ANY language, the port is a small shim around the language's PBT library + an `assert_state_delta` function that captures the multi-violation collection semantics. **Keep it small (~70-150 LOC). Do not over-engineer.**

### Step 1 — Translate the API contract

Adapt the function signatures using language-idiomatic types:
- Universe = set/list of strings (`Set<String>`, `string[]`, `&[String]`, etc.)
- Expected = map of string → predicate (`Map<String, Predicate>`, `{[key: string]: Predicate}`, `HashMap<String, Box<dyn Fn>>`)
- Predicate = callable taking `(old, new) → bool`

### Step 2 — Implement the multi-violation collector

```pseudocode
function assert_state_delta(before, after, universe, expected, strict=false):
    violations = []
    for key in universe:
        if key in expected:
            predicate = expected[key]
            if not predicate(before[key], after[key]):
                violations.append(predicate_failed_violation(key, before[key], after[key]))
        else:
            if before[key] != after[key]:
                violations.append(undeclared_change_violation(key, before[key], after[key]))
    if strict:
        for key in (before.keys ∪ after.keys) - universe:
            violations.append(strict_universe_mismatch_violation(key, before.get(key), after.get(key)))
    if violations:
        raise AssertionError(format_multiline_message(violations))
```

### Step 3 — Implement the 8 predicate factories

Each factory closes over its parameters and returns a callable. Use language-idiomatic closure mechanism:
- TypeScript: arrow functions
- Rust: `move` closures returning `impl Fn(...) -> bool`
- F#: partial application
- Java: anonymous inner class or lambda + `Function`/`BiPredicate`
- Go: function returning `func(old, new interface{}) bool`

### Step 4 — Hook to PBT library

Combine with language's PBT library. The PBT library generates inputs; `assert_state_delta` validates the post-action state.

```pseudocode
property "installer preserves user PATH":
    forall(path: gen_realistic_path):
        before = capture_state()
        installer.install(path)
        after = capture_state()
        assert_state_delta(before, after,
                          universe={"PATH", "permissions", "hooks"},
                          expected={"PATH": prepended_with(des_bin)},
                          strict=true)
```

---

## Idiomatic mini-examples per language

### TypeScript / fast-check

```typescript
import { fc } from 'fast-check';
import { assertStateDelta, prependedWith } from './state-delta';  // ~80 LOC shim

fc.assert(
  fc.property(pathStrategy(), (userPath) => {
    const before = captureState();
    installShims(userPath);
    const after = captureState();
    assertStateDelta(before, after, {
      universe: ['PATH', 'permissions', 'hooks'],
      expected: { PATH: prependedWith('/des/bin') },
      strict: true,
    });
  })
);
```

### Rust / proptest

```rust
use proptest::prelude::*;
use crate::state_delta::{assert_state_delta, prepended_with};  // ~100 LOC shim

proptest! {
    #[test]
    fn installer_preserves_user_path(user_path in path_strategy()) {
        let before = capture_state();
        install_shims(&user_path);
        let after = capture_state();
        assert_state_delta(
            &before, &after,
            &["PATH", "permissions", "hooks"],
            &[("PATH", prepended_with("/des/bin"))],
            true,  // strict
        ).unwrap();
    }
}
```

### F# / FsCheck

```fsharp
open FsCheck.Xunit
open StateDelta  // ~70 LOC shim

[<Property>]
let ``installer preserves user PATH`` (userPath: PathShape) =
    let before = captureState()
    installShims userPath
    let after = captureState()
    assertStateDelta before after
        [ "PATH"; "permissions"; "hooks" ]
        [ "PATH", prependedWith "/des/bin" ]
        StrictMode.Strict
```

### Java / jqwik

```java
import net.jqwik.api.*;
import org.example.statedelta.StateDelta;  // ~120 LOC shim

class InstallerProperties {
    @Property
    void installerPreservesUserPath(@ForAll("paths") String userPath) {
        var before = captureState();
        installer.install(userPath);
        var after = captureState();
        StateDelta.assertStateDelta(
            before, after,
            Set.of("PATH", "permissions", "hooks"),
            Map.of("PATH", StateDelta.prependedWith("/des/bin")),
            true  // strict
        );
    }
}
```

---

## When to NOT port (use canonical Python via subprocess)

If the SUT (system under test) is a Python service or CLI:
- Skip language port; call Python from your language's test runner
- Spawn the Python service, use Python `assert_state_delta` directly via test fixture
- Cheaper than re-porting the matcher

If the SUT is in your language but you only need state-delta for a few critical surfaces:
- Hand-roll a 30-line minimal version (just `assert_state_delta` + 2-3 predicates you actually need)
- Don't port the full 8-predicate library prematurely

---

## Stage cascade applies cross-language

The 3-stage cascade in `nw-tdd-methodology::Paradigm Mandate` applies regardless of language:

- **Stage 0** (new code, paradigm-from-day-zero): debt never accumulates. Apply paradigm in whatever language as you write tests
- **Stage 1** (legacy bug-prone): state-delta migration captures debt (33-75% yield)
- **Stage 2a** (post Stage 1): PBT amplification ~0% by design
- **Stage 2b** (legacy bug-prone, no Stage 1): PBT amplification ~75%

Stage applicability is independent of language. Language port is enabling infrastructure; the paradigm itself is universal.

---

## Enterprise option

If your organization needs:
- Tested, supported language packages (cross-version stability)
- Cross-language consistency checks (same paradigm everywhere, audited)
- Migration tooling (AI-assisted Stage 1 conversions in your language)

These ship as part of the **nwave-pro** enterprise bundle (deferred — contact the nWave team). Open-source path is sufficient for paradigm validation; enterprise reduces porting effort + adds support.

---

## Quick reference

| Task | Resource |
|---|---|
| Read paradigm mandate | `nw-tdd-methodology::Paradigm Mandate` |
| Read stage cascade | `nw-tdd-methodology::Empirical efficacy framework` |
| Python canonical implementation | `nwave_ai.state_delta` (matcher.py + predicates.py) |
| Python pilot example | `tests/state_delta/integration/test_pilot_bug48.py` (D-12 Part A + B) |
| Roadmap directive (architects) | `nw-roadmap::Test paradigm mandate` |

For language-specific PBT library docs, see official:
- fast-check: `https://fast-check.dev/`
- proptest: `https://docs.rs/proptest/`
- jqwik: `https://jqwik.net/`
- FsCheck: `https://fscheck.github.io/FsCheck/`
- gopter: `https://github.com/leanovate/gopter`
- ScalaCheck: `https://scalacheck.org/`
- qcheck: `https://github.com/c-cube/qcheck`
- kotest (built-in): `https://kotest.io/docs/proptest/property-based-testing.html`
