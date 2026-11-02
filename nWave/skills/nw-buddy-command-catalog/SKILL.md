---
name: nw-buddy-command-catalog
description: Current public nWave delivery commands.
user-invocable: false
disable-model-invocation: true
---
# Command Catalog

Read `nw-nwdes` for the authoritative host-led route, role/task mapping and
current options. Use `nwdes <verb> [<action>] --help` before composing an argv.

| Need | Command or owner |
|---|---|
| Choose collaboration mode | `/nw-mode-select` and `nw-human-collaboration`; retain an existing choice |
| Start delivery | `nwdes feature new`, then the Product Owner's generated prompt; it records with `nwdes product` verbs |
| Define a slice | `nwdes slice set` |
| Resume | Read the feature handoff and briefs; `nw-nwdes` supplies the route, not stored workflow state |
| Read authority as a person | `nwdes document` renders full briefs and HTML |
| Obtain exact role instructions | `nwdes prompt` |
| Obtain a role's recording verbs | `nwdes prompt` includes its generated verb reference; `nwdes <kind> --help` describes CLI flags |
| Clarify product meaning | `/nw-discuss <outcome>`; `nwdes prompt --role nw-product-owner --task discuss` supplies the Product Owner's recording instructions |
| Supply a public charter | The Product Owner uses the generated `nwdes charter` verbs |
| Supply design decisions | The owning architect uses generated `nwdes design` verbs; missing architecture returns to that owner before acceptance authoring |
| Author acceptance coverage | The acceptance designer uses generated `nwdes acceptance` verbs for the selected slice |
| Supply platform advice | Give semantic platform facts to the coordinating architect through the generated prompt's `--root-context`, not a separate constructor |
| Prepare review or public examination evidence | `nwdes packet`; the host captures observations |
| Review a candidate | Native installed reviewer records with `nwdes review finding add/close` |
| Fix or revise public expectations | `nwdes expectations row add/close`; revisions use `open --from-current`, then `close --revise` |
| Record examiner verdicts | `nwdes examine verdict set/close` |
| Implement and verify | Native installed crafter records with `nwdes craft file add/command add/close`; the host runs each declared RED/GREEN command once, and the root consumes its attributed evidence |
| Isolate and integrate feature work | `nwdes lane open`, `compose`, `integrate` (fast-forwards trunk, then removes the lane) |
| Configure provider/model facts | `nw-rigor`, then `nwave-ai model set`; the host invokes models |
| Diagnose an installation | `nwave-ai doctor` |
| Commit authorized changes | `git commit`; `nwave-ai attribution` governs the trailer |

The LLM revises S/M/L, applicability, sequencing and upstream corrections from
evidence. nwdes constructs artifacts without workflow ledgers, gates or a
next-step controller, and runs neither models nor verification commands.
Every role uses Bash to record semantic values through its kind's nwdes CLI
verbs from its generated prompt, then closes its draft.
Run every nwdes command from the top level of the checkout; roots default to
cwd and the repository root, and lane verbs resolve the main worktree. The first
add, set or remove creates the scoped draft. Use `open --from-current` to revise
current authority; close with no draft validates empty values.
The host writes no JSON and copies no reply into another command. For each role the
route invokes, it passes that role's generated `nwdes prompt` bundle verbatim, and
that role, not the host, runs its kind's verbs. Facts the route assigns to the host,
such as `feature new` and `slice set`, stay with the host.
nwdes constructs ids, structure, paths and serialization. Craft and review
close into the feature's `runs/<kind>[.<slice>].json`, separate from the handoff.
Preserve independent review and public-perspective EXAMINE; a successful close
replaces neither.

Select feature and slice explicitly in the host invocation. The Product Owner
and examiner work from the user's point of view; this does not forbid code access.
Local authoring checks are diagnostic; verification evidence is the host's own runs.
Roles write only declared oracle, supports or targets; nwdes writes the handoff
and closed role records.

Lane configuration belongs in the main worktree's `.nwave/config.json`.
Preserve unrelated settings and choose its intended existing trunk explicitly.
The host owns native execution environments, output/cache locations and retained
observations; no retired verification-cache configuration is needed. Preserve
unknown, tracked, staged and live content before any authorized cleanup.
