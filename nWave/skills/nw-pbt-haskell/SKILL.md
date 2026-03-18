---
name: nw-pbt-haskell
agent: nw-functional-software-crafter
description: Haskell property-based testing with QuickCheck and Hedgehog frameworks
disable-model-invocation: true
---

# PBT Haskell -- QuickCheck + Hedgehog

## Framework Selection

| Framework | Shrinking | Stateful | Choose When |
|-----------|-----------|----------|-------------|
| QuickCheck | Type-based (manual) | Limited (open-source) | Default for most projects. Universal ecosystem support. |
| Hedgehog | Integrated (automatic) | Yes (parallel too) | Need automatic shrinking composition or parallel stateful testing |

QuickCheck is the original PBT framework (2000). Hedgehog is the modern alternative with better shrinking.

## Quick Start (QuickCheck)

```haskell
import Test.QuickCheck

prop_reverse_involutory :: [Int] -> Bool
prop_reverse_involutory xs = reverse (reverse xs) == xs

-- Run: quickCheck prop_reverse_involutory
-- Or in test suite: testProperty "reverse" prop_reverse_involutory
```

## Generator Cheat Sheet (QuickCheck)

### Via Arbitrary Type Class
```haskell
arbitrary :: Gen Int       -- any Int
arbitrary :: Gen String    -- any String
arbitrary :: Gen [Int]     -- any list of Ints
arbitrary :: Gen Bool

-- Custom Arbitrary
data Color = Red | Green | Blue deriving (Show, Eq)

instance Arbitrary Color where
  arbitrary = elements [Red, Green, Blue]
  shrink Red = []
  shrink _   = [Red]
```

### Gen Combinators
```haskell
choose (0, 100)              -- bounded int
elements [1, 2, 3]           -- pick from list
oneof [gen1, gen2]           -- union
frequency [(80, gen1), (20, gen2)]  -- weighted

listOf arbitrary             -- list
listOf1 arbitrary            -- non-empty list
vectorOf 5 arbitrary         -- fixed-length list

-- Map
fmap (* 2) arbitrary         -- even integers

-- Bind (dependent generation)
do xs <- listOf1 arbitrary
   x  <- elements xs
   return (xs, x)

-- Sized
sized $ \n -> resize (n `div` 2) arbitrary
```

### Shrinking
```haskell
instance Arbitrary MyType where
  arbitrary = ...
  shrink (MyType a b) = [MyType a' b | a' <- shrink a]
                     ++ [MyType a b' | b' <- shrink b]
```

## Stateful Testing (QuickCheck)

Not supported in open-source QuickCheck. Use Hedgehog for stateful testing, or commercial Quviq QuickCheck (Erlang).

## Quick Start (Hedgehog)

```haskell
import Hedgehog
import qualified Hedgehog.Gen as Gen
import qualified Hedgehog.Range as Range

prop_reverse :: Property
prop_reverse = property $ do
  xs <- forAll $ Gen.list (Range.linear 0 100) Gen.alpha
  reverse (reverse xs) === xs

-- Run: check prop_reverse
```

## Generator Cheat Sheet (Hedgehog)

```haskell
Gen.int (Range.linear 0 100)
Gen.int (Range.constant 0 100)    -- no size scaling
Gen.double (Range.linearFrac 0 1)
Gen.string (Range.linear 0 50) Gen.alpha
Gen.bool
Gen.element [Red, Green, Blue]

-- Collections
Gen.list (Range.linear 0 50) Gen.alpha
Gen.nonEmpty (Range.linear 1 50) Gen.alpha
Gen.set (Range.linear 0 20) Gen.int

-- Map
Gen.int (Range.linear 0 100) <&> (* 2)

-- Filter
Gen.filter (> 0) (Gen.int (Range.linear minBound maxBound))

-- Recursive
Gen.recursive Gen.choice
  [ Gen.constant Leaf ]
  [ Node <$> genTree <*> Gen.int (Range.linear 0 100) <*> genTree ]
```

### Hedgehog Ranges
```haskell
Range.linear 0 100       -- scales with size parameter
Range.constant 0 100     -- fixed bounds, no scaling
Range.linearFrac 0.0 1.0 -- fractional, scales with size
Range.singleton 42       -- always 42
```

## Stateful Testing (Hedgehog)

Hedgehog supports sequential and parallel state machine testing.

```haskell
import qualified Hedgehog.Gen as Gen
import qualified Hedgehog.Range as Range
import Hedgehog
import Hedgehog.Internal.State

-- Define state and commands
newtype ModelState (v :: * -> *) = ModelState { items :: Map String Int }

data Put (v :: * -> *) = Put String Int deriving (Show, Eq)
data Get (v :: * -> *) = Get String     deriving (Show, Eq)

instance HTraversable Put where
  htraverse _ (Put k v) = pure (Put k v)
instance HTraversable Get where
  htraverse _ (Get k) = pure (Get k)

cPut :: (MonadGen n, MonadIO m, MonadTest m) => Command n m ModelState
cPut = Command
  (\state -> Just $ Put <$> Gen.string (Range.linear 1 10) Gen.alpha
                        <*> Gen.int (Range.linear 0 100))
  (\(Put k v) -> liftIO $ storePut realStore k v)
  [ Update $ \(ModelState m) (Put k v) _out -> ModelState (Map.insert k v m)
  ]

cGet :: (MonadGen n, MonadIO m, MonadTest m) => Command n m ModelState
cGet = Command
  (\(ModelState m) -> if Map.null m then Nothing
                      else Just $ Get <$> Gen.element (Map.keys m))
  (\(Get k) -> liftIO $ storeGet realStore k)
  [ Ensure $ \(ModelState before) _after (Get k) out ->
      out === Map.lookup k before
  ]

prop_store :: Property
prop_store = property $ do
  actions <- forAll $ Gen.sequential (Range.linear 1 50)
    (ModelState Map.empty) [cPut, cGet]
  executeSequential (ModelState Map.empty) actions
```

For parallel testing, replace `Gen.sequential` with `Gen.parallel` and `executeSequential` with `executeParallel`. Checks linearizability of concurrent operations.

## Test Runner Integration

### QuickCheck
```haskell
-- With HSpec
describe "sort" $ do
  it "preserves length" $ property $
    \(xs :: [Int]) -> length (sort xs) == length xs

-- With Tasty
testGroup "sort" [ testProperty "length" prop_sortLength ]

-- Cabal/Stack: depends on QuickCheck, hspec-discover or tasty
```

### Hedgehog
```haskell
-- With Tasty
testGroup "sort" [ Hedgehog.testProperty "length" prop_sortLength ]

-- Cabal/Stack: depends on hedgehog, tasty-hedgehog
```

## Unique Features

### QuickCheck
- **The original**: 25+ years, every Haskell test framework integrates with it
- **Arbitrary type class**: One generator per type, automatic derivation via Generic
- **Quviq commercial version**: Most complete PBT implementation ever built (Erlang)

### Hedgehog
- **Integrated shrinking**: Automatic via rose trees, composes through applicative
- **No orphan instances**: Explicit generators avoid type class problem
- **Range combinators**: Fine control over value scaling with size
- **Parallel stateful testing**: Built-in linearizability checking
