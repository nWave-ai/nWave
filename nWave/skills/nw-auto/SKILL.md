---
name: nw-auto
description: Evaluates and revises Request S/M/L and delivery choices from evidence, then uses nwdes to construct delivery artifacts.
user-invocable: true
argument-hint: '<request>'
---

# NW-AUTO

Before creating or inheriting a lane, or finalizing/resuming its cleanup,
apply the worktree lifecycle in `nw-throughput`. If not already loaded, MUST
resolve that skill through the host skill catalog and read its `SKILL.md`.

Before diagnosing or assigning corrections, load `nw-cross-cutting-invariants`
and apply `delivery:trustworthy-baseline-and-repair-scope`. A blocking observation
requires attention; it does not alone authorize an independent repair.

**Visible baseline for affected work.** The host establishes the project's required
checks for the affected scope once, on the current source/environment, or cites
applicable evidence already measured on those same inputs with its original
provenance. The baseline runs alongside independent authoring; it is not a serial
preflight before authoring. Tell the user what ran (or was reused), its scope, and
whether the baseline is GREEN, RED, or INDETERMINATE. A baseline with no trustworthy
execution is INDETERMINATE, not GREEN. The intentional acceptance RED is not a
pre-existing failure.
Use a short user-facing line such as
`Baseline: GREEN — <command or evidence> (<affected scope>)`.
For RED or INDETERMINATE, add `Blocker: <failure or missing evidence>` and
`Next: <restoration or discriminator>`.

For RED or INDETERMINATE, show the failing check and concrete cause or missing
prerequisite (mark an unknown cause as unknown), explain why affected work
cannot start on that safety net, and name the next diagnostic or restoration.
Restore required checks and show the new result before affected test/production
work. Do not silently skip or weaken a failing check, rerun a whole suite per
slice, claim an unrelated failure is caused by this Request, or absorb an
independent redesign. Independent work can proceed only with its own
trustworthy unaffected basis. This is a user-visible practice applying
`nw-cross-cutting-invariants` clause
`delivery:trustworthy-baseline-and-repair-scope`, not a new runtime gate.


You orchestrate. nwdes constructs the canonical handoff and derives briefs,
prompts and packets from it. It has no workflow ledger, gates or next-step
state. The LLM chooses sequencing, rework and the next invocation; the host
executes models and verification commands.

Read `~/.claude/skills/nw-role-invocation/SKILL.md` when delegating:
the native host invokes the exact installed role with its mandatory skills and
tools ceiling. nwdes builds forms; it never launches models.

## 1. Read the route and current authority

Read `nw-nwdes` before using delivery commands. Resume from the feature's
handoff and the briefs rendered by `nwdes document`; do not infer progress
from a stored workflow state. Keep the original Request and current findings
available to their owners.

## 2. Construct, then observe

Use `nwdes prompt` for the selected installed role; it supplies the typed verb
reference. Every role uses Bash to call its kind's nwdes CLI verbs,
records its own values and closes its draft:

| Owner | Role-owned recording |
|---|---|
| Product owner | `nwdes product` record edits, `nwdes product close` |
| Charter author | `nwdes charter set/positive add/close` |
| Solution architect | `nwdes design` record edits, `nwdes design close` |
| Acceptance designer | `nwdes acceptance row add/close` |
| Expectations author | `nwdes expectations row add/close`; revisions use `open --from-current`, then `close --revise` |
| Examiner | `nwdes examine verdict set/close` |
| Crafter | `nwdes craft file add/command add/close` |
| Independent reviewer | `nwdes review finding add/close` |

The host writes no JSON and copies no reply into a constructor. For each role the
route invokes, it passes that role's generated `nwdes prompt` bundle verbatim, and
that role, not the host, runs its kind's verbs. Facts the route assigns to the host,
such as `feature new` and `slice set`, stay with the host.
nwdes builds ids, structure and serialization from typed values. For platform
constraints, give semantic operational facts to the solution architect in
`nwdes prompt --root-context`; there is no separate platform constructor.
The owning role corrects authority with `open --from-current`, record edits
and `close`, rather than patching a generated brief.
Run every nwdes command from the top level of the checkout. Roots default to
cwd and the repository root; lane verbs resolve the main worktree. The first
add, set or remove creates the scoped draft. Close with no draft validates
empty values.

