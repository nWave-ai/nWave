---
name: nw-mutation-test
description: "Run an explicit mutation probe over a named production delta, or support the project-level nightly-delta policy. Disabled by default."
user-invocable: true
argument-hint: '[--delta <base>...<head> | --nightly-delta] [--threshold 80]'
---

# Mutation Test

Mutation testing is **disabled by default**. This skill runs only after an
explicit on-demand invocation or when the project itself declares
`Mutation Testing Strategy: nightly-delta`.

It is a standalone diagnostic outer loop, not a DELIVER phase, rigor knob, completion
gate, workflow state or substitute for semantic acceptance tests.

## Input authority

- Explicit probe: use the named production diff.
- Nightly delta: use production files changed since the last successful
  mutation run.
- Never infer targets from `docs/feature/`, feature-delta, a progress ledger,
  filenames alone or the implementation agent's claims.

If the diff is empty, report `not-applicable` and stop. If a target is
missing, outside the repository or not production code, fail loudly before
starting a mutation tool.

## Execution

1. Detect the project's language and existing mutation runner. Do not impose a
   Python-specific tool on another language.
2. Prove the target's ordinary tests pass with the project's declared runner.
3. Snapshot the user's worktree status.
4. Create a dedicated disposable worktree or copy and run all mutations there.
   Never mutate, reset or restore the user's worktree.
5. Compare the user's status with the snapshot and discard only the disposable
   target.

Each invocation binds the actual production delta/commit snapshot, ordinary-GREEN
baseline, oracle/support/source identities and native build/discovery graph.
Allocate distinct process, workspace, mutable config, build/temp/cache and result
paths with provenance; parallel probes cannot share fixed files or cache identity.
Tests must participate in that native graph, not a disconnected Python harness.
The repository's nightly Python adapter supports its declared Python/mutmut 3.8
contract only; it is not a cross-stack runner. Empty/unsupported target sets,
driver no-ops, zero generated mutants or interrupted attempts are never PASS100.

No supported runner is an honest `indeterminate`, not a fabricated PASS.

## Result

The requested/project threshold (default 80%) applies only to a valid attributed
attempt with a measured nonzero denominator. Report actual generated, killed,
survived and incomplete/unclassified counts with their population and conservation.
Do not turn timeout, build/setup failure or untested mutants into killed outcomes,
or omit them to inflate the denominator. Preserve invalid attempt evidence and
partial actual counts without a passing rate.

- `pass`: valid complete attempt, kill rate >= threshold.
- `fail`: valid complete attempt below threshold; name real survivors by production
  file, line/symbol and smallest missing observable.
- `indeterminate`: unavailable runner, failed baseline, no-op/zero mutants,
  interruption, incomplete outcome or evidence not attributable to this delta.
- `not-applicable`: validated delta contains no mutable production target.

Keep the interactive report concise: verdict, numerator/denominator, per-file
survivor count, and a bounded list of actionable survivors. Do not create a
per-delivery markdown report or another persistent progress artifact.

For `nightly-delta`, CI owns persistence: create or update one deduplicated
issue containing the same bounded report and the exact comparison range. A
later green run closes that issue. The nightly job must not expand to the
whole repository when its baseline is missing; establish a new baseline
explicitly instead.
