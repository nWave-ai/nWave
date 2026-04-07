---
name: nw-fp-haskell
agent: nw-functional-software-crafter
description: Haskell language-specific patterns, GADTs, type classes, and effect systems
user-invocable: false
disable-model-invocation: true
---

# FP in Haskell -- Functional Software Crafter Skill

Cross-references: [fp-principles](../nw-fp-principles/SKILL.md) | [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md) | [pbt-haskell](../nw-pbt-haskell/SKILL.md)

## When to Choose Haskell

- Best for: correctness-critical systems | compiler-enforced purity | maximum type safety | financial systems
- Not ideal for: teams needing fast onboarding | rapid prototyping | .NET/JVM platform requirements

## [STARTER] Quick Setup

```bash
# Install GHCup (manages GHC, cabal, stack, HLS)
curl --proto '=https' --tlsv1.2 -sSf https://get-ghcup.haskell.org | sh

# Create project
mkdir order-service && cd order-service && cabal init --interactive
# Or: stack new order-service simple && stack build && stack test
```

**Test runner**: `cabal test` or `stack test`. Add `hspec`, `QuickCheck`, `hedgehog` to `build-depends`.

## [STARTER] Type System for Domain Modeling

### Choice Types (Sum Types)

```haskell
data PaymentMethod
  = CreditCard CardNumber ExpiryDate
  | BankTransfer AccountNumber
  | Cash
  deriving (Eq, Show)
```

### Record Types and Newtypes

```haskell
data Customer = Customer
  { customerId    :: CustomerId
  , customerName  :: CustomerName
  , customerEmail :: EmailAddress
  } deriving (Eq, Show)

newtype OrderId = OrderId Int deriving (Eq, Ord, Show)
newtype EmailAddress = EmailAddress Text deriving (Eq, Show)
```

`newtype` is erased at compile time -- zero runtime overhead, full type safety.

### [STARTER] Validated Construction (Smart Constructors)

```haskell
module Domain.Email (EmailAddress, mkEmailAddress, emailToText) where

import Data.Text (Text)
import qualified Data.Text as T

newtype EmailAddress = EmailAddress Text deriving (Eq, Show)

mkEmailAddress :: Text -> Either ValidationError EmailAddress
mkEmailAddress raw
  | "@" `T.isInfixOf` raw = Right (EmailAddress raw)
  | otherwise              = Left (InvalidEmail raw)
```

Export the type but not the constructor. Only `mkEmailAddress` can create values.

## [INTERMEDIATE] Composition Style

### Function Composition (Right-to-Left)

```haskell
-- (.) composes right-to-left
processOrder :: RawOrder -> Either OrderError Confirmation
processOrder = confirmOrder . priceOrder . validateOrder
```

### Monadic Chaining with do-notation

```haskell
placeOrder :: RawOrder -> Either OrderError Confirmation
placeOrder raw = do
  validated <- validateOrder raw
  priced    <- priceOrder validated
  confirmOrder priced
```

### Applicative for Independent Validation

```haskell
mkCustomer :: Text -> Text -> Either ValidationError Customer
mkCustomer rawName rawEmail =
  Customer
    <$> mkCustomerId 0
    <*> mkCustomerName rawName
    <*> mkEmailAddress rawEmail
```

### Error-Accumulating Validation

```haskell
import Data.Validation (Validation, failure, success)

mkCustomerV :: Text -> Text -> Validation [ValidationError] Customer
mkCustomerV rawName rawEmail =
  Customer
    <$> validateName rawName    -- Validation [ValidationError] CustomerName
    <*> validateEmail rawEmail  -- all errors collected, not short-circuited
```

Unlike `Either` which stops at first error, `Validation` accumulates all failures via its `Applicative` instance.

## [INTERMEDIATE] Effect Management

Haskell enforces purity at the compiler level. `IO` in return type means side effects.

```haskell
calculateTotal :: Order -> Money           -- Pure: compiler guarantees no side effects
calculateTotal order = sumOf (orderLines order)

saveOrder :: Order -> IO ()                -- Impure: IO in the type
saveOrder order = writeToDatabase order
-- calculateTotal CANNOT call saveOrder -- compiler error
```

