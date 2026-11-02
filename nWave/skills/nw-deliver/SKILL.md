---
name: nw-deliver
description: Routes one strict Request through host-owned delivery using nwdes artifacts.
user-invocable: true
argument-hint: '<request>'
---
# NW-DELIVER

Before creating or inheriting a lane, or finalizing/resuming its cleanup,
apply the worktree lifecycle in `nw-throughput`. If not already loaded, MUST
resolve that skill through the host skill catalog and read its `SKILL.md`.
Load `nw-auto` for its visible-baseline rule before changing code. The baseline
runs alongside authoring, not as a serial preflight. A broken setup is not an
intentional feature RED.


Use nwdes as the delivery route: read `nw-nwdes` and `nw-role-invocation`
before delegating. Generate the installed Product Owner's prompt with the
complete Request; it records product values through the nwdes CLI using Bash
(`nwdes product` record edits, `nwdes product close`).

The LLM evaluates and revises S/M/L, applicable waves, sequencing and upstream
corrections. nwdes constructs the handoff, briefs, prompts and packets; it has
no workflow ledger, gates or next-step state and launches no models.

Generate role instructions with `nwdes prompt`. Every role records through the
CLI with its kind's verbs. The architect records design values
with design verbs; the acceptance designer uses acceptance verbs for its
assigned slice. Before oracle authoring, the examiner records public
expectations with `nwdes expectations row add/close`.
The host writes no JSON and copies no reply into another command. For each role the
route invokes, it passes that role's generated `nwdes prompt` bundle verbatim, and
that role, not the host, runs its kind's verbs. Facts the route assigns to the host,
such as `feature new` and `slice set`, stay with the host.
Run every nwdes command from the checkout's top level; roots default to cwd
and the repository root, and lane verbs resolve the main worktree. The first
add, set or remove creates the scoped draft. Use `open --from-current` to revise
current authority; close with no draft validates empty values.
The crafter records changed files and command results with craft verbs;
nwdes writes its closed run evidence separately from the handoff.
The host runs each declared verification command once per candidate and captures
actual RED/GREEN and live native observations; the root never repeats them.
The final reviewer owns selection and sufficiency of the touched-file selected tests.
It reuses a complete applicable native result (host, CI or the normal commit hook)
whose source, test, argv and runtime inputs are unchanged, citing its original operator
and run; it executes only missing or affected checks, once. Reuse never waives a check.
The final whole-candidate independent
review and source-blind public-perspective EXAMINE remain required where applicable,
run after composition; prepare actual public evidence with `nwdes packet`.
The reviewer records findings with review verbs; the examiner records verdicts
with `nwdes examine verdict set` and closes with `nwdes examine close`.

Where an uncertain boundary remains, exercise an early concrete
producer-to-consumer connection through the real public port. Return a
consumer's specific missing semantic question and counterexample to its owner
before expanding the solution. This creates no cycle for technical fragments.

## Human-readable authority

Use `nwdes document` to render current briefs and HTML. Read
`nw-doc-as-artifact` when using those views with the human. There is no
wave-entry preference, density gate or completion offer to resolve.

## Integrate and close

Use the project lane reported by `nwdes lane open` and follow `nw-throughput`
for composition and integration. Preserve useful evidence before
`nwdes lane integrate`, which fast-forwards trunk and then removes the lane; `LaneNotMerged` means the lane tip is not contained in the
integration candidate, not that the lane must already be merged. The handoff and product brief are the feature record, without a
separate evolution constructor. Commit only when authorized; nwdes never
commits or publishes automatically.
