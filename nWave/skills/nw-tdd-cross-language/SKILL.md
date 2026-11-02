---
name: nw-tdd-cross-language
description: Port the state-delta + property-based testing paradigm to languages other than Python. DIY recipes per language; canonical Python ref shipped in nwave_ai.state_delta.
user-invocable: false
disable-model-invocation: true
---

# Cross-Language State-Delta Porting Guide

This optional implementation guide is not a requirement to port an nWave API.
Native discovery and applicability live in `nw-test-design-mandates`; its
layered-mechanics module owns observation laws. Use incumbent native assertions,
generators, shrinking/replay and helpers first. Matching `nw-pbt-*` guidance
loads on need; unlisted languages use their real native tooling, not an
`EVIDENCE_GAP` merely because no adapter is shipped. Never borrow Python as a
substitute. The recipes below illustrate one optional helper implementation.

Unlisted languages (C, C++, OCaml, etc.) use their own native test, generator, shrinker and replay libraries; no Python-derived shim is imposed.

---

## Canonical Python reference

**Illustrative Python API contract** (semantics reference only; not a required API, file path or predicate count; see `nwave_ai.state_delta.matcher`):

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

# Illustrative predicate factories (not a required set or count):
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

## Porting recipe (conditional, language-agnostic)

Only when an existing native assertion/helper cannot express a needed public-state preservation observation, consider a small project-idiomatic helper. Translate the semantics needed by actual consumers, not a mandatory eight-predicate API or fixed path. Do not create a shim or additional allocations merely to match this illustrative Python reference.

### Step 1 — Translate the semantics, only if a helper is needed

Adapt the function signatures using language-idiomatic types:
- Universe = set/list of strings (`Set<String>`, `string[]`, `&[String]`, etc.)
- Expected = map of string → predicate (`Map<String, Predicate>`, `{[key: string]: Predicate}`, `HashMap<String, Box<dyn Fn>>`)
- Predicate = callable taking `(old, new) → bool`

### Step 2 — Multi-violation collector (illustrative)

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

### Step 3 — Predicates (only those consumers need)

Include only the predicates actual tests need; the Python eight are illustrative, not a required count. If added, each closes over its parameters using the language's idiom (illustrative: TypeScript arrow functions, Rust `move` closures, F# partial application, Java lambdas, Go returned funcs).

### Step 4 — Compose with the native PBT library (if any)

If the project already has a generator/shrinker/replay library, it generates inputs and the native assertion or helper validates post-action state. Illustrative sketch:
```pseudocode
property "installer preserves user PATH":
    forall(path: gen_realistic_path):
        before = capture_state()
        installer.install(path)
        after = capture_state()
        assert_state_delta(before, after,
                          universe={"PATH", "permissions", "hooks"},
                          expected={"PATH": prepended_with(app_bin)},
                          strict=true)
```

---

## Illustrative mini-examples per language (not required APIs, paths or LOC)

### TypeScript / fast-check

```typescript
import { fc } from 'fast-check';
import { assertStateDelta, prependedWith } from './state-delta';  // hypothetical helper

fc.assert(
  fc.property(pathStrategy(), (userPath) => {
    const before = captureState();
    installShims(userPath);
    const after = captureState();
    assertStateDelta(before, after, {
      universe: ['PATH', 'permissions', 'hooks'],
      expected: { PATH: prependedWith('/app/bin') },
      strict: true,
    });
  })
);
```

### Rust / proptest

```rust
use proptest::prelude::*;
use crate::state_delta::{assert_state_delta, prepended_with};  // hypothetical helper

proptest! {
    #[test]
    fn installer_preserves_user_path(user_path in path_strategy()) {
        let before = capture_state();
        install_shims(&user_path);
        let after = capture_state();
        assert_state_delta(
            &before, &after,
            &["PATH", "permissions", "hooks"],
            &[("PATH", prepended_with("/app/bin"))],
            true,  // strict
        ).unwrap();
    }
}
```

### F# / FsCheck

```fsharp
open FsCheck.Xunit
open StateDelta  // hypothetical helper

[<Property>]
let ``installer preserves user PATH`` (userPath: PathShape) =
    let before = captureState()
    installShims userPath
    let after = captureState()
    assertStateDelta before after
        [ "PATH"; "permissions"; "hooks" ]
        [ "PATH", prependedWith "/app/bin" ]
        StrictMode.Strict
```

### Java / jqwik

```java
import net.jqwik.api.*;
import org.example.statedelta.StateDelta;  // hypothetical helper

class InstallerProperties {
    @Property
    void installerPreservesUserPath(@ForAll("paths") String userPath) {
        var before = captureState();
        installer.install(userPath);
        var after = captureState();
        StateDelta.assertStateDelta(
            before, after,
            Set.of("PATH", "permissions", "hooks"),
            Map.of("PATH", StateDelta.prependedWith("/app/bin")),
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

If the SUT is in your language, first use the incumbent native assertions. Only if a public-state preservation observation cannot be expressed, add a minimal project-idiomatic helper with just the predicates consumers actually need; do not port a fixed predicate set.

---

## Stage cascade applies cross-language

The 3-stage cascade in `nw-tdd-methodology::Paradigm Mandate` applies regardless of language:

- **Stage 0** (new code, paradigm-from-day-zero): debt never accumulates. Apply paradigm in whatever language as you write tests
- **Stage 1** (legacy bug-prone): state-delta migration captures debt (33-75% yield)
- **Stage 2a** (post Stage 1): PBT amplification ~0% by design
- **Stage 2b** (legacy bug-prone, no Stage 1): PBT amplification ~75%

Stage applicability is independent of language. The language-independent law: observe port-exposed state before and after the action, and fail closed on any unexpected change. Express it with the project's own native tooling; any helper is optional infrastructure.

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
| Design directive (architects) | `nw-design::Development Paradigm Selection` |

For language-specific PBT library docs, see official:
- fast-check: `https://fast-check.dev/`
- proptest: `https://docs.rs/proptest/`
- jqwik: `https://jqwik.net/`
- FsCheck: `https://fscheck.github.io/FsCheck/`
- gopter: `https://github.com/leanovate/gopter`
- ScalaCheck: `https://scalacheck.org/`
- qcheck: `https://github.com/c-cube/qcheck`
- kotest (built-in): `https://kotest.io/docs/proptest/property-based-testing.html`
