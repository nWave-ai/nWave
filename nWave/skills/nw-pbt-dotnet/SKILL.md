---
name: nw-pbt-dotnet
agent: nw-functional-software-crafter
description: ".NET property-based testing with FsCheck, CsCheck, and fsharp-hedgehog. Load when writing property-based tests in C# or F# or choosing a .NET PBT framework."
user-invocable: false
disable-model-invocation: true
---

# PBT .NET -- FsCheck + CsCheck (C#/F#)

## Framework Selection

| Framework | Language | Shrinking | Stateful | Parallel | Choose When |
|-----------|----------|-----------|----------|----------|-------------|
| FsCheck | C#/F# | Type-based | No | No | F#-first projects, or C# needing mature PBT |
| CsCheck | C# | PCG-based | Yes | Yes (linearizability) | C# projects needing concurrent testing |
| fsharp-hedgehog | F# | Integrated | No | No | F# projects wanting modern integrated shrinking |

**C# default**: CsCheck (better shrinking, stateful + parallel). **F# default**: FsCheck or fsharp-hedgehog.

## Quick Start (FsCheck)

```csharp
// C#
using FsCheck; using FsCheck.Xunit;

public class SortProperties
{
    [Property]
    public bool SortPreservesLength(List<int> xs) =>
        xs.OrderBy(x => x).Count() == xs.Count;
}
```

```fsharp
// F#
open FsCheck

let propSortIdempotent (xs: int list) =
    List.sort (List.sort xs) = List.sort xs

Check.Quick propSortIdempotent
```

## Generator Cheat Sheet (FsCheck)

### C#
```csharp
Arb.Generate<int>()                    // any int
Gen.Choose(0, 100)                     // bounded
Arb.Generate<string>()
Arb.Generate<List<int>>()

// Custom generator
public static Arbitrary<Email> EmailArb() =>
    Arb.From(
        from name in Arb.Generate<NonEmptyString>()
        select new Email($"{name}@example.com")
    );

Arb.Register<MyGenerators>();          // register custom arbitraries
```

### F#
```fsharp
Gen.choose (0, 100)
Gen.elements [1; 2; 3]
Gen.oneof [gen1; gen2]
Gen.frequency [(80, gen1); (20, gen2)]
Gen.listOf (Gen.choose (0, 100))

Gen.choose (0, 100) |> Gen.map (fun x -> x * 2)

gen {
    let! xs = Gen.listOf (Gen.choose (0, 100))
    let! x = Gen.elements xs
    return (xs, x)
}
```

## Quick Start (CsCheck)

```csharp
using CsCheck;

[Fact]
public void Sort_Preserves_Length()
{
    Gen.Int.Array
       .Sample(arr => arr.OrderBy(x => x).Count() == arr.Length);
}
```

### CsCheck Generators
```csharp
Gen.Int                                // any int
Gen.Int[0, 100]                        // bounded
Gen.Double
Gen.String
Gen.Bool
Gen.Int.Array                          // int[]
Gen.Int.List                           // List<int>
Gen.Int.HashSet                        // HashSet<int>
Gen.Int.Select(x => x * 2)            // map
Gen.Select(Gen.String, Gen.Int, (name, age) => new User(name, age))
Gen.OneOf(Gen.Int.Select(x => (object)x), Gen.String.Select(x => (object)x))
Gen.Int.Where(x => x > 0)             // filter
```

## Stateful Testing

FsCheck: No stateful testing support. Use CsCheck for stateful and parallel testing.
fsharp-hedgehog: No stateful testing support.

### CsCheck Stateful Testing

```csharp
[Fact]
public void Store_Matches_Model()
{
    Gen.Int.List[0, 100].Sample(operations =>
    {
        var store = new MyStore();
        var model = new Dictionary<string, int>();
        // CsCheck uses operation sequences with Check.Sample
    });
}
```

### CsCheck Parallel/Linearizability Testing

```csharp
[Fact]
public void Store_Is_Linearizable()
{
    Check.SampleConcurrent(
        Gen.Operation<MyStore>(/* ... */),
        initialState: () => new MyStore()
    );
}
```

`Check.SampleConcurrent` runs operations sequentially then in parallel, checking against all possible linearizations. Shrinking works for parallel failures -- rare among PBT frameworks.

## Quick Start (fsharp-hedgehog)

```fsharp
open Hedgehog

let propReverse = property {
    let! xs = Gen.list (Range.linear 0 100) Gen.alpha
    return List.rev (List.rev xs) = xs
}

Property.check propReverse
```

### fsharp-hedgehog Generators
```fsharp
Gen.int (Range.linear 0 100)
Gen.string (Range.linear 0 50) Gen.alpha
Gen.bool
Gen.list (Range.linear 0 50) (Gen.int (Range.linear 0 100))
Gen.option (Gen.int (Range.linear 0 100))
```

## Test Runner Integration

```xml
<!-- FsCheck -->
<PackageReference Include="FsCheck.Xunit" Version="3.0.0" />
<!-- CsCheck -->
<PackageReference Include="CsCheck" Version="4.0.0" />
<!-- fsharp-hedgehog -->
<PackageReference Include="Hedgehog" Version="0.13.0" />
<PackageReference Include="Hedgehog.Xunit" Version="0.5.0" />
<!-- All work with xUnit, NUnit, MSTest (CsCheck/FsCheck) -->
```

## Unique Features

### FsCheck
- **F# + C# + VB.NET**: Works across all .NET languages
- **Arb<T> type class**: Type-based generation/shrinking, automatic derivation
- **v3 stable**: Major rewrite with improved API and performance
- **Conditional properties**: `Prop.When` for preconditions with automatic discard tracking
- **Model-based testing**: `Prop.ForAll` with `Command` for lightweight model checking
- **Observable properties**: Distribution analysis via `Prop.Collect` and `Prop.Classify`

### CsCheck
- **Parallel linearizability testing**: `Check.SampleConcurrent` -- rare capability
- **PCG-based shrinking**: Parallelizable, fast, reproducible
- **Performance testing**: Built-in `Check.Faster` for comparative benchmarks
- **Causal profiling**: Built-in `Check.CausalProfiling`

### fsharp-hedgehog
- **Computation expressions**: `gen { }`, `property { }` -- most readable F# PBT syntax
- **Integrated shrinking**: Automatic via rose trees
- **Hedgehog.Experimental**: Auto-generators (AutoFixture-like)
