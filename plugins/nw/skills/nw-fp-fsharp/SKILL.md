---
name: nw-fp-fsharp
agent: nw-functional-software-crafter
description: F# language-specific patterns, Railway-Oriented Programming, and Computation Expressions
user-invocable: false
disable-model-invocation: true
---

# FP in F# -- Functional Software Crafter Skill

Cross-references: [fp-principles](../nw-fp-principles/SKILL.md) | [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md) | [pbt-dotnet](../nw-pbt-dotnet/SKILL.md)

## When to Choose F#

- Best for: domain modeling on .NET | DDD | railway-oriented programming | pipeline-first design | finance
- Not ideal for: teams needing higher-kinded types | non-.NET platforms | large existing C# codebases resistant to change

## [STARTER] Quick Setup

```bash
dotnet new console -lang F# -o OrderService && cd OrderService
dotnet new xunit -lang F# -o OrderService.Tests
dotnet add OrderService.Tests reference OrderService
dotnet add OrderService.Tests package FsCheck.Xunit
dotnet test
```

**File order matters**: F# compiles files top-to-bottom as listed in `.fsproj`. Types must be defined before use.

## [STARTER] Type System for Domain Modeling

### Choice Types (Discriminated Unions)

```fsharp
type PaymentMethod =
    | CreditCard of cardNumber: string * expiryDate: string
    | BankTransfer of accountNumber: string
    | Cash
```

### Record Types and Domain Wrappers

```fsharp
type Customer = {
    CustomerId: CustomerId
    CustomerName: CustomerName
    CustomerEmail: EmailAddress
}

type OrderId = OrderId of int
type EmailAddress = EmailAddress of string
```

