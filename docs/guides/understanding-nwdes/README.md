# Understanding nwdes

This page explains what the `nwdes` command is, what it deliberately does
not do, and how its design keeps records honest. `nwdes` is the assistant's
tool; how you point your assistant at it is in
[For your assistant](../README.md#for-your-assistant). For step-by-step
delivery, read [Deliver a feature](../nwdes/deliver-feature.md); for every
verb and option, read the [nwdes reference](../nwdes/reference/index.md).

## A tool, not a runner

**nwdes** is the delivery tool of nWave 4. A **role** is a specialist agent
with its own skills (product owner, architect, acceptance designer, crafter,
reviewer, examiner). nwdes builds the artifacts those roles work from:

- one canonical **handoff** per feature — the JSON file
  `docs/feature/ID/handoff.json` in your repository that holds the feature's
  recorded facts;
- role prompts, output schemas, briefs and review packets rendered from that
  handoff;
- run records written next to the handoff when a role closes its work.

What nwdes never does is just as important:

| nwdes never | Instead |
|---|---|
| Calls a model or launches an agent | The host (Claude Code, Codex, OpenCode, OMP, ...) invokes the roles |
| Runs the slice's declared verification commands or selects tests | The host runs them and keeps the observations (the examiner's own bounded probes inside EXAMINE are the one exception — see the [examine reference](../nwdes/reference/examine.md)) |
| Keeps a workflow ledger, gates or a next-step cursor | The root assistant reads the results and decides the next step |
| Submits or repairs role output | Each role records its own typed values and closes; refusals go back to the same role |

The **root assistant** is the session you talk to. It orchestrates: it
chooses the next operation, passes each role's generated prompt verbatim, and
reads the actual command results. **Humans** decide genuine scope and
trade-offs. Because nwdes holds no workflow state, nothing is hidden behind a
progress bar: what exists is the handoff, the run records and the real
command output.

## Correctness by construction

nwdes behaves deterministically because it gets its shape from construction,
not from enforcement. The tool builds each step itself — the handoff, role
prompts, output schemas, the kind verbs roles record with, the lane verbs —
and an LLM only supplies typed values into that form. The wrong state is not
hunted down afterwards; it cannot be written in the first place. Records stay
honest because the tool makes wrong states hard to produce:

- **Roles type values, they do not write JSON.** Each role calls its kind's
  verbs (`nwdes product promise add`, `nwdes review finding add`, `nwdes
  examine verdict set`, ...). nwdes assigns the IDs, builds the form and
  serializes the file. A role cannot hand-craft a malformed record.
- **A close is checked before it is published.** Every recording ends with a
  `close` that carries an outcome and a diagnostic. An invalid close is
  refused and the draft is preserved unchanged, so the owning role corrects
  its own values.
- **Every refusal states WHAT, WHY and HOW.** One concrete example: a
  reviewer who runs `nwdes review close` without having recorded any
  observation is refused with `ReviewUnobserved` — the refusal names the
  missing fact, explains why an unobserved review cannot be published, and
  says how to record one. The close simply cannot produce an "accepted
  review" that nobody observed.
- **Dangerous operations report every problem before acting.** `nwdes lane
  integrate` lists all admission problems in one pass before it changes
  anything, and never force-pushes or deletes undeclared files.

The predecessor delivery runtime pushed the session into shape from the
outside, with hooks and run-time checks of its own; those are gone with it.
v4 moved the guarantees into the form: nwdes makes no model calls and
enforces no gates — the host runs the models and the verification commands,
the root assistant decides the next step, and humans decide scope. The hooks
nWave still installs today carry attribution, session notices and a write
guard, not delivery gates.

Determinism by construction is a property of the tool, not a duty on the
reader: your assistant gets it by running nwdes instead of hand-writing
delivery records.

## Three routes, one choice

A **route** is the way a Request travels. Three are open:

1. **Spine waves** — the `/nw-*` commands (discover, discuss, design,
   distill, deliver, ...). Whole-feature default: delivery gates, independent
   review and source-blind EXAMINE where applicable.
2. **Host-led nwdes steps** — the root drives the roles with the prompts
   `nwdes prompt` builds. Roles record typed values with their kind verbs and
   close their drafts. A public oracle (an executable check of the promised
   behavior) is approved before code is written.
3. **Working directly** — fastest. No gates, no independent review, no
   retained authority, so nothing attests the result.

The rule for choosing: what must survive the session, and what would a late
refusal cost? The root assistant opens each Request with a working size
assessment — **S**, **M** or **L** — and its reason. That label is an
explanation of the current judgment; it never decides the route. A revised
label never switches the route by itself, and working directly remains a
valid answer when little must survive.

## Honest limits

- nwdes is not a requirement for all new work. It is the host-led route, one
  of three; the choice is stated per Request.
- nwdes does not verify anything itself. Verification lives in the host's
  real command runs; nwdes only records what roles typed.
- If an installed role cannot run, the route stops with its cause. Only human
  authorization permits substituting the host's default agent for that role,
  and the substitution is reported.

## Where to read next

| Topic | Page |
|---|---|
| The artifacts and the delivery order | [Understanding delivery artifacts](../understanding-delivery-artifacts/) |
| The workflow contract in detail | [nw-nwdes skill](../../reference/skills/nw-nwdes.md) |
| Every verb and option | [nwdes reference](../nwdes/reference/index.md) |
| Route and size assessment | [nw-auto skill](../../reference/skills/nw-auto.md) |
| What changed in v4 | [What's new in v4](../whats-new-v4/) |
