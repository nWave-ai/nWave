---
name: nw-test-design-mandates
description: Load before writing, reviewing or timing any test - oracle, scenarios, assertions, fakes, names, budgets, walking skeleton.
user-invocable: false
---

# Test design mandates

Examples are Python; write in the project's own language. Rules on private imports and the driving-port example (1.4, 1.5, 7.7) bind acceptance tests; unit and property tests may exercise the public contract of a non-exported internal module.

## 1. Decide before writing

1. Find the project's native test contract (manifests, build files, test targets, existing tests) and use its language, runner and style. Never add Python, pytest, Hypothesis, Gherkin or `tests/common` the project lacks. A missing toolchain is an EVIDENCE_GAP you report, never a reason to switch stack.
2. List each promised outcome of the request with the test that proves it. Each outcome gets at least one falsifiable test whose assertion states that outcome in plain words and whose public stimulus and observed result use no implementation names; an existing unchanged test that proves it counts. An outcome with no test gets a gap line with its reason in the closing statement; never write "all outcomes covered" while one has neither.
3. Name the law each test protects in one sentence ("a refused order leaves the cart unchanged"). If you can only say "the feature works", stop and name the law.
4. Take the narrowest surface that carries the law: a pure function under its public contract, plus one example at the driving port. State every input the behaviour depends on (environment, cwd, clock, platform) in the test instead of inheriting it.
5. Reach the system only through its public driving port (CLI main, service method, HTTP handler, a library's exported function) or the composition locator the DESIGN declares, composed as production composes it. Import or call no private module, helper or class. If the port cannot express a promise, return the finding to the design owner and name the public alternative; never invent a field, operation or fixture fact.
6. Give each port its treatment:

| Port | Focused test uses |
|---|---|
| Driving (CLI, API, hook, call) | the real entry called in-process with a capturing output port; no subprocess |
| Driven internal (repository, cache, read model) | in-memory fake |
| Driven external (clock, email, payment, LLM, third-party API) | fake that captures output so Then reads the side effect |

   A real driven-internal adapter appears only in the walking skeleton or a declared adapter-integration test. No test double is defined or used inside domain or application code. Every in-memory fake rejects each input the real adapter rejects (None, empty string, out-of-range number, invalid enum). A port you cannot classify: ask.
7. Put business logic in pure functions first; parametrize fixtures only for the thin adapter layer.
8. When DESIGN declares a seam, name that exact seam, drive it through the real entry point and assert its observable effect. When DESIGN declares a contract-test obligation, feed real producer output to the real consumer (no mock echo, no hand-written producer record). When it declares an architectural-test obligation, write one check that fails the law over its whole governed scope, at the declared locator.

## 2. Write the scenario

1. Name the test as a sentence: class `<DrivingPort>Should`, method `<expected_outcome>_when_<behaviour>[_given_<precondition>]`; where there are no classes, one name with the same parts. Derive the name from the promise before writing it.

```python
class AccountServiceShould:
    def test_increase_balance_when_deposit_made_given_sufficient_funds(self): ...
```
2. A name or title states what the user achieves, in words a non-engineer reads. It contains no layer, plumbing, process id (`slice_NN`, `Mandate-12`, ADR number, `V3`, step or commit name), production class, function or error-code constant. The only production name allowed is the public driving port in the class name `<DrivingPort>Should`; public protocol identifiers may also appear where the protocol is the promise. Titles are unique within the feature.
3. Write steps as Given / When / Then (or Arrange / Act / Assert) in domain words, 3-5 steps, with exactly one When/Act (one stimulus). Steps contain no business logic, branching or loops; no helper owns a whole scenario. A scenario states the user value it delivers (the promised outcome); add a motivation only if the request supplied it.
4. Use concrete values ("balance is $100.00", "name 'Ada'"), not abstract phrases ("sufficient funds"). Write stimulus data in plain domain words; an identifier appears only where it is the public protocol or a promised domain fact.
5. Declare each domain concept that appears in two or more scenarios once as a domain type; step methods take that type, not raw strings or ints. Call shared step helpers; never re-implement the step DSL per test. Create the scenario context fresh per test; share no static or global step state. When a type already exists in production source, import it; never redeclare it test-side.
6. Parametrize only data variants of the same scenario with the same outcome shape. Keep each identical stimulus-and-assertion pair once; every test adds a distinct observation that a declared obligation induces; no property repeats a finite example's pair.
7. A scenario may reuse the state a previous scenario produced only through the public port, never through shared fixture state; each test still passes alone.
8. Write error and edge cases from the promises: per feature, one case where the promised outcome succeeds and one where it is refused. Each promised sad path (refusal, conflict, race, stale or invalid input, missing operand) gets its own test. Each promised failure or recovery mode gets a test whose assertion differs from every other mode's. A refused-operation test asserts the public state the contract keeps unchanged or changes and no other change. An integration-level failure path is a named concrete example.
9. A refusal you cannot test through a public surface plus a DESIGN-declared locator goes back to design; do not mark it untested.

## 3. Write the assertions

1. Assert a return value, a public state change or the captured output of a fake at its declared port. Never assert a private field, internal state, a mock's call count or argument wiring. A promised retry, recovery or exclusion is read from that captured output on every invocation, not only the final result.
2. Assert outcome, state, type or required fields; not incidental ordering, formatting or representation, unless the authority promises it. Equivalent extra fields stay valid.
3. Never assert only that code runs, that a shape or type appears, `is not None`, or that an internal call happened, unless that shape is the promised contract.
4. Take each expected value from a stated requirement or business rule, never from the code or fixture under test. A test whose oracle is data the test fabricated passes with production deleted; assert an artifact the system shipped or an effect it produced.
5. State preserved state: observe the promised public state before and after; an undeclared change fails the test. A pure output needs no invented state.
6. Observe at the real boundary any promise a fake could falsely satisfy (durability, atomicity, real protocol, race).
7. Pin no prose: no phrase, heading or regex over documentation, except a machine contract (schema, table grammar, CLI output format, parse rule). Verify a shipped asset through its real consumer.
8. Word every assertion failure message as WHAT failed (expected vs actual), WHY it matters (the contract broken), HOW to fix (what must become true). Then/Assert steps carry it; scenario bodies stay clean.
9. Counts name their population and are asserted against it, never a bare integer. A split into parts asserts the parts sum back to the whole (compare record identities with multiplicity, not only `len`). A "none / empty / not applicable" result builds the empty case and a broken or incapable case in the same test and asserts their outputs differ.

## 4. Oracle, red and the one probe

1. The oracle tests collect, build and run through the repository's native test command with declared dependencies only, and the promised stimulus reaches an assertion of the business outcome.
2. Read why each test fails. The promised outcome absent or wrong is RED. An import, collection, dependency, fixture or startup failure is BROKEN: fix the test. Already-satisfied behaviour stays green; invent no production change for it.
3. A test for a promised, not yet built outcome stays RED in its committed state. Skip, expected-fail and pass-bridging are forbidden; do not toggle markers to fake RED. Write no production stub, placeholder or assertion-error scaffold to manufacture RED.
4. The production step edits no oracle test file. A test defect returns to the oracle author. When the oracle cannot go green without them, a single executor may add new unit tests in new files; it never edits oracle files.
5. For NEW behaviour, probe once at authoring time per test: after green, re-inject the one wrong behaviour the promise names into the covered code, confirm the test fails, restore. This is one deliberate break, not mutation testing, and never a review gate. An already-satisfied promise needs no probe; the unchanged applicable test covers it.
6. Run each new test alone in a fresh process; it must pass with no other test's side effects. Renaming a private helper must leave every new test green.

## 5. Walking skeleton

1. Each feature has exactly one walking skeleton, written first: the thinnest real path from the real entry point to a real terminal effect. Later slices extend it; none adds another. Extra end-to-end scenarios need a distinct integration need.
2. Title it as a user goal; Given/When are user actions; Then is what the user observes (confirmation, file, output), not a database row or queued message.
3. It performs real I/O at every declared internal adapter (filesystem on a temp dir, git repo, local subprocess, database); external systems stay capturing fakes. If a fake could not observe the declared failure, escalate; never swap it in silently.
4. When the user consumes a built artifact (package, image, bundle), the skeleton asserts a capability the user gets from that artifact, using the repository's existing prepared build and install setup. A new test never runs a full installer or lifecycle subprocess itself.
5. Every driven adapter has at least one integration test with real I/O. A feature with no entry point, a behaviour-preserving refactor, or a config/docs-only change needs no skeleton; state which case.

## 6. Budgets and fixtures

1. A unit test's median time is at most 10 ms. A property case is about 10 ms. The default suite finishes within 300 s, or within the ceiling the repository sets. Only a recorded human override lets the suite pass above the ceiling.
2. Provision each real adapter fixture once per session or module and isolate per test with a unique namespace, schema or directory; never provision again inside each test. If the shared instance dies, dependent tests fail with what broke.
3. Real adapter fault injection (storage down, interrupted or double write, crash, concurrent writers) goes in a separate infrastructure suite that the default run excludes, and only where the human granted it. Never write a test above budget; report it to the human instead.
4. Give each formal law an executable projection on the pure core inside the default suite.
5. Closed finite domains use examples; broad laws follow nw-property-based-testing.

## 7. Self-check before recording the step

1. Each promised outcome has a test or a stated gap; the closing statement claims nothing more.
2. Each test name reads as a sentence and holds no process id, layer term or production symbol except the driving port in `<DrivingPort>Should`.
3. One When per scenario; no logic in steps; concrete values.
4. Success and refusal each tested; each sad path observed; refusals assert preserved state.
5. No assertion on private state, mock calls, shape-only or prose wording.
6. Fakes only at driven ports; none in domain code; fakes reject what the real adapter rejects.
7. Tests reach the system only via the public port; none imports a private module.
8. One walking skeleton with real internal adapters; no extra subprocess or installer runs.
9. Every count has a population, every split sums back, every "none" differs from "broken".
10. Each new test failed for the right reason once, passed alone, and fits its time budget.
11. No skip, expected-fail, stub or edited oracle file.

## 8. Mandate registry, numbering and routing

This core owns the mandate numbering. Numbers are an SSOT-internal index, defined in exactly one place - the registry below; re-indexing is allowed when the registry is reorganized. Refer to a mandate externally by its stable descriptive name plus this SSOT, never by a hard-coded number; numeric labels in test docstrings (`Mandate-12`, ...) are legacy shorthand for the named rules.

| # | Name | Where it lives |
|---|------|---|
| 1 | Hexagonal Boundary Enforcement | nw-test-design-mandates-scenario-design |
| 2 | Business Language Abstraction | nw-test-design-mandates-scenario-design |
| 3 | User Journey Completeness | nw-test-design-mandates-scenario-design |
| 4 | Pure Function Extraction Before Fixtures | nw-test-design-mandates-scenario-design |
| - | The 3 Pillars (style backbone) | nw-test-design-mandates-scenario-design |
| - | Walking Skeleton Strategy | nw-test-design-mandates-scenario-design |
| 16 | Algebraic Analysis Before the Scenario | nw-test-design-mandates-scenario-design |
| 8 | Universe-bound assertion at layers 1-3 | nw-test-design-mandates-layered-mechanics |
| 9 | PBT input mode is layer-dependent | nw-test-design-mandates-layered-mechanics |
| 10 | Two-tier acceptance for rich journeys | nw-test-design-mandates-layered-mechanics |
| 11 | Integration sad paths stay example-based | nw-test-design-mandates-layered-mechanics |
| - | Layered Test Discipline table + Polyglot Adapter Matrix | nw-test-design-mandates-layered-mechanics |
| 12 | SSOT + Zero Duplication via Types | this file (section 2.5) |
| 13 | Driving-Port-Only Boundary | this file (section 1.5) |
| 14 | Contract Shape Classification | this file (sections 1.4, 1.6, 3.7) |
| 15 | Dormant-Seam Reconciliation | this file (section 1.8) |

Load `nw-test-design-mandates-scenario-design` when shaping or judging a scenario's shape (boundary, language, journey, fixtures, style) and `nw-test-design-mandates-layered-mechanics` when choosing observation mechanics for a layer or adapter realness. The composition rules (12-15) are held here; `nw-test-design-mandates-composition-contract` is a pointer stub to this file.
