---
name: nw-code-design-oo
description: "Load before designing or changing domain/application code: owners, reuse, boundaries, simplest design, domain language, calisthenics, aggregates, architectural and contract tests."
---

# Code design (OO, ports and adapters)

## 1. Decide before writing

1. Follow the paradigm the repository and touched code already use; a unit in another paradigm gets its reason in the closing statement. Procedural code keeps its imperative structure; do not rewrite it into classes or functions to fit a label. Section 5 (calisthenics) applies to the OO track only; FP track rules are in section 5b.
2. Search for an existing owner by responsibility, invariant and consumers, not by name. A second algorithm deciding a fact an owner already decides is a defect even when it looks different. Reuse or extend the owner at the place that owns the rule; create new only for a stated incompatibility.
3. Merge two units into one abstraction only when they answer the same question and change for the same reason; look-alikes that change for different reasons stay apart.
4. Give each decision, effect, error type and per-process state exactly one owning module. No second module decides or stores it.
5. Changing a shared contract or rule: change its owner, its producer and every consumer in the same diff, or name in the closing statement why a consumer is unaffected.
6. A pipeline stage, container or infra file extends the existing workflow/definition; if it cannot, name the existing alternative and why it failed.
7. Add no field, parameter, flag, branch, layer, option or extension point that no accepted outcome reads. Add no pass-through layer that hides no knowledge. Add no type or channel that repeats a fact an existing carrier already holds.
8. Abstract (framework, plugin, base class) only when a second real caller needs it.
9. An edge case: reuse or relax the general rule; add no named exception, token or special-case branch.
10. When removing or merging a type, layer or branch, keep every accepted outcome observed by a passing test. Keep an element if an accepted outcome breaks without it, or if removing it makes the whole path costlier (more steps, rework or waiting for other roles).
11. Judge a design in this order: behaviour shown by tests; no semantic duplication; clarity; fewest elements.
12. State in the closing statement the chosen design, the alternative you rejected and what the choice costs (coupling, latency, effort).
13. For a change touching an external dependency, retry, recovery or concurrency, name each assumption it relies on, what still works when it fails, and what must never happen then; add one test per such failure.

## 2. Boundaries

- Dependencies point inward. Domain and application code depend on driven ports named for a capability (`OrderStore`, not `PostgresClient`), never on adapters or technology.
- Every new user-facing behaviour is reachable from its public driving port; check the producer-to-consumer path reaches that port.
- An adapter failure (timeout, decode error, dependency down) is translated at the port into the declared application outcome. No vendor or transport exception type reaches domain or application code.
- A read-only driving port exposes no write method. A preview or validate operation returns a plan value and writes nothing: `dry_run(cfg) -> Plan` is pure, `execute(plan)` is the only impure call.
- Core and business units receive collaborators and environment (clock, env vars, home dir, filesystem) as constructor or function parameters, resolved where the caller can see them. Only composition roots and effect adapters construct or read them.
- Wiring needs a restricted capability (`SafeFileSystem(root)`), not a god object (`os`, `Path.home()`).
- Per component state its contract shape: pure (return only), bounded change (declared mutation set), or plan-only.

## 3. Domain model and language

- A decision about an object's data lives on its owner: value object, entity, aggregate root, choice type. A policy spanning aggregates lives in a named domain service. An application service coordinates ports and owns no domain rule; a method that reads state, branches, and writes it back moves onto the owner.
- Value object: immutable, refuses an invalid value at construction, equal when its exposed observations agree.
- One transaction changes one aggregate. Reference other aggregates by identity (`ProductId`, not `Product`). A cross-aggregate effect is a domain event.
- A repository serves one aggregate root, returns domain objects, takes domain-language queries (`find_active_orders`), and exposes no SQL, JSON or row shape to domain code.
- Domain events are past-tense facts, one fact each (`OrderConfirmed`).
- Names and types come from the domain vocabulary, never from mechanics (`Manager`, `Helper`, `Data`). Do not abbreviate a name.
- One word names one concept across code, tests and docs of a bounded context. Use the context glossary's terms in changed docs. A word meaning different things in two contexts is kept distinct at the boundary (`SalesOrder`, `FulfilmentOrder`).
- Renaming a concept renames every use in code, tests and docs in the same diff.
- Two confusable concepts get distinct types, not the same `str`/`int`; a native type that already says the concept stays native.
- A generic payload boundary (dict, JSON) is documented at the boundary; deliberate boundaries use precise records, unions or result types.

## 4. Outcomes

Count the operation's outcomes. Each domain outcome (not found, refused, empty, already done) is in the return type as a named value the caller branches on, illegal combinations unconstructible; never return `None`/null for a domain outcome. Raise only for programming errors. A caller matching on `except` of a domain outcome is a defect.

## 5. Calisthenics (OO track: all ten, strict, in domain and application code)

1. One indentation level per method.
2. No `else`: guard clauses, polymorphism or Null Object.
3. Wrap primitives and strings that carry domain meaning; none as a method argument or return except in constructors.
4. First-class collections: a class holding a collection holds nothing else; no collection argument except in constructors.
5. One dot per line: talk to self, owned fields, parameters, objects you create. Fluent builders and streams are fine.
6. No abbreviations.
7. Small units: one responsibility each; cohesion decides size, not line counts.
8. At most two instance variables; a third is a missing collaborator.
9. No getters, setters or public mutable properties: tell, don't ask.
10. No stateless utility classes or "managers".

Adapters, DTOs at port boundaries, read models, config and ORM mappings are exempt; map them to the domain at the boundary. State each break and its cost in the closing statement.

## 5b. FP track

- Build behaviour by composing small single-purpose functions.
- Each function's type admits only the capabilities its body uses (a pure function takes no clock or store).

## 6. Modularity

- One reason to change and a narrow public surface per module.
- A unit that reads another unit's fields to decide (flag, branch on its state) sends the decision to the data's owner instead.
- Two units that agree on a position, literal, algorithm or call order get one named type, constant or single owner.
- A method that groups steps only because they run in sequence or share data is split by responsibility.
- Inheritance only for substitutable specialization: a subtype never strengthens a precondition or weakens a postcondition. An interface is one cohesive role; no client depends on an operation it does not use. Otherwise compose.

## 7. Architectural and contract tests

1. For each dependency, boundary or ownership law the change can reach, add or keep an architectural test; else state why the law does not apply. It checks the law over everything the law governs (modules added later, transitive paths), never a fixed file list or style.
2. For each shared contract whose parties can change apart (other owner, deployable, release schedule, or persisted/wire data outliving the producer), add or keep a contract test; else state why not. It feeds real producer output through the real consumer; no mock echo, no hand-written producer record.
3. Add no contract test for callers in one deployable that change in the same commit, unless persisted or wire data outlives the producer version.
4. Run these tests under a verification command the repository declares. Leave existing ones present and unweakened.

## Self-check before recording the step

1. Each reused owner is called or edited where it owns the rule; no second decider exists.
2. Every added element is read by an accepted outcome.
3. Dependencies point inward; adapter errors are translated at the port.
4. Each decision, effect and error has one owner; every consumer of a changed contract changed.
5. All ten calisthenics rules hold in changed domain code, or the break is stated.
6. Aggregates: one per transaction, others by id, effects as events.
7. Names are domain words, unabbreviated, one word per concept.
8. Architectural and contract tests exist or have a stated reason.
9. Every domain outcome is a named return value, never null.
10. The closing statement names the rejected alternative and its cost, and each failure assumption with its test.