### [ADVANCED] Three Layers Pattern (Hexagonal Architecture)

```haskell
-- Layer 1: Pure domain (no IO, no effects)
module Domain.Order (calculateDiscount, validateOrder) where
calculateDiscount :: Order -> Discount
calculateDiscount order
  | totalLines order > 10 = Discount 0.1
  | otherwise              = Discount 0.0

-- Layer 2: Effect interfaces (type classes as ports)
class Monad m => OrderRepo m where
  findOrder :: OrderId -> m (Maybe Order)
  saveOrder :: Order -> m ()

-- Layer 3: IO implementations (adapters)
instance OrderRepo IO where
  findOrder orderId = queryDatabase orderId
  saveOrder order   = insertDatabase order
```

**Effect libraries**: Effectful (recommended starting point, best performance) | mtl (existing codebases) | Polysemy (algebraic effect semantics).

## [INTERMEDIATE] Testing

**Frameworks**: QuickCheck (original PBT) | Hedgehog (integrated shrinking) | Hspec (BDD) | tasty (composable test tree). See [pbt-haskell](../nw-pbt-haskell/SKILL.md) for detailed PBT patterns.

### Property Test Example

```haskell
import Test.Hspec
import Test.QuickCheck

spec :: Spec
spec = describe "validateOrder" $ do
  it "round-trips through serialization" $
    property $ \order ->
      deserializeOrder (serializeOrder order) === Right order

  it "validated orders always have positive totals" $
    property $ \rawOrder ->
      case validateOrder rawOrder of
        Left _      -> discard
        Right valid -> orderTotal valid > Money 0
```

### Custom Generator

```haskell
import Data.Text (pack)
import Test.QuickCheck

genValidEmail :: Gen EmailAddress
genValidEmail = do
  user   <- listOf1 (elements ['a'..'z'])
  domain <- listOf1 (elements ['a'..'z'])
  pure (EmailAddress (pack (user ++ "@" ++ domain ++ ".com")))
```

## [ADVANCED] Idiomatic Patterns

### GADTs for State Machines

```haskell
{-# LANGUAGE GADTs, DataKinds #-}

data OrderState = Unvalidated | Validated | Priced

data Order (s :: OrderState) where
  UnvalidatedOrder :: RawData -> Order 'Unvalidated
  ValidatedOrder   :: ValidData -> Order 'Validated
  PricedOrder      :: PricedData -> Order 'Priced

-- Type-safe transitions: only validated orders can be priced
priceOrder :: Order 'Validated -> Either PricingError (Order 'Priced)
priceOrder (ValidatedOrder d) = Right (PricedOrder (addPricing d))
```

### Lazy Evaluation for Decoupled Pipelines

```haskell
eligibleOrders :: [Order] -> [Order]
eligibleOrders = take 10 . filter isEligible . sortBy orderDate
```

## Maturity and Adoption

- **Steep learning curve**: Monads, type classes, category-theory vocabulary create significant onboarding barrier. Budget extra ramp-up time.
- **GHC extensions confusion**: Over 100 language extensions; knowing which to enable requires experience. Start with `GHC2021` defaults.
- **Space leaks from laziness**: Default lazy evaluation causes subtle memory issues. Requires profiling discipline and strict annotations.
- **Smaller talent pool**: Hiring Haskell developers harder than mainstream languages. Consider team sustainability before committing.

## Common Pitfalls

1. **Lazy space leaks**: Use `foldl'` (strict) instead of `foldl`. Use `BangPatterns` for strict accumulators.
2. **String vs Text**: Never use `String` ([Char]) for real data. Use `Data.Text` / `Data.ByteString`.
3. **Orphan instances**: Define instances in the module of the type or class. Use newtype wrappers otherwise.
4. **Over-abstracting with type-level programming**: GADTs and type families increase compile times and error complexity. Use for genuine safety gains.
