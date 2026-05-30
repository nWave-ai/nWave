---
name: nw-tpp-methodology
agent: nw-software-crafter
description: Transformation Priority Premise + ZOMBIES — two heuristics for choosing the next test to write, both prioritizing the test that drives the simplest transformation. Applies during the RED phase of outside-in TDD.
user-invocable: false
disable-model-invocation: true
---

# Transformation Priority Premise (TPP) + ZOMBIES

Companion to `nw-tdd-methodology`. The TDD cycle tells you *to* write a failing
test then make it pass. It does not tell you **which test to write next**. TPP
and ZOMBIES both answer exactly that question, and they answer it the same way:

> **Choose the next test that can be satisfied by the simplest transformation.**

Both are test-selection heuristics that apply during the **RED phase** of nWave's
canonical RED → GREEN → COMMIT cycle (owned by `nw-tdd-methodology` — this skill
defers to it and does not redefine it). Neither is about picking the
production-code change after the test is chosen — they are about *ordering the
tests* so that each step requires only the smallest possible generalization of
the code.

Core principle (Robert C. Martin): **as the tests get more specific, the code
gets more generic.** (Martin uses "generic" and "general" interchangeably for
this; "The Cycles of TDD" section heading is the written canon — "Generic.") You
steer that progression by selecting tests in order of the transformation they
demand — simplest first.

Sources:
- TPP (original) — https://blog.cleancoder.com/uncle-bob/2013/05/27/TheTransformationPriorityPremise.html
- TPP & test ordering — "The Cycles of TDD" — https://blog.cleancoder.com/uncle-bob/2014/12/17/TheCyclesOfTDD.html
- TPP applied to sorting (comic-form companion) — https://blog.cleancoder.com/uncle-bob/2013/05/27/TransformationPriorityAndSorting.html
- Robert C. Martin, "The Transformation Priority Premise" talk, NDC 2011 (video) — https://www.youtube.com/watch?v=B93QezwTQpI
- ZOMBIES — https://blog.wingman-sw.com/tdd-guided-by-zombies (James Grenning)
- Jeff Langr, *Modern C++ Programming with Test-Driven Development* (Pragmatic Bookshelf) — https://pragprog.com/titles/lotdd/modern-c-programming-with-test-driven-development/ — works TPP through a full algorithm and stresses test-list discipline and pragmatic impasse handling (the test-list, rule-bending, and deferral points below draw on it)

---

## Part 1 — TPP: rank the transformations, pick the test that needs the simplest

The Transformation Priority Premise ranks the *transformations* a passing test
can force on the code, from simplest to most complex. The premise is that when
deciding the next test, you should **prefer the test whose passing requires the
highest-priority (simplest) transformation still available**. The ranking is the
selection criterion for the test — not a menu for hacking code to green.

| # | Transformation | Notation | A test at this rank forces… |
|---|----------------|----------|------------------------------|
| 1 | nothing → nil | `{} → nil` | code to exist at all, returning nil/null |
| 2 | nil → constant | `nil → constant` | a fixed constant value |
| 3 | constant → richer constant | `constant → constant+` | a simple constant to become a more complex one |
| 4 | constant → scalar | `constant → scalar` | a constant to become a variable / argument |
| 5 | statement → statements | `statement → statements` | more unconditional statements |
| 6 | unconditional → conditional | `unconditional → if` | the execution path to split with `if` |
| 7 | scalar → array | `scalar → array` | a variable to become an array |
| 8 | array → container | `array → container` | an array to become a richer container (list/map/set) |
| 9 | statement → tail-recursion | `statement → tail-recursion` | tail recursion |
| 10 | if → while | `if → while` | a conditional to become a loop |
| 11 | statement → non-tail recursion | `statement → recursion` | general (non-tail) recursion |
| 12 | expression → function | `expression → function` | an expression to become a function/algorithm |
| 13 | variable → assignment | `variable → assignment` | a variable's value to be reassigned / mutated |
| 14 | add a case | `case` | a new case / else added to an existing switch or if |

This is the canonical 14-transformation list from the original article (recursion
splits into **tail-recursion at rank 9, before `if → while`**, and **non-tail
recursion at rank 11, after** it; rank 14 `case` is easy to forget). Uncle Bob
notes the ordering is **language-specific** — in an imperative language like Java
you may rank iteration (`if → while`) and assignment above recursion — and that
"there are likely others." Treat the ranks as a strong default, not a law.

### The premise — how to use it

- When several candidate tests remain, **write the one that drives the
  highest-priority transformation** in the list above.
- Prefer the top of the list. A test that only needs `nil → constant` comes
  before one that needs `if → while`.
- If the only test you can think of would force a low-priority transformation
  (recursion, while, function) early, that is a signal a **simpler test is
  missing** — find and write that one first.
