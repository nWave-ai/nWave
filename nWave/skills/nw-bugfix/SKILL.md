---
name: nw-bugfix
description: Routes an observed defect through host-owned diagnosis and nwdes delivery artifacts.
user-invocable: true
argument-hint: '<observed defect>'
---
# NW-BUGFIX
Use this route when the root cause is not yet known. A defect whose root cause
is established, found during current work, is fixed in place in the current
lane instead: regression test observed RED, fix, GREEN, one commit, covered by
that Request's review and CI (`nw-auto` recovery table). No separate Request.

Before authoring regression tests or changing code, load `nw-auto` and report
the affected project's existing test baseline to the user as required by its
visible-baseline rule. A broken setup is not the bug's intentional RED.

Use nwdes as the delivery route. Give the observed defect verbatim to the native
installed Product Owner. Read `nw-nwdes` for the current route and
`nw-role-invocation` for mandatory skills and exact role contracts. Generate
instructions with `nwdes prompt`. Every role records through its kind's CLI verbs
using Bash. The Product Owner records product values
with `nwdes product` record edits and `nwdes product close`.
The host writes no JSON and copies no reply into another command. For each role the
route invokes, it passes that role's generated `nwdes prompt` bundle verbatim, and
that role, not the host, runs its kind's verbs. Facts the route assigns to the host,
such as `feature new` and `slice set`, stay with the host.
Run every nwdes command from the checkout's top level; roots default to cwd
and the repository root, and lane verbs resolve the main worktree. The first
add, set or remove creates the scoped draft. Use `open --from-current` to revise
current authority; close with no draft validates empty values.

Keep the defect verbatim in product authority and its matching public
observation in acceptance authority. The architect records design values with
design verbs. Before oracle authoring, generate the examiner's expectations
prompt; it records expectations with `nwdes expectations row add/close`.
The acceptance designer authors the regression oracle and records acceptance
rows with `nwdes acceptance row add` for its assigned slice, then closes.
The host runs its verification command on the original pre-fix source for RED.
Never infer that source from HEAD after the fix is committed. The native
crafter implements the correction and records changed files and command
results with craft verbs for its assigned slice; the host captures GREEN.

After implementation, prepare actual public evidence with
`nwdes packet --kind examine`. The examiner records each verdict with
`nwdes examine verdict set` and closes with `nwdes examine close`.
A fix no one observed working is
not a fix. Invoke independent review separately; the reviewer records
findings and closes its review with review verbs.

The LLM revises S/M/L, applicability, sequencing and upstream corrections from
evidence. nwdes constructs artifacts, not code, models, workflow state or
verification seals. `nw-auto` owns the common evidence and recovery guidance.
