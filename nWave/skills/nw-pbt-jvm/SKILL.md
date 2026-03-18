---
name: nw-pbt-jvm
agent: nw-functional-software-crafter
description: JVM property-based testing with jqwik, ScalaCheck, and ZIO Test frameworks
disable-model-invocation: true
---

# PBT JVM -- jqwik (Java/Kotlin) + ScalaCheck + ZIO Test

## Framework Selection

| Framework | Language | Shrinking | Stateful | Choose When |
|-----------|----------|-----------|----------|-------------|
| jqwik | Java/Kotlin | Integrated | Yes (actions) | Java/Kotlin projects (recommended default) |
| ScalaCheck | Scala | Type-based | Yes (Commands) | Scala projects (established choice) |
| ZIO Test | Scala | Integrated | Via effects | ZIO-based Scala projects |

## Quick Start (jqwik)

```java
import net.jqwik.api.*;

class SortProperties {
    @Property
    void sortPreservesLength(@ForAll List<Integer> list) {
        List<Integer> sorted = new ArrayList<>(list);
        Collections.sort(sorted);
        Assertions.assertEquals(list.size(), sorted.size());
    }
}
// Run: ./gradlew test (or mvn test)
```

## Generator (Arbitrary) Cheat Sheet (jqwik)

```java
@ForAll int x                          // any int
@ForAll @IntRange(min = 0, max = 99) int x
@ForAll @StringLength(min = 1, max = 50) String s
@ForAll @Size(min = 1, max = 10) List<Integer> list

// Custom provider
@Provide
Arbitrary<String> emails() {
    return Arbitraries.strings().alpha().ofMinLength(1).ofMaxLength(10)
        .map(name -> name + "@example.com");
}

// Combinators
Arbitraries.integers().between(0, 100)
Arbitraries.of("a", "b", "c")
Arbitraries.frequencyOf(Tuple.of(80, Arbitraries.integers()), Tuple.of(20, Arbitraries.just(0)))

// Combine
Combinators.combine(
    Arbitraries.strings().alpha().ofMinLength(1),
    Arbitraries.integers().between(1, 120)
).as((name, age) -> new User(name, age))

// Recursive
Arbitraries.recursive(
    () -> Arbitraries.of(JsonValue.NULL, JsonValue.TRUE),
    inner -> Arbitraries.maps(Arbitraries.strings(), inner).map(JsonValue::fromMap),
    5
)
```

## Stateful Testing (jqwik)

```java
@Property
void storeMatchesModel(@ForAll("storeActions") ActionSequence<MyStore> actions) {
    actions.run(new MyStore());
}

@Provide
ActionSequenceArbitrary<MyStore> storeActions() {
    return Arbitraries.sequences(
        Arbitraries.oneOf(
            Combinators.combine(Arbitraries.strings(), Arbitraries.integers())
                .as(PutAction::new),
            Arbitraries.strings().map(GetAction::new)
        )
    );
}

class PutAction implements Action<MyStore> {
    final String key; final int value;
    PutAction(String key, int value) { this.key = key; this.value = value; }
    @Override public MyStore run(MyStore store) { store.put(key, value); return store; }
}
```

## Quick Start (ScalaCheck)

```scala
import org.scalacheck.Prop.forAll

val propSortLength = forAll { (xs: List[Int]) => xs.sorted.length == xs.length }

// With ScalaTest
class SortSpec extends AnyFunSuite with ScalaCheckPropertyChecks {
  test("sort idempotent") { forAll { (xs: List[Int]) => xs.sorted.sorted shouldBe xs.sorted } }
}
```

### ScalaCheck Generators
```scala
Gen.choose(0, 100)                    // bounded int
Gen.alphaStr                          // alphabetic string
Gen.listOf(Gen.posNum[Int])           // list
Gen.oneOf(Gen.const(1), Gen.const(2)) // union
Gen.frequency((80, Gen.alphaChar), (20, Gen.numChar))
Gen.recursive[Tree](gen =>
  Gen.oneOf(Gen.const(Leaf), for { l <- gen; r <- gen; v <- Gen.posNum[Int] } yield Node(v, l, r))
)
```

### ScalaCheck Stateful (Commands)
```scala
object StoreSpec extends Commands {
  type State = Map[String, Int]; type Sut = MyStore
  def genCommand(state: State): Gen[Command] = Gen.oneOf(
    for { k <- Gen.alphaStr; v <- Gen.posNum[Int] } yield Put(k, v),
    Gen.oneOf(state.keys.toSeq).map(Get(_))
  )
}
```

## Quick Start (ZIO Test)

```scala
import zio.test._

test("sort preserves length") {
  check(Gen.listOf(Gen.int)) { xs => assertTrue(xs.sorted.length == xs.length) }
}
```

### ZIO Test Generator Cheat Sheet
```scala
Gen.int                               // any Int
Gen.int(0, 100)                       // bounded
Gen.double                            // any Double
Gen.string                            // any String
Gen.alphaNumericString
Gen.boolean
Gen.listOf(Gen.int)                   // List[Int]
Gen.setOf(Gen.string)                 // Set[String]
Gen.mapOf(Gen.string, Gen.int)        // Map[String, Int]
Gen.option(Gen.int)                   // Option[Int]
Gen.oneOf(Gen.const(1), Gen.const(2)) // union
Gen.weighted((Gen.int, 80.0), (Gen.const(0), 20.0))  // weighted

// Custom
val genUser = for {
  name <- Gen.alphaNumericString
  age  <- Gen.int(1, 120)
} yield User(name, age)
```

ZIO Test stateful testing: Use `ZIO.stateful` with Ref-based model state in effect composition.

## Test Runner Integration

```xml
<!-- jqwik (Maven) -->
<dependency>
    <groupId>net.jqwik</groupId><artifactId>jqwik</artifactId>
    <version>1.8.0</version><scope>test</scope>
</dependency>
```
```scala
// ScalaCheck (build.sbt)
libraryDependencies += "org.scalacheck" %% "scalacheck" % "1.17.0" % Test
// ZIO Test: "dev.zio" %% "zio-test" % "2.x" % Test
```

## Unique Features

### jqwik
- **Edge cases**: Automatically tests boundary values (0, MIN/MAX, empty)
- **@StatisticsReport**: Shows distribution of generated values
- **Domains**: Group related arbitraries into reusable contexts
- **Kotlin support**: Works natively via JUnit 5

### ScalaCheck
- **Type-class based**: `Arbitrary[T]` for automatic derivation
- **Parallel Commands**: Stateful testing with parallel execution
- **Shrink[T]**: Separate shrink type class (can shrink past generator constraints)