- **Keep a running test list.** TPP works by *scanning* the behaviors you have
  not tested yet and choosing the one whose transformation ranks highest; a
  visible backlog is what makes that comparison possible. Maintain the list, pick
  the highest-priority item from it, and add to it as new behaviors surface
  (Langr treats a maintained test list as near-essential to TPP — see Sources).

Why select tests this way:

- it produces **simpler designs** — the code grows by the smallest generalization
  each time (a constant before a scalar, an `if` before a `while`);
- it **avoids getting stuck** — a premature low-priority test can force an
  algorithm into a corner a simpler ordering would have avoided;
- it keeps every step **minimal and reversible**, preserving the always-green bar.

### The decision-point rule — and the sort example

TPP's sharpest use is at a **decision point**: when more than one transformation
could make the failing test pass, choose the one **higher on the list**. In his
NDC 2011 talk Uncle Bob shows why with a sort. At "two elements out of order" you
can either *compare-and-swap* (a `statement → assignment`, near the bottom of the
list) or *compare and return a new array* (no assignment). Follow the swap and
you inevitably derive **bubble sort** — "the worst possible sort algorithm."
Avoid the low-priority assignment and "you wind up with a quick sort, and it
almost falls out inevitably."

Caveat — a strong heuristic, not a theorem. Martin himself frames TPP as a
*premise*: *"will you get better algorithms in every case if you choose a
transformation that is higher on the list?"* is posed as an open question, not a
proof. Which design emerges still depends on the **tests and transformations you
choose** at each fork. Use TPP+ZOMBIES to avoid impasses and steer toward good
designs — then apply design judgement when several simplest-first paths exist.

Bending the ranking is sometimes correct. When a transformation legitimately
needs a helper to land — e.g. a recursive solution over a collection needs a
function to take the tail/substring — taking that step is fine if it is the
smallest *real* increment. The goal is the next smallest increment, not literal
obedience to the list (a point Langr emphasizes — see Sources).

---

## Part 2 — ZOMBIES: the same idea, as a concrete test-ordering mnemonic

ZOMBIES gives you a memorable order for choosing those simplest-first tests.
**ZOM** (Zero, One, Many) is the core progression; **BIES** (Boundaries,
Interface, Exceptions, Simple) covers what else to select for as you go.

| Letter | Stands for | Choose a test that… |
|--------|------------|----------------------|
| **Z** | Zero | exercises the empty / zero / null case (empty list, no input, count of 0) |
| **O** | One | exercises exactly one element / one occurrence |
| **M** | Many / More | exercises many elements — the test that forces the loop/collection generalization |
| **B** | Boundary behaviors | probes limits: first/last, off-by-one, min/max, empty-vs-one transition |
| **I** | Interface definition | pins the smallest viable signature/return type the caller needs |
| **E** | Exercise exceptional behavior | drives invalid input, failures, exceptions at the port boundary |
| **S** | Simple scenarios, Simple solutions | keeps each chosen scenario — and the step it implies — as simple as possible |

### Ordering rule

