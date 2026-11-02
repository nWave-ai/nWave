---
name: nw-pbt-go
agent: nw-functional-software-crafter
description: Go property-based testing with rapid and gopter frameworks
user-invocable: false
---

# PBT Go -- rapid, gopter

## Framework Selection

| Framework | Shrinking | Stateful | API Style | Choose When |
|-----------|-----------|----------|-----------|-------------|
| rapid | Internal (Hypothesis-like) | Yes (StateMachine) | Idiomatic Go (`*rapid.T`) | Default choice. Simpler API, better shrinking. |
| gopter | Type-based | Yes (commands) | Explicit generator construction | Need maximum control over generation |

**Default**: rapid. More idiomatic Go API and fully automatic shrinking.

## Quick Start (rapid)

```go
import (
    "sort"
    "testing"
    "pgregory.net/rapid"
)

func TestSortPreservesLength(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        xs := rapid.SliceOf(rapid.Int()).Draw(t, "xs")
        sorted := make([]int, len(xs))
        copy(sorted, xs)
        sort.Ints(sorted)
        if len(sorted) != len(xs) {
            t.Fatalf("length changed: %d -> %d", len(xs), len(sorted))
        }
    })
}

// Run: go test
```

## Generator Cheat Sheet (rapid)

### Primitives
```go
rapid.Int()                           // any int
rapid.IntRange(0, 99)                 // bounded
rapid.Int32()
rapid.Float64()
rapid.String()
rapid.StringN(1, 50, -1)             // min 1, max 50 chars
rapid.Bool()
rapid.Byte()
```

### Collections
```go
rapid.SliceOf(rapid.Int())
rapid.SliceOfN(rapid.Int(), 1, 10)   // min 1, max 10 elements
rapid.MapOf(rapid.String(), rapid.Int())
```

### Combinators
```go
rapid.OneOf(rapid.Int(), rapid.Int32()) // does not work for different types
rapid.SampledFrom([]string{"a", "b", "c"})
rapid.Just(42)

// Map (transform)
rapid.Map(rapid.Int(), func(x int) int { return x * 2 }) // even integers

// Filter
rapid.Filter(rapid.Int(), func(x int) bool { return x > 0 })
// Prefer: rapid.IntRange(1, math.MaxInt)

// Custom generator (draw pattern)
func userGen(t *rapid.T) User {
    return User{
        Name: rapid.StringN(1, 20, -1).Draw(t, "name"),
        Age:  rapid.IntRange(1, 120).Draw(t, "age"),
    }
}
// Use: rapid.Custom(userGen)
```

## Stateful Testing (rapid)

```go
type storeModel struct {
    items map[string]int
}

func (m *storeModel) Init(t *rapid.T) {
    m.items = make(map[string]int)
}

func (m *storeModel) Put(t *rapid.T) {
    key := rapid.String().Draw(t, "key")
    val := rapid.Int().Draw(t, "val")
    store.Put(key, val)       // real system
    m.items[key] = val        // model
}

func (m *storeModel) Get(t *rapid.T) {
    if len(m.items) == 0 {
        t.Skip("no items")   // precondition
    }
    keys := make([]string, 0, len(m.items))
    for k := range m.items {
        keys = append(keys, k)
    }
    key := rapid.SampledFrom(keys).Draw(t, "key")
    got := store.Get(key)
    if got != m.items[key] {
        t.Fatalf("get(%q): expected %d, got %d", key, m.items[key], got)
    }
}

func (m *storeModel) Check(t *rapid.T) {
    if store.Size() != len(m.items) {
        t.Fatalf("size mismatch: %d vs %d", store.Size(), len(m.items))
    }
}

func TestStore(t *testing.T) {
    rapid.Check(t, rapid.Run[*storeModel]())
}
```

No parallel/linearizability testing in rapid.

## Stateful Testing (gopter)

gopter provides stateful testing via `commands` package:

```go
import (
    "github.com/leanovate/gopter"
    "github.com/leanovate/gopter/commands"
    "github.com/leanovate/gopter/gen"
)

var storeCommands = &commands.ProtoCommands{
    NewSystemUnderTestFunc: func(initialState commands.State) commands.SystemUnderTest {
        return NewMyStore()
    },
    InitialStateGen: gen.Const(map[string]int{}),
    GenCommandFunc: func(state commands.State) gopter.Gen {
        return gen.OneGenOf(
            gen.Struct(reflect.TypeOf(&PutCommand{}), map[string]gopter.Gen{
                "Key": gen.AlphaString(),
                "Val": gen.Int(),
            }),
            gen.Struct(reflect.TypeOf(&GetCommand{}), map[string]gopter.Gen{
                "Key": gen.AlphaString(),
            }),
        )
    },
}

func TestStoreStateful(t *testing.T) {
    parameters := gopter.DefaultTestParameters()
    properties := gopter.NewProperties(parameters)
    properties.Property("store model", commands.Prop(storeCommands))
    properties.TestingRun(t)
}
```

## Generator Cheat Sheet (gopter)

```go
gen.Int()                             // any int
gen.IntRange(0, 100)                  // bounded
gen.Float64()
gen.AlphaString()                     // alphabetic string
gen.AnyString()
gen.Bool()
gen.SliceOf(gen.Int())                // []int
gen.MapOf(gen.AlphaString(), gen.Int())
gen.OneConstOf("a", "b", "c")        // pick from values
gen.OneGenOf(gen.Int(), gen.Int64())  // union of generators
gen.Frequency(
    gen.NewWeightedGen(80, gen.Int()),
    gen.NewWeightedGen(20, gen.Const(0)),
)
gen.Struct(reflect.TypeOf(&User{}), map[string]gopter.Gen{
    "Name": gen.AlphaString(),
    "Age":  gen.IntRange(1, 120),
})
```

## Quick Start (gopter)

```go
func TestSortLength(t *testing.T) {
    properties := gopter.NewProperties(nil)
    properties.Property("sort preserves length", prop.ForAll(
        func(xs []int) bool {
            sorted := make([]int, len(xs))
            copy(sorted, xs)
            sort.Ints(sorted)
            return len(sorted) == len(xs)
        },
        gen.SliceOf(gen.Int()),
    ))
    properties.TestingRun(t)
}
```

## Test Runner Integration

```go
// rapid: go get pgregory.net/rapid
// gopter: go get github.com/leanovate/gopter

// Both integrate with standard go test
// Run: go test ./...
// rapid saves failures to testdata/ for replay
```

## Unique Features

### rapid
- **Idiomatic Go**: Uses `*rapid.T` like Go's `*testing.T`
- **Internal shrinking**: Fully automatic, no user code needed
- **Draw pattern**: Generators called inline (`rapid.Int().Draw(t, "name")`)
- **StateMachine**: Methods on struct define commands; `Init`, `Check` are special

### gopter
- **commands package**: Traditional state machine testing with pre/post conditions
- **gen.Struct**: Generate structs with per-field generators
- **Derived generators**: `DeriveGen` for automatic struct generation
