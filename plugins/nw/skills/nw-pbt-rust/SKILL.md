---
name: nw-pbt-rust
agent: nw-functional-software-crafter
description: "Rust property-based testing with proptest, quickcheck, and bolero. Load when writing property-based tests in Rust or choosing between proptest, quickcheck, and bolero."
user-invocable: false
disable-model-invocation: true
---

# PBT Rust -- proptest, quickcheck, bolero

## Framework Selection

| Framework | Shrinking | Stateful | Choose When |
|-----------|-----------|----------|-------------|
| proptest | Integrated | No | Default choice. Most features, best shrinking. |
| quickcheck | Type-based | No | Simple properties, one generator per type sufficient |
| bolero | Engine-dependent | No | Want to switch between PBT and fuzzing engines |

**Default**: proptest. Supports multiple strategies per type without newtype wrappers, better shrinking.

## Quick Start (proptest)

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn sort_preserves_length(ref v in prop::collection::vec(any::<i32>(), 0..100)) {
        let mut sorted = v.clone();
        sorted.sort();
        prop_assert_eq!(sorted.len(), v.len());
    }
}

// Run: cargo test
```

## Generator (Strategy) Cheat Sheet (proptest)

### Primitives
```rust
any::<i32>()                          // any i32
0..100i32                             // range (implements Strategy)
any::<f64>()
any::<String>()
any::<bool>()
any::<Vec<u8>>()                      // bytes
Just(42)                              // constant
```

### Collections
```rust
prop::collection::vec(any::<i32>(), 0..50)
prop::collection::vec(any::<i32>(), 1..=10)   // non-empty, max 10
prop::collection::hash_set(any::<i32>(), 0..20)
prop::collection::hash_map(any::<String>(), any::<i32>(), 0..20)
(any::<i32>(), any::<String>())       // tuple
```

### Combinators
```rust
// Union
prop_oneof![any::<i32>().prop_map(Value::Int), any::<String>().prop_map(Value::Str)]

// Map
any::<i32>().prop_map(|x| x * 2)     // even integers

// Filter
any::<i32>().prop_filter("positive", |x| *x > 0)
// Prefer: 1..i32::MAX

// FlatMap (dependent generation)
prop::collection::vec(any::<i32>(), 1..50)
    .prop_flat_map(|v| {
        let len = v.len();
        (Just(v), 0..len)
    })

// Regex-based strings
"[a-z]{1,10}"                        // implements Strategy
"[0-9]{3}-[0-9]{4}"                  // phone-like pattern
```

### Recursive
```rust
fn json_value() -> impl Strategy<Value = JsonValue> {
    let leaf = prop_oneof![
        Just(JsonValue::Null),
        any::<bool>().prop_map(JsonValue::Bool),
        any::<i64>().prop_map(JsonValue::Number),
    ];
    leaf.prop_recursive(8, 256, 10, |inner| prop_oneof![
        prop::collection::vec(inner.clone(), 0..10).prop_map(JsonValue::Array),
        prop::collection::hash_map(".*", inner, 0..10).prop_map(JsonValue::Object),
    ])
}
```

### Custom Strategy
```rust
#[derive(Debug, Clone)]
struct User { name: String, age: u8 }

fn user_strategy() -> impl Strategy<Value = User> {
    ("[a-z]{1,20}", 1..120u8)
        .prop_map(|(name, age)| User { name, age })
}

// Or derive Arbitrary
#[derive(Debug, Arbitrary)]
struct Point { x: i32, y: i32 }
```

## Generator Cheat Sheet (quickcheck)

```rust
// Implement Arbitrary for custom types
impl quickcheck::Arbitrary for Color {
    fn arbitrary(g: &mut quickcheck::Gen) -> Self {
        *g.choose(&[Color::Red, Color::Green, Color::Blue]).unwrap()
    }
}

// Built-in Arbitrary for primitives, Vec, String, Option, Result, tuples
// Bounded generation via Gen::choose
impl quickcheck::Arbitrary for SmallInt {
    fn arbitrary(g: &mut quickcheck::Gen) -> Self {
        SmallInt(*g.choose(&(0..=100).collect::<Vec<_>>()).unwrap())
    }
    fn shrink(&self) -> Box<dyn Iterator<Item = Self>> {
        Box::new(self.0.shrink().map(SmallInt))
    }
}
```

## Quick Start (quickcheck)

```rust
use quickcheck::quickcheck;

quickcheck! {
    fn prop_reverse_involutory(xs: Vec<i32>) -> bool {
        let rev: Vec<_> = xs.iter().rev().rev().cloned().collect();
        rev == xs
    }
}
```

## Stateful Testing

Not natively supported by proptest or quickcheck. Manual pattern:

```rust
#[derive(Debug, Clone, Arbitrary)]
enum Command { Put(String, i32), Get(String), Delete(String) }

proptest! {
    #[test]
    fn store_matches_model(cmds in prop::collection::vec(any::<Command>(), 0..50)) {
        let mut store = MyStore::new();
        let mut model = HashMap::new();
        for cmd in cmds {
            match cmd {
                Command::Put(k, v) => { store.put(&k, v); model.insert(k, v); }
                Command::Get(k) => {
                    prop_assert_eq!(store.get(&k), model.get(&k).copied());
                }
                Command::Delete(k) => { store.delete(&k); model.remove(&k); }
            }
        }
    }
}
```

## Quick Start (bolero)

```rust
use bolero::check;

#[test]
fn sort_test() {
    check!().with_type::<Vec<i32>>().for_each(|v| {
        let mut sorted = v.clone();
        sorted.sort();
        assert_eq!(sorted.len(), v.len());
    });
}
// Requires: cargo install cargo-bolero (for fuzzing engines)
// Run with fuzzer: cargo bolero test sort_test --engine libfuzzer
// Run as PBT: cargo test (uses random engine)
```

bolero's value: same test runs with libfuzzer, honggfuzz, AFL, or Kani verifier.

## Test Runner Integration

```rust
// proptest: add to Cargo.toml
// [dev-dependencies]
// proptest = "1"
// Failures saved to proptest-regressions/ directory

// Configure in proptest.toml or ProptestConfig
proptest! {
    #![proptest_config(ProptestConfig::with_cases(10000))]
    #[test]
    fn my_prop(x in any::<i32>()) { /* ... */ }
}
```

## Unique Features (proptest)

- **Regex-based string generation**: `"[a-z]{1,10}"` as a strategy
- **Multiple strategies per type**: No newtype wrappers needed (unlike quickcheck)
- **Failure persistence**: Saves to `proptest-regressions/` files, auto-replays
- **prop_compose!**: Macro for composing strategies declaratively
- **Integrated shrinking**: Constraint-aware, avoids generating invalid values during shrink