Pick tests **Z → O → M** for the happy path, letting **I** (interface) emerge
from the very first test and **B**/**E** fill in once the core generalization
exists. Never select a Many test before a One test has forced it — Zero→One→Many
is exactly the simplest-transformation-first ordering TPP prescribes, made
concrete.

> Rule of thumb: each test you choose should add **one** small new behavior and
> demand the **smallest** possible generalization. If the only remaining test
> forces a large leap, a smaller test is missing between it and the last green.
> ("Behavior" here is the framework's canonical unit — see
> `nw-test-optimization` section 1, which also bounds the unit-test budget.)

---

## Part 3 — Where this fits in nWave's RED → GREEN → COMMIT cycle

TPP and ZOMBIES are not a cycle of their own. They operate **inside the RED
phase** — when you decide what to test next — within nWave's canonical
RED → GREEN → COMMIT cycle. The cycle itself is owned by `nw-tdd-methodology`;
this skill only governs *test selection* within it.

- **RED** — SELECT the next test with TPP/ZOMBIES: the behavior whose passing
  needs the simplest transformation (ZOMBIES order Z→O→M→B/I/E = TPP rank,
  simplest first). Watch it fail for the right reason (fail-for-right-reason
  gate, `nw-tdd-methodology`).
- **GREEN** — write the minimum code to pass; the test you chose already
  guarantees the implementation grows by the smallest generalization.
- **COMMIT** — refactor, then commit. nWave folds the classic red-green-**refactor**
  step into COMMIT; larger refactors run at deliver level via `/nw-refactor`
  (`nw-progressive-refactoring`). Then repeat: "tests more specific, code more
  generic."

> Naming note: the TDD literature calls the inner loop *red-green-refactor*. nWave
> names the step-level cycle *RED → GREEN → COMMIT* and treats refactoring as part
> of COMMIT (and the deliver-level refactor pass) — same activities, different
> grouping. There is no separate "refactor phase" to add.

### With property-based tests and batched authoring (the nWave default)

nWave's default is **property-based + state-delta**, not one example at a time
(`nw-tdd-methodology` Paradigm Mandate; single-example is fallback only) — so you
will often write a property, or several parametrized tests, at once. ZOMBIES
still applies, but to the **order in which behaviors are introduced**, not a
literal one-test-per-step cadence:

- a single property usually subsumes Zero/One/Many for one behavior — write the
  property once instead of three examples, and let `nw-test-optimization` collapse
  any redundant Z/O/M examples;
- when you batch or parametrize tests, the tests fix the *behaviors*; **TPP still
  governs how generically the implementation answers them** as you make them pass;
- keep distinct tests for Boundaries, Interface, and Exceptions that a single
  property does not naturally express;
- once a behavior is selected, author the test the nWave way — a property with
  `assert_state_delta(...)` at unit / in-memory layers (example-only at
  integration / E2E). TPP/ZOMBIES choose *which* test; `nw-tdd-methodology` and
  `nw-test-design-mandates` define *how* to write it.

### Diagnostic heuristics (all about test choice)

- *About to write a Many/loop test first?* You skipped Zero/One. Choose the Zero
  test — it needs only `nil → constant`.
- *The only test you can think of forces recursion or `while`?* A simpler test is
  missing. A One-case test usually drops the required transformation to
  `unconditional → if` or `statement → statements`.
- *A test forces a huge implementation leap?* It is too coarse. Insert a smaller
  ZOMBIES test between it and the last green commit.
- *Implementation came out over-engineered?* You likely selected too big a test.
  Back up and choose a higher-priority (simpler) one.
- *The test you picked won't even run* — a cascading error, not a clean assertion
  failure? Don't force it. Temporarily disable/skip it, pick a higher-priority
  test that fails cleanly, reach green, then re-enable the deferred test
  (strategic deferral per Langr — see Sources — not overcoding).

---

## Part 4 — Worked example: `sum(numbers)`

Each row is the **next behavior chosen** because it needs the simplest remaining
transformation — not a code trick to pass a pre-chosen test. (The canonical TPP
demo is the **Prime Factors Kata** from Uncle Bob's NDC 2011 talk —
nil → empty list → `if n>1` → constant `2` → variable `n` → `if`→`while`→`for`.
`sum()` below is a smaller stand-in with the same shape. Under nWave's PBT
default these rows often collapse into one property over Zero/One/Many plus
explicit boundary/exception cases — the *ordering* of behaviors is the point, not
the count of test functions.)

| Order | Behavior chosen (ZOMBIES) | Why chosen — transformation it drives (TPP) |
|-------|---------------------------|---------------------------------------------|
| 1 | **Z**ero — `sum([]) == 0` | needs only `nil → constant` (`return 0`) — the simplest transformation available |
| 2 | **O**ne — `sum([5]) == 5` | next simplest: `constant → scalar` — read the single element |
| 3 | **M**any — `sum([5, 3]) == 8` | first behavior that genuinely forces `if → while` (the fold/loop) |
| 4 | **B**oundary — `sum([-1, 1]) == 0` | no new transformation — confirms the generalization holds |
| 5 | **E**xception — `sum(None)` raises | drives `unconditional → if` — a guard at the port boundary |

Each row adds exactly one behavior and uses the highest transformation that
keeps the suite green. Step 3 is where Many forces the generic loop — and not a
moment earlier.

---

## Relationship to other skills

- **`nw-tdd-methodology`** — owns the RED→GREEN→COMMIT cycle, fail-for-right-reason
  gate, and the PBT + state-delta paradigm. TPP/ZOMBIES operate *inside its RED
  phase* as selection heuristics; they do not change the cycle.
- **`nw-test-design-mandates`** — TPP/ZOMBIES select among **observable, port-level
  behaviors** (the mandates' unit of test), never internal steps.
- **`nw-property-based-testing`** — ZOMBIES equivalence classes (Zero/One/Many,
  Boundaries) map onto Hypothesis strategies: a property over "Many" generalizes a
  parametrized One/Many example set.
- **`nw-progressive-refactoring`** — owns the refactoring that happens in COMMIT
  and at deliver level (L1–L6, `/nw-refactor`).
- **`nw-test-optimization`** — defines "behavior" (section 1) and guards against
  ZOMBIES inflation: collapse redundant Zero/One/Many examples into a single
  property where they assert one behavior.
