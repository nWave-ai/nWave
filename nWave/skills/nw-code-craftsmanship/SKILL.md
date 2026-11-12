---
name: nw-code-craftsmanship
description: Load when writing or changing production code in craft; per-unit rules, failure messages, security, recovery, performance, honest closing statement.
user-invocable: false
disable-model-invocation: true
---

# Code craftsmanship

## Before writing a unit
1. Search for an existing owner of the responsibility (by what it decides and who consumes it). Reuse or extend it; create a new one only when you can name the incompatibility.
2. Give each fact, rule or config value one owner. Two units deciding the same fact are a defect even if the code differs; look-alikes that answer different questions stay separate.
3. Generalize (abstraction, plugin, framework) only when a second real caller needs it now.
4. Follow the design already chosen; if two owners compete for a rule, stop and raise it to the design owner instead of picking one.
5. Follow the paradigm of the touched code; state the reason in the closing statement for any unit in another paradigm.

## Writing each unit
6. Name from the domain language, never `Manager`, `Helper`, mechanics. One unit = one reason to change, one responsibility visible from its name.
7. State what the domain decides (expressions, pipelines, polymorphism), not bookkeeping.
8. Keep state private; change it only through the owner's methods; keep data with the behaviour that uses it; expose no internal type across a boundary.
9. When unit A reads unit B's data to decide, move the decision into B and send B a message.
10. Two units sharing a position, literal, value meaning, algorithm or call order: replace by a named type, a named constant or one shared owner.
11. Give a concept its own type when it can be confused with another, when a type can exclude invalid states, or when it owns a rule; its constructor refuses the invalid value. A native type that already says this stays native.
12. At deliberate boundaries use precise records, unions or result types. Document, at the boundary, every generic payload (dict, Any, object) you add.
13. Keep business decisions apart from SQL, transport and filesystem code; dependencies point inward through ports; inject collaborators.
14. Functional code: pure core, thin effect shell (read, decide, write); the core never calls the shell.
15. A driving or driven port exposes no private structure.

## Failure messages
16. Every refusal or failure you add states WHAT failed (the violated invariant), WHY (the cause), and HOW to fix, naming the concrete fix and the command or tool that produces a valid input.
17. Include every fact the rejecting code already holds that the reader needs: the offending value and where it lives (file, line, field), the limit it broke.
18. A validator over several inputs collects every independent defect and reports them all in one pass; checks that depend on another say they did not run.
19. Run the remedy the message names; it must lead to an accepted input.
20. Return every domain outcome in the return type; raise only for programming errors.
21. Each failure ends in correct recovery, a loud refusal or INDETERMINATE, never a silent wrong success. Could-not-verify is a third result and reaches the summary.

## Security and portability
22. Parse untrusted input with schema validation at the trust boundary before use; never deserialize it into an arbitrary object (no `pickle`, no `yaml.load`).
23. Normalise untrusted paths (`resolve()`) and check they stay inside the allowed root.
24. Pass untrusted data to commands, queries and templates only as arguments: `subprocess.run([..])` without shell, `cursor.execute("... ?", (v,))`, never string-built syntax.
25. Never log or print a secret or commit a secret literal; read secrets from environment or store.
26. Security defaults deny on error and grant least privilege; looser settings need explicit opt-in; check access on every request. A missing or newly added security scanner yields failure or INDETERMINATE, never a silent pass.
27. Make each read-check-write atomic where a race breaks an invariant (`open(p, "x")`, rename, lock, transaction).

## Recovery
28. An operation promised idempotent or recoverable must reach the same final state when re-run after interruption, with no duplicate or half-applied effect (write temp then rename; upsert).
29. When you change persisted data, keep a way back (revert or stated partial-rollback plan), or list it as unverified in the closing statement.
30. For each failure point or bypass the design names, have a test observe the degraded outcome, or state in the closing statement why it is unreachable. When an assumption (dependency down, input twice, step interrupted) is negated, the code refuses loudly or degrades as documented.
31. Adapter fault-injection tests (storage down, interrupted or double write, crash, concurrent writers) go in an infrastructure suite the default run excludes, and only where the human granted it.
32. A rollback or degradation trigger is a stated measurable value that a check can trip.

## Performance
33. Avoid allocation, copying, repeated I/O and quadratic work on hot paths.
34. Claim a speedup only with a re-runnable before/after measurement; each performance threshold you hard-code comes from a stated requirement.

## Tests you add
35. The oracle is not yours to edit. Add a unit test only when the oracle cannot go green without it, and only in the owned test paths.
36. Every refusal or check you add gets one assertion that fails on a constructed violation; probe once by re-injecting the violation, then restore.
37. A count assertion names its population and compares to it (`len(found) == len(expected_ids)`); a partition asserts that its parts sum to the whole; "nothing found" differs in output from a broken case.

## Comments, docs, closing statement
38. Comments and docstrings give the reason for a choice or a dated incident; no "this module reads X", no numbers the code can derive.
39. A document you change agrees with the code; fix the wrong side in the same change. Commands in a README or runbook run as written. Every nontrivial claim in a changed document is backed by a check the reader can rerun, or marked `not measured`.
40. Call something wired or active only after running the surface that invokes it and seeing the effect.
41. Closing statement: name the delivered behaviour, claim none the diff lacks. Show command and output for each check reported passed and for each numeric claim. Mark anything not run, stale or partly run as `not measured`, never as passed. Each unresolved finding names the obligation affected and a remedy.
42. Report an independent pre-existing defect to its owner; fix it only when authorised or when it is a regression of this request. State in the closing statement every repair of a pre-existing defect and who authorised it.

## Self-check before recording the step
1. No fact decided twice; new owners justified.
2. Every refusal says what, why, how, with located facts; remedy executed.
3. Untrusted input validated, paths confined, races atomic.
4. Recovery and failure-point tests or stated limits present.
5. Each added check has a failing-on-violation assertion.
6. Closing statement: commands with output, unknowns listed, pre-existing repairs named.
