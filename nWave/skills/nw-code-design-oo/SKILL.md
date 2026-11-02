---
name: nw-code-design-oo
description: OO code-design SSOT — the WHAT-to-design anti-smell catalog (Object Calisthenics, RPP smell taxonomy, effect isolation) shared by the solution architect (design-time) and the crafter (execution-time).
---

# OO Code Design

Design-time anti-smell catalog for object-oriented work. The architect loads this
to design smell-free domain types and module boundaries BEFORE DISTILL authors
ATs; the crafter loads the same SSOT for the execution mechanics that enforce it.
This file is the WHAT-to-design subset. `nw-tdd-methodology` owns RED→GREEN
verification; `nw-refactor` owns behavior-preserving refactoring. Repository
runner and hooks own build, test, and commit execution.

## Object Calisthenics

Ten rules for the OO core (Agile Technical Practices Distilled, "Object
Calisthenics – 10 Steps to Better Software Design"). Inside the hexagon, domain
objects and application services, they are strict. Breaking one is a conscious
design decision recorded in the diagnostic with the smell it causes, its benefit
and its cost; an unrecorded break is accidental complexity.

| # | Rule | Why | Smell it prevents |
|---|------|-----|-------------------|
| 1 | Only one level of indentation per method | One thing per method; small reusable units | Long Method |
| 2 | Don't use the ELSE keyword | One main lane with guard clauses; polymorphism (State, Strategy) or Null Object for the alternatives | Switch Statements, Long Method |
| 3 | Wrap all primitives and strings | No primitive or string as a method argument (except constructors) or return value; each concept gets a type that attracts its behaviour and makes wrong state unrepresentable | Primitive Obsession, Shotgun Surgery |
| 4 | First-class collections | No collection as an argument (except constructors); a class that holds a collection holds nothing else; filters and joins live there | Primitive Obsession, Feature Envy |
| 5 | One dot per line | Talk only to your immediate collaborators (Law of Demeter): self, owned fields, parameters and objects the method creates. The rule is about navigating a collaborator's internals, not LINQ, streams or fluent builders | Message Chains, Inappropriate Intimacy |
| 6 | Don't abbreviate | Names reveal intention; a name you want to abbreviate signals a unit doing too much | Large Class |
| 7 | Keep all entities small | Each method does one thing and each class holds one responsibility; size follows from cohesion, never from splitting code to meet a line count | Large Class, Long Method |
| 8 | No classes with more than two instance variables | High cohesion; a third field signals a missing collaborator | Large Class, Data Clumps |
| 9 | No getters/setters/properties | Tell, don't ask: the decision lives on the object that owns the data | Data Class, Feature Envy |
| 10 | All classes must have state | No static utility classes or stateless "managers"; behaviour has a home | Feature Envy, Middle Man |

**Scope**: domain entities, value objects and application services. Adapters,
infrastructure, DTOs at port boundaries, CQRS read models, configuration and
framework or ORM mapping are exempt; map them to the domain at the boundary.

**Services**: an application service coordinates ports and domain objects and
owns no domain rule. A decision about one object's data lives on that object; a
policy spanning several aggregates may live in a domain service. An application
service method that reads an object's state, branches on it and writes it back
is a transaction script; move the decision onto the owner.

**Rich domain model**: entities carry identity and the behaviour of their
lifecycle; value objects are immutable, equal by value and refuse an invalid
value at construction; an aggregate root is the only entry point that changes
its aggregate and guards its invariants in one consistency boundary; a
repository loads and stores one aggregate; a domain event names a completed
fact. `nw-ddd-tactical` owns these building blocks and their rules.

## Code Smells Hierarchy

Primitive Obsession, Feature Envy (with Inappropriate Intimacy) and Message
Chains cause most other smells; remove them first.

- **Primitive Obsession** → Duplicated Code, Shotgun Surgery, Divergent Change, Long Parameter List.
- **Feature Envy / Inappropriate Intimacy** → Lazy Class, Data Class, Middle Man, Data Clumps, Long Method, Large Class, Duplicated Code, Shotgun Surgery, Divergent Change, Long Parameter List.
- **Message Chains** → Data Clumps, Duplicated Code.

## Refactoring Priority Premise

Refactor each delta in this order, smallest level first, without changing
behaviour; the refactoring is verified once, together with the delta. A level is
done when none of its smells remains in the code you changed. `nw-refactor` owns
the mechanics.

| Level | Goal | Smells it cleans |
|-------|------|------------------|
| L1 Readability | Tackle clutter, comments, dead code, implicit knowledge, scattering, bad naming | Comments, Dead Code, Magic Strings and Numbers, Scope of variables and methods |
| L2 Complexity | Tackle complexity and duplication | Long Method, Duplicated Code |
| L3 Responsibilities | Tackle misplaced responsibilities | Long Class, Feature Envy, Inappropriate Intimacy, Data Class, Message Chain |
| L4 Abstractions | Tackle missing abstractions | Long Parameter List, Data Clump, Primitive Obsession, Middle Man |
| L5 Design Patterns | Replace conditionals with polymorphism; apply a pattern only as the target of a refactoring the actual recurring problem asks for, shaped to the context and named for the domain behaviour | Switch Statements → Dictionary/Hashmap, Strategy, State, Command |
| L6 SOLID++ | Fix the design principles | Refused Bequest → LSP, ISP; Divergent Change → SRP; Shotgun Surgery → SRP; Speculative Generality → YAGNI; Parallel Inheritance → ISP |

**Liskov substitution**: a subtype or interface implementation keeps every
promise to its clients: no stronger preconditions, no weaker postconditions,
invariants preserved. **Interface segregation**: an interface is one cohesive
role its clients need; no client depends on an operation it does not use.
Inheritance expresses substitutable specialization only; other collaboration
uses composition.

## RPP Smell Taxonomy

Smells an architect detects in a design before code is written, and the design
decision each one asks for. Detection is design-time; the refactoring order above
and `nw-refactor` belong to the crafter.

| Level | Smell | Design-time implication |
|-------|-------|-------------------------|
| L3 | Primitive Obsession | Raw int/str carrying domain meaning → introduce a value object |
| L3 | Magic Numbers | Bare literal with hidden semantics → name it (enum / constant / value object) |
| L3 | Tell-Don't-Ask | Caller queries state then decides → move the decision onto the owning object |
| L3 | Feature Envy | Method reaches into another type's data → relocate behavior to that type |
| L3 | God Object | One type owns too many responsibilities → split along bounded responsibilities |
| L3 | Large Class | Class owns more than one cohesive responsibility → extract collaborators |
| L4 | Shotgun Surgery | One change forces edits across many sites → consolidate the concept into one home |

Design rule: a smell detected at design time does not survive into the design
artifact unless it is a recorded conscious trade-off. Resolve it in the type and
boundary decisions, not at DELIVER.

## Effect Isolation

Design components so the bug class "side-effect-free function silently writes" is
non-representable, not testable-around. Push contract enforcement up the type
hierarchy as far as the language allows. Three levers:

- **Functional Core / Imperative Shell** (Bernhardt) — business logic in pure
  functions; effects only at a thin shell. Approximates IO-monad separation in
  any language.
- **Plan-value pattern** — dry-run / preview / validate functions return a `Plan`
  data value, never silent side effects (`dry_run(cfg) -> Plan` pure; `execute(plan)`
  the only impure call). Makes "preview wrote to disk" structurally impossible.
- **Capability injection** — pass restricted interfaces (`PlanRecorder`,
  `SafeFileSystem(root=tmp)`) at boundaries, never god-objects (`os`,
  `Path.home()`). Approximates capability typing via DI.

Per component, declare a **contract shape**: pure-function (return-only),
bounded-change (declared mutation set), or unbounded-preservation (must return a
Plan, never mutate). A driving port that "only reads" must not expose write
methods — split read/write into separate ports.

### Declared inputs at the boundary

The OO reading of `contract:declared-inputs-not-ambient-reads` (SSOT:
`nw-cross-cutting-invariants` — the gate list and the anchor live there, not
here). It is `Capability injection` above restated as a review question, because
that pattern is easy to agree with and easy not to apply.

> **What does this component read that nobody passed it?** For every gate the
> clause lists, decide at the boundary: a constructor parameter, an injected
> capability, or an explicit override — with the ambient lookup kept as a default
> the caller may state.

Resolve it **where the caller can see it**. A gate resolved lazily, at first use
deep inside a method, is read outside the window in which the caller — or a test
— controls the environment, so even a caller that wanted to declare it cannot.

Test-side mirror: the Algebraic Analysis Before the Scenario mandate
(`nw-test-design-mandates`), its declared-inputs question.

### Enumerate the outcomes before choosing the return type

> **How many outcomes does this operation have — and does its signature carry
> every one of them?** "It returns the value and raises on the bad case" is the
> wrong answer: that is N-1 outcomes in the type and one in the control flow.
> **If any outcome is not in the return type, put it there** — a value the caller
> branches on, with the illegal combinations unconstructible (enforce in the
> constructor: only the outcome that carries a payload may carry one, and it
> always does).

Why this is a design rule, not a style preference: `except` matches on class
**identity**, so a raised outcome couples the caller to the exact module object
the raiser was loaded from. Where the same package is reachable by more than one
path — a source tree plus an installed runtime, a harness that adjusts
`sys.path`, a plugin cache — that identity is not guaranteed. The `except` then
fails to match and a *handled* outcome escapes as a crash, in an environment
nobody was testing.

Keep `raise` for what it is good at: a **programming error** (a broken
precondition, an import-time drift guard) where crashing is the correct outcome
and no `except` is meant to cross a module boundary to catch it.

FP states the canonical form of the same rule — a total function into a sum type
(`nw-code-design-fp` § Railway, "Count the outcomes before you choose the return
type"). This is its OO translation.

Empirical anchor, 2026-08-06: CI reported `UnknownPhaseName`
propagating out of `_resolve` from the line INSIDE its own `try`, with the
matching `except` on the next line. `resolve_phase` documented three outcomes,
returned two, threw the third. Returning all three closed the failure class
*without* establishing why the module loaded twice — a fix that does not depend
on that answer is a design fix rather than a patch.

## Cross-cutting invariants (load them — they are not restated here)

Paradigm- and role-independent rules live in ONE shipped home: `nw-cross-cutting-invariants`.
Load it alongside this skill and honour these clauses by id — they are NOT duplicated here:

- `data:consumer-known-before-produced` — a datum is produced only because a named consumer
  reads it, and you must name the JOIN KEY it will be related on. No reader, or no key → the
  datum is unjustified.
- `gate:self-explaining-what-why-how` — every rejection states WHAT / WHY / HOW.
- `gate:design-principles-gdp-1-9` — the canonical gate-design contract.