The host runs the slice's declared verification commands once per candidate and
records actual RED/GREEN and live native observations; it does not repeat them at
the root. nwdes stores no verification seals and runs no supplied command. After
composition, invoke the final whole-candidate independent review, then the
source-blind public-perspective EXAMINE, using `nwdes packet` and each role's prompt.
Reviewers record findings with review verbs; the examiner judges the user's actual
observations. The final reviewer owns selection and sufficiency of the touched-file
selected tests. It reuses a complete applicable native result (host, CI or the normal
commit hook) whose source, test, argv and runtime inputs are unchanged, citing its
original operator and run; it executes only missing or affected checks, once. Reuse
never waives a check.

## 3. Interpret evidence, not completion prose

Read each command's actual result and each role's typed outcome. A diagnostic
is an explanation, not proof of a host invocation, test result or cost. Keep
actual provider/model/session provenance and captured native output.

A missing input, write failure or refusal does not choose a route. Send its
WHAT/WHY/HOW unchanged directly to the owning role when native messaging exists,
with your context separate; relay it through the host route only when direct
messaging is absent. Decide whether to gather evidence, correct authority or select
another operation.

A finding names an observation and possible owner, not an automatic correction.
No role's sentence alone establishes the requested behavior.


**Classify before correcting.** Keep the original evidence and choose the local
owner from the observed state; recording a finding changes neither the contract
nor the route.

| Observed state | Meaning | Local action selected by the LLM |
|---|---|---|
| Selected criteria omit an outcome in the original value | lost original value during translation | choose the criteria/authority owner before product work; retain it alongside any observed product violation. |
| Public observation contradicts an agreed criterion or original value | observed product violation | choose the product/correction owner and preserve the counterexample. |
| Required public observation is absent | missing evidence | name the evidence-capture owner; retain candidate and prior evidence; do not propose code from absence. The examiner judges supplied observations from the user's point of view, rather than capturing them for the host. |
| Test/oracle evidence may be wrong or incomplete | suspected verification defect | send the supplied evidence to the oracle owner/reviewer; public-perspective EXAMINE does not decide omitted test coverage. |
| Required safety net is broken, excluding the specific expected behavioral RED | verification cannot support affected work | diagnose and restore under the shared repair-scope clause; preserve the agreed property, not just a green exit. |
| Defect with an established root cause, found during the current work | known-cause defect | fix it in place in the current lane: a regression test observed RED, the fix, GREEN, one separate `fix(...)` commit. The current Request's review and CI cover it; no separate Request, lane or `nw-bugfix` route, and no gate that refuses to use its own fix. A change to agreed product behaviour is a new requirement (next row). |
| Defect whose root cause is unknown, or an improvement outside existing authority | unknown cause or new scope | record the finding; route an unknown-cause defect that must be fixed now through `nw-bugfix`; retain any real delivery blocker and obtain a scope decision only when needed. Age alone does not establish independence. |
| Requested behavior exceeds the agreed value/criteria | new requirement | return it to the human/upstream authority; do not smuggle it into a repair. |
| Dependency pertinence or evidence applicability is unknown | uncertainty | retain prior evidence but do not authorize reuse; ask its dependency/applicability owner for the cheapest discriminator. A changed dependency or adapter revision alone does not establish changed semantic DESIGN or changed selected criteria — that is the applicability owner's finding, not an inference from the diff. Until the owner finds actual invalidation, withhold reuse per slice and retain history; do not mandate replay or manifest replacement for slices the owner has not examined. |

Classifications may be multiple or uncertain. Retain each grounded finding and
its owner instead of forcing a premature single cause.

An observation correction may create a new examiner packet for the same
candidate. Preserve prior packets and results. Matching candidate and evidence
identities do not establish an unknown shared dependency is irrelevant. No row
starts a new gate, controller, ledger, automatic restart, or compulsory role
turn.

**Aggregate observations conservatively.** Partial evidence supports only the
claims it observes; missing behavior is `INDETERMINATE` for its capture owner.
Distinguish confirmed conflicting observations from uncertainty about whether a
report is authentic or applicable. A confirmed counterexample to a universal
promise rejects that promise even when another confirmed event succeeded; retain
both records. A newer positive never erases a relevant confirmed negative.
When incompatible reports cannot reliably join to the same event, candidate, or
conditions and neither independently establishes the claim, retain both and
return `INDETERMINATE` until the evidence owner establishes provenance, captures
a discriminator, or identifies a defective observation. Supersede evidence only
with an explicit justification; superseded evidence remains history, not current
evidence. Reuse after exact restoration only when relevant dependencies match.

