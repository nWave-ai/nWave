---
description: Routes one observed defect Request through nwdes delivery.
argument-hint: '[observed defect]'
---
# NW-BUGFIX

Load `nw-bugfix`, `nw-auto` and `nw-role-invocation`. Report the affected baseline
before authoring the regression oracle or changing production code.

Load `nw-nwdes` and use nwdes as the delivery route. Invoke the native installed
Product Owner with the observed defect verbatim and its generated prompt.
It records product values with `nwdes product` record edits and
`nwdes product close`. Every role records through its kind's nwdes CLI verbs using Bash.
The host writes no JSON and copies no reply into another command. For each role
the route invokes, it passes that role's generated `nwdes prompt` bundle verbatim,
and that role, not the host, runs its kind's verbs. Facts the route assigns to the
host, such as `feature new` and `slice set`, stay with the host.
Run every nwdes command from the checkout's top level; roots default to cwd and
the repository root, and lane verbs resolve the main worktree. The first add,
set or remove creates the draft. Use `open --from-current` to revise current
authority; close with no draft validates empty values.

Keep the defect and regression obligation on the same public observation.
Use `nwdes prompt` for the selected architect and acceptance designer.
The architect records design values with design verbs; the acceptance designer
records acceptance rows for its assigned slice and closes its draft.
Roles supply typed semantic values; nwdes constructs ids, structure and
serialization, rather than requiring handwritten authority documents.

The host runs the declared verification commands against the original pre-fix
source to observe RED, then against the native crafter's implementation to
observe GREEN. Do not substitute an already-fixed HEAD for the original source.
Keep the actual command results as evidence; no verification seals are needed.

The crafter records files and command results with craft verbs for its
assigned slice. The host chooses the next action and independently invokes
the installed reviewer and fresh public-perspective examiner on prepared evidence.
The reviewer records findings with review verbs; the examiner uses
`nwdes expectations` before oracle authoring and `nwdes examine` for final
verdicts through the same CLI. Resume from the
feature's handoff and briefs with `nwdes document`; nwdes keeps no workflow state.