Records have structural equality by default. Single-case DUs have small runtime cost (unlike Haskell's zero-cost newtype).

### [STARTER] Validated Construction (Smart Constructors)

```fsharp
module EmailAddress =
    let create (rawEmail: string) : Result<EmailAddress, string> =
        if rawEmail.Contains("@") then Ok (EmailAddress rawEmail)
        else Error $"Invalid email: {rawEmail}"

    let value (EmailAddress email) = email
```

## [INTERMEDIATE] Composition Style

### Pipeline Operator (The Defining Feature)

```fsharp
let processOrder rawOrder =
    rawOrder
    |> validateOrder
    |> Result.bind priceOrder
    |> Result.bind confirmOrder
    |> Result.map generateReceipt
```

**Data-last convention**: F# functions put primary input last so they compose with `|>`.

### Railway-Oriented Programming (Error-Track Pipelines)

```fsharp
let placeOrder unvalidatedOrder =
    unvalidatedOrder
    |> validateOrder
    |> Result.bind priceOrder
    |> Result.bind confirmOrder
    |> Result.mapError PlaceOrderError.Validation
```

### Computation Expressions for Monadic Syntax

```fsharp
open FsToolkit.ErrorHandling

let placeOrder rawOrder = result {
    let! validated = validateOrder rawOrder
    let! priced = priceOrder validated
    return! confirmOrder priced
}
```

Key builders: `result { }` (error-track) | `async { }` (async I/O) | `task { }` (.NET Task interop) | `validation { }` (accumulate errors, FsToolkit).

## [INTERMEDIATE] Effect Management

F# is impure by default. Purity maintained by architectural convention, not the compiler.

### Pure Core / Imperative Shell

```fsharp
// Pure domain logic (no I/O, no mutation)
module Domain =
    let calculateDiscount (order: Order) : Discount =
        if List.length order.OrderLines > 10 then Discount 0.1m
        else Discount 0.0m

// Imperative shell (I/O at edges)
module App =
    let placeOrderHandler (deps: Dependencies) (rawOrder: UnvalidatedOrder) = async {
        let! result =
            rawOrder
            |> Domain.validateOrder deps.CheckProductExists
            |> Result.bind (Domain.priceOrder deps.GetProductPrice)
        do! deps.SaveOrder result
        return result
    }
```

### [ADVANCED] Hexagonal Architecture via Partial Application

```fsharp
// Ports as function types
type FindOrder = OrderId -> Async<Order option>
type SaveOrder = Order -> Async<unit>

// Adapter: concrete implementation
let findOrderInDb (connStr: string) (orderId: OrderId) : Async<Order option> =
    async { (* database query *) }

// Composition root: partially apply dependencies
let findOrder = findOrderInDb "Server=localhost;Database=orders"
```

Dependencies first, primary input last. Partially apply at composition root.

## [INTERMEDIATE] Testing

**Frameworks**: FsCheck (QuickCheck port) | fsharp-hedgehog (integrated shrinking) | Expecto (F#-native) | Unquote (assertions). See [pbt-dotnet](../nw-pbt-dotnet/SKILL.md) for detailed PBT patterns.

### Property Test Example (FsCheck + xUnit)

```fsharp
open FsCheck.Xunit

[<Property>]
let ``validated orders always have positive totals`` (rawOrder: RawOrder) =
    match validateOrder rawOrder with
    | Error _ -> true
    | Ok valid -> orderTotal valid > Money 0m

[<Property>]
let ``serialization round-trips`` (order: Order) =
    order |> serialize |> deserialize = Ok order
```

### Custom Generator

```fsharp
let genValidEmail = gen {
    let! user = Gen.nonEmptyListOf (Gen.elements ['a'..'z']) |> Gen.map (fun cs -> System.String(Array.ofList cs))
    let! domain = Gen.nonEmptyListOf (Gen.elements ['a'..'z']) |> Gen.map (fun cs -> System.String(Array.ofList cs))
    return EmailAddress $"{user}@{domain}.com"
}
```

## [ADVANCED] Idiomatic Patterns

### Document Lifecycle as Separate Types

```fsharp
type UnvalidatedOrder = { RawName: string; RawEmail: string; RawLines: string list }
type ValidatedOrder = { Name: CustomerName; Email: EmailAddress; Lines: OrderLine list }
type PricedOrder = { ValidOrder: ValidatedOrder; Total: Money; Lines: PricedOrderLine list }
```

Each stage is a distinct type. Pipeline transforms one into the next.

### Collect-All-Errors Validation

```fsharp
open FsToolkit.ErrorHandling

let validateCustomer (raw: RawCustomer) = validation {
    let! name = validateName raw.Name
    and! email = validateEmail raw.Email
    and! address = validateAddress raw.Address
    return { Name = name; Email = email; Address = address }
}
```

**Project structure**: Domain types/workflows in `OrderService.Domain/` | adapters in `OrderService.Infrastructure/` | composition root in `OrderService.App/`. File ordering in `.fsproj` defines compilation order.

## Maturity and Adoption

- **.NET dependency**: Deployment outside .NET (native, WASM) is limited. Tooling improvements lag behind C#.
- **Smaller community**: Fewer libraries, tutorials, Stack Overflow answers than C#. Community is helpful but small.
- **File ordering constraint**: Top-to-bottom compilation prevents circular dependencies (benefit) but frustrates developers used to free ordering. Refactoring file order is a real cost.
- **Second-class .NET citizen**: New .NET features (Blazor, MAUI) often ship C#-first with delayed or incomplete F# support.

## Common Pitfalls

1. **File order dependency**: Types in `B.fs` cannot reference `A.fs` if `A.fs` listed after `B.fs`. Reorder files when adding dependencies.
2. **No higher-kinded types**: Cannot abstract over `Result<_,_>` vs `Option<_>` generically. Use concrete types or computation expressions.
3. **.NET OO pressure**: C# interop pushes toward classes. Resist: use modules, records, and DUs as primary modeling tools.
4. **Forgetting Result.mapError**: When composing steps with different error types, unify with `Result.mapError` before `Result.bind`.