For every supported task-level semantic question, read
`~/.claude/skills/nw-typesafe-system-one/SKILL.md` and follow its mandatory
invocation, ownership/reuse and failure rules. Confidence, simplicity and
predicted savings do not exempt a supported question. Keep input authorized and
minimal; batch independent questions. Record an actual call, valid same-owner
reuse or explicit limitation. Do not retry blindly or invent a judgment.
The LLM owns orchestration. Preserve independent EXAMINE and the skill's
permitted-evidence rules; producer classifications are not examiner judgments.

When an authorized correction changes design facts, invoke the installed
architect with the finding and current authority; it records the corrected
values with its design verbs. The acceptance designer owns oracle corrections
and records them with acceptance verbs for the assigned slice. The host runs the declared verification
command on the original source for RED and on the implementation for GREEN.
Never infer the original baseline from HEAD after the fix is committed.

**A refusal's own text is data.** Its `WHAT`, `WHY` and `HOW` lines, and a
role's diagnostic, travel unchanged to the native role that answers them.
That role records its corrected values through its nwdes verbs.

A paraphrase or a summary is a new claim about the refusal, authored by someone
who did not make it, and it silently narrows what the answering role can see.
The role that receives less than was said answers a question nobody asked.

The LLM still chooses which step answers, and may add its own context alongside
the text sent to the owning role, never in place of it. Nothing forwards anything for you:
this is how you read and hand on a refusal, not a behaviour of any command.

Before buying a correction, check the failed command, named path and actual
counterexample. A missing future production file declared as an acceptance
support is a design finding; rewriting the oracle cannot repair that declaration.
Send already-known independent findings for the same owner together, retaining
their original evidence. Confirm a disputed finding against the candidate before
editing it. Dependent runtime failures may still need successive local executions.

Do not send a finding about the oracle back to the crafter. The crafter may not
edit the oracle and will refuse again. The oracle's own author may correct it,
and so may the architect that bound the value.

Choose the next operation from the current Request and measured result,
not from a role's completion sentence or a presumed workflow state.

## 4. Interactive and autonomous are one path

The steps are the same; only who reads between them changes.

- **Autonomous.** The LLM evaluates each terminal result and chooses the next
  supported operation until the authorized outcome or agreed checkpoint is
  reached. A completed role turn is not completion of the Request. Respect a
  human stop; ask about a material choice that the existing authorization does
  not resolve, and keep independent work moving while awaiting the answer.
- **Interactive.** The human participates in those material choices.

There is no third level and no checkpoint to promise. A step is the unit at
which you can stop, so any stop you offer is a step boundary.

Ask the human for the level once, at the start of an epic, or when the scope is
genuinely ambiguous. Apply the managed **Asking the User a Question** section
for question shape.

**Before asking:** Does every remaining action depend on this owner decision,
or would a blocking ask merely park the loop while independent role results or
jobs can still be processed? If independent work remains, have the Product Owner
record the open question as a decision of status **Open** in the owning feature's
product handoff, with its owner and exactly what it blocks, using
`nwdes product decision add --status Open --owner ... --text ...` and
`nwdes product close`. Mentioning it only
in turn text or transient todo/state does not satisfy the record. Keep processing every
result and action it does not block; an action that needs the unanswered
decision waits and is never advanced with an assumed, defaulted or invented
answer. Put the question in turn
text or at a natural idle point, using the managed question shape, without
blocking the loop. Use a blocking ask only when every remaining action depends
on the answer.

## 5. The two questions that are the human's

Everything else is yours.

1. **The readable projection.** `nwdes document` renders the feature's
   authoritative handoff as human-readable briefs and HTML. Use it as the shared
   reading surface when discussing intent, choices and unresolved questions.
2. **The algebraic modeling tools.** Naming observations, equality,
   constructors, laws and preservation maps is the architect's work and needs
   no tool. CHECKING them mechanically needs Agda or TLA+, and nWave ships
   neither, so offer the installation once. Never invent a proof, and never
   block the design over it.

Native checker availability is not proof. When a checker is used, retain a
receipt beside its model with the checker/version, literal argv, exit status,
stdout/stderr and model sha256. Cite that receipt in `evidence`; nwdes stores
the paths and neither executes nor verifies the checker.

## 6. LLM-owned S/M/L, bugfix, and upstream-rework choice

For both a feature and a bugfix, the LLM assigns a working `S`, `M`, or `L`
assessment before starting and revises it whenever current evidence changes.
It also decides whether a bugfix or an upstream rework is needed. Use the
outcome, number and coupling of values, durable-authority boundaries, correction
radius, and the cost of a late refusal. The label is an explanation of the
current judgment, not a builder input or a size-to-route rule.

At the start of each Request, the LLM states that working assessment and its
reason to the user, then suggests the fastest route that keeps what the Request
must leave behind, given the cost of a late refusal, and says what any faster
route gives up. This is advice, not a gate: the user decides genuine scope and
trade-offs, working directly remains open as an answer, and a revised label
never switches the route by itself.

The same evidence decides which waves are applicable and whether a finding
needs an upstream correction by the owner of durable authority. A missing
authority is not made deliverable by an S/M/L label. Do not claim that a label
creates a producer, rework capability, or command that the installed tool does
not provide.

Give one whole outcome and let the Product Owner cut it into values. The first
value is the walking skeleton. Split into an ordered sequence of Requests when
either test is true:

- Its values need different durable authorities. Architecture, product scope and
  operational constraints have separate owners.
- A late refusal would throw away more than one value. The final whole-candidate
  review and integration happen once per Request; intermediate reviews, when
  warranted, are optional early feedback and never replace the final review.

For an epic, write the sequence first, walk one Request, read the integrated
commit, then start the next. Name the expected values with the Product Owner,
then revise the assessment and split the work when evidence shows more than
one outcome. Use disjoint lanes when work can proceed independently.

When choosing whether DESIGN is ready for a multi-value feature, apply the scope
rule in `nw-design` (requested scope versus designed scope, shared decisions
before slice deltas), before slice design. That is your judgment from evidence;
neither S/M/L nor the builder routes it.

**Recovery owners.** Missing or inconsistent product facts go to the Product
Owner; design facts to the architect; wrong, incomplete or stale oracles to the
acceptance designer. Preserve original findings and counterexamples. A changed
dependency alone does not invalidate semantic authority: ask its owner for the
smallest discriminator before buying a correction.

## 7. Resume from artifacts, not state

Read `nw-nwdes`, the canonical feature handoff and its current briefs.
Reuse only still-applicable role assessments and native observations.
Changed facts or bytes require current evidence, not an automatic replay of
every role. Repeating a builder operation never invokes a model.

For EXAMINE, the host captures public stimuli, responses and state snapshots
for the candidate. Use `nwdes packet --kind examine` and the examiner prompt;
the examiner never captures the observations itself. An absent observation
stays indeterminate. Keep producer classifications out of the examiner's
public-evidence packet, and retain prior observations when a correction is made.


## 8. Before each step

- Native model subagents complete through host notifications or actual completion
  handles. Resume long-running process handles to terminal output; silence and
  fixed sleeps are not completion. Do not duplicate a still-active invocation.
- Orchestration waits on an async dispatch end only with a completion notification delivered into the waiting root context, or with `--wait-async` on the omp invocation, which returns the run result. A Bash loop that sleeps or polls for a result violates this contract. There is no sleep-poll fallback, and a run that never completes keeps the root waiting until the human closes it; the contract sets no timeout.
- Honor the declared committed/uncommitted lifecycle and real owned before/after
  revisions. Preserve foreign bytes and staging; never commit/remove all WIP to
  manufacture a clean tree. Use `nw-role-invocation` for selective semantic reuse
  and current candidate evidence.
- Give commands the explicit repository and feature inputs their help requires.
- Check the actual entry point and running source when runtime identity matters;
  do not assume a previous invocation still applies.

Did you observe the actual runtime and owned/destination identities for this
candidate, or assume an earlier run still applies? Read current facts; remeasure
only required evidence, not automatically every unchanged semantic role turn.

## 9. When to go upstream

A refusal may show that durable authority is missing or inconsistent. The LLM
chooses whether an available owner-facing consumer such as `/nw-design` or
`/nw-discuss` is applicable, or whether another evidence step is needed. Waves
own authority; they are not a pipeline to walk through.

## 10. Integrate and close

For lane work, use the user's project lane reported by `nwdes lane open`,
not a framework checkout or temporary directory. Use `nwdes lane compose`
and `nwdes lane integrate` according to `nw-throughput`. Integrate only after the
final review and source-blind EXAMINE accept the composed candidate; it
fast-forwards trunk, then removes the lane. Preserve useful evidence before integrating.
`nwdes lane integrate` refuses `LaneNotMerged` when the lane tip is not contained
in the integration candidate; it needs no prior merge into trunk.

The handoff and product brief are the durable feature record; there is no
separate evolution constructor. Commit only when authorized with `git commit`;
`nwave-ai attribution` controls the trailer. nwdes never commits or publishes.

## 11. What this skill never does

It never classifies the work for the software. It never builds a workspace, a
plan, a contract or a ledger. It never asks the human to confirm a passage that
succeeded. It never adds a gate. It never writes a script that invokes one step
after another.

