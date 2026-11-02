---
name: nw-throughput
description: Evidence-led orchestration for maximizing delivery throughput with independent fan-out, capacity-bounded local test runs, long runs batched off the box, and concise whole-value evidence.
user-invocable: true
---

# nw-throughput

Before diagnosing or assigning corrections, load `nw-cross-cutting-invariants`
and apply `delivery:trustworthy-baseline-and-repair-scope`. A blocking observation
requires attention; it does not alone authorize an independent repair.

Load `nw-cross-cutting-invariants` and apply `flow:findings-go-to-the-owner-directly` when dispatching or coordinating roles.


## Constraint

The bottleneck is usually the shared machine or a causal boundary, not the
number of available agents. Keep cloud reasoning busy; the local constraint is
usually machine capacity (often memory, then CPU), not exclusivity. Measure which
resource saturates, and stop adding lanes when contention increases end-to-end
wall time.

## Strategy

1. Select the nearest measurable constraint and shortest falsifier.
2. Fan out only independent work with disjoint ownership in detached worktrees;
   apply the worktree lifecycle below when creating or inheriting a lane.
   A pending owner answer blocks only the work that depends on it; see nw-auto
   §4.
3. Admit local test runs by capacity, not by one exclusive lock. Before each
   admission, the operator checks current box-wide load, including launchers
   outside the queue, and the headroom of any existing shared process,
   container or scope cap that bounds the lanes. Gate on `MemAvailable`, not
   `MemFree` or load: judge whether current capacity covers the run about to be
   admitted alongside work already running on the box. A shared cap gets the
   same judgement: its current headroom must comfortably cover the run.
   Admission is a judgement on current capacity and observed contention, not
   arithmetic over recorded peaks; there is no recorded floor to consult.
   A single run passes the same check.
   Check the measured binding resource too: defer CPU-saturating work when it
   would increase end-to-end wall time or starve focused runs.
   This is operator practice, not atomic reservation accounting: no box-wide
   reservation mechanism exists here, and per-worktree locks cannot provide one.
   One operator coordinates admissions across lanes; independent operators must
   coordinate before launch because a load snapshot alone cannot prevent races.
   Keep exclusivity only for a resource shown to be shared and mutable.
   Never run the whole suite locally; keep reproductions bounded and respect
   Git-write restrictions. When test-impact selection (rule 5) selects the whole
   suite, including when it cannot decide and so selects every test, or local
   capacity forbids running the selected set, dispatch the complete selected set
   to CI instead; never silently narrow the selection to fit, and report the
   change as unverified until that run returns, or for as long as no CI capacity
   can run it. Starving the box can kill other lanes' work and can corrupt `.git`.
   An OOM-killed run is INDETERMINATE, never a red.
4. The operator orders waiting runs shortest first (RED, GREEN, focused tests
   before broad runs), with aging: after a broad run waits 1200 s (Ale's chosen
   bound), it goes next and nothing behind it starts until it fits. Never
   preempt a running test. This is a manual queue policy, not an implemented gate.
5. Minimize broad local runs. Do not rerun a broad scope locally once per
   commit or per slice. Commit with the focused checks and batch related slices.
   The focused checks are the tests a reliable test-impact analysis selects over
   the change (dependency-affected tests), run locally within rule 3 or, when
   rule 3 forbids the selected set, as one complete CI run; the default CI suite
   (300 s unless a repository ADR sets another) and each feature's infrastructure suite at its
   declared trigger run the rest (`test:feedback-loop-budget` in `nw-cross-cutting-invariants`).
   In existing Request context, state a maximum batch size before accumulating
   commits; close the batch at that limit or at the end of the Request, whichever
   comes first. The operator then dispatches one broad run by hand on CI capacity
   outside the contended machine before publication. Self-hosted CI on the same
   box is local capacity, not off-box capacity. If no off-box capacity exists,
   run the batch's impact-selected tests once locally as the only broad run,
   subject to rules 3 and 4; a selection rule 3 sends to CI never runs locally
   and the batch stays unverified until CI capacity runs it.
   A red broad run names its failing tests. Keep the other work moving. Keep
   CI/CD health a standing responsibility: for each red batch open one
   short-lived CI-recovery lane with a stated deadline in existing task context.
   Classify every failure first, fix pipeline and test-infrastructure defects
   there, and route a product or oracle regression to the Request that owns it.
   Keep that owner reachable until batch verification; a closed Request must be
   reopened or receive an explicit successor owner, not silently lose the defect.
   Close the recovery lane when the batch is green or its deadline is reached;
   at the deadline transfer unresolved work with preserved evidence and a named
   owner under the worktree lifecycle below. Transfer is not resolution.
   A red broad run never ends by being ignored: promoting a build to a release
   requires the whole broad run green on that exact build. The batch run attests
   the batched candidate, not each commit inside it.
6. Fan in on the whole delivered value. Keep the final whole-candidate review,
   source-blind EXAMINE, integration, observation and cleanup; the orchestrating
   LLM chooses and invokes them, while nwdes constructs the canonical handoff and briefs.
7. Measure wall time, queue wait versus service time per run class, peak
   memory, cost, tokens, retries, tool calls, and human intervention against
   the outcome. Tune admission judgement from observed capacity and contention.

## Lane flow

- **CI gates the push, not integration.** CI is an asynchronous pipeline over
  trunk snapshots: full-matrix CI before push stays required, and it gates only
  the push of trunk, never local integration of a lane. A red also present on
  trunk belongs to the one CI-recovery lane, which keeps a named owner until
  green.
- **Unintegrated lanes are a work-in-progress count, not an admission limit.**
  Count lanes whose measured tips remain outside their destination to describe
  current WIP, not to cap lanes or admit another workload. Strategy rule 3
  remains the box-capacity admission authority for local execution.
- **Rework before new work.** Finish rework of an open lane before opening new
  work (shortest remaining processing time). After 2 consecutive rework
  services one admissible new lane is opened; assuming every rework service
  ends and the loop keeps serving ready work, a new lane's wait is bounded to 2
  rework services once its base exists and a WIP slot is free. Assumption: the
  lane already holds work-in-progress and the rework is shorter than the new
  work, for example
  about 5 minutes against 30. Expected lead-time effect: mean lead time falls,
  because the short job leaves the queue first while the long job waits only
  that short time. Derived from the TLA+ model
  docs/feature/delivery-flow-policy/design/FlowPolicy.tla (ReworkPreempts,
  NoStarvation) and queueing assumptions, not observed performance. Rework
  never skips verification of the changed revision, the final whole-candidate
  review or source-blind EXAMINE.
- **Split out a held value.** When a value is held by an owner question or a
  failing dependency, split it out so the other values continue through verify and
  composition; owner-question scheduling is nw-auto section 4 and the
  separate owner-questions-nonblocking Request, not redefined here. Assumption:
  the held value's work is independent of the other values. Expected lead-time
  effect: the other values stop waiting behind one held value, so mean lead time
  falls. Derived from the TLA+ model FlowPolicy.tla and queueing assumptions,
  not observed performance. Splitting never skips a value's own native verification;
  the final whole-candidate review and source-blind EXAMINE still cover every value integrated.
- **Return a stuck finding to its owner.** A finding still open after 2 rework
  rounds returns to its owner instead of receiving a further patch round.
  Assumption: each rework round is a bounded step and a repeated finding means
  the cause is not in the patch. Expected lead-time effect: the steps one lane
  can take stay bounded, so one finding cannot loop without bound. Derived from
  the TLA+ model FlowPolicy.tla (BoundedSteps) and queueing assumptions, not
  observed performance. Returning a finding never skips verification of the revision
  it changes, the final whole-candidate review or source-blind EXAMINE.
- **Cycle targets stay targets.** The owner's 5 ± 2 minute rework target
  remains a target: it is never reported as met without an observed
  measurement, and no rule above lowers required assurance.

## Bounded observed correction context

For a bounded correction with an observed counterexample, targeted context may
be used when it supplies the observation/counterexample, requested delta, exact
candidate, and references to the applicable authorities. Fetch further context
when a required fact is missing; do not repeat the entire narrative handoff.
Preserve semantic decisions and declared quality, then return the commands
actually performed, their evidence, and any facts still missing. This is a
conditional context choice, not a blanket removal of guidance.

## P2: diagnose a changed interface surface once

When the first failure reveals an interface migration, the orchestrating LLM
chooses the related property x consumer test-file scope and runs that complete
scope through the repository's native test executor before paying for the next
broad run. Collect all failures in the selected scope, repair the coherent
contract within the shared repair-scope clause, then run the required broad verification.
Diagnosing an interface migration does not itself authorize that migration. Selected files are evidence
about that scope only; they do not establish whole-project coverage.

Use the repository's own affected-test selector when it exists. In this Python
repository, `python3 scripts/hooks/pytest_touched_files.py --diagnose PATH ...`
is available: it launches every selected runnable file within the normal
bounded ceiling without early stopping, clears ambient `PYTEST_ADDOPTS`
selection filters, and prints the exact argv plus deferred and uncovered paths.
Repository collection configuration still applies. It returns nonzero for
failures, zero collection, an oversized scope, or a scope left incomplete by
deferred/uncovered paths. The ordinary pre-commit command runs every selected runnable file
within the same bounded ceiling and reports every failure, not only the first. This example is not a
cross-language requirement: another repository uses its native executor and
must report the corresponding selected, deferred, and uncovered scope loudly.

The LLM selects the scope and the next commands from the observed failures. Do
not add a controller, automatic retry, phase transition, or gate for this
workflow.

## Disk ownership and retention

Are build outputs multiplying with each lane or verification? Admit heavy local
workloads by capacity, reuse read-only toolchains and environments, and give each
writable build directory one owner. Keep reusable generated outputs in the
principal repository and bind the isolated verifier to them; do not copy build
trees or environments into every lane. Cooperative verification across linked
lanes holds one repository-wide lease. Other native writers must be stopped by
the caller before using those shared outputs.

- **Verification workspaces:** the host owns source isolation, environments,
  outputs and cache invalidation. Reuse only explicitly owned generated outputs
  whose native recipe supports it; never share mutable source, environments or
  metadata by declaring them a cache.
- **Native cache contract:** declared commands own dependency, toolchain, flags,
  generated-input and timestamp invalidation. Execute checks, never replay cached
  verdicts. Finish all writers; a daemon still writing is not quiescence.
- **Freshness and evidence:** one owner per verification. The host runs each required
  verification command once per candidate, retains source/oracle/support/argv/runtime
  identities with actual output, and owns the live native observations; the root never
  repeats them. The final reviewer owns selection and sufficiency of the touched-file
  selected tests. It reuses a complete applicable native result (host, CI or the normal
  commit hook) whose source, test, argv and runtime inputs are unchanged, citing its
  original operator and run; it executes only missing or affected checks, once. Reuse
  never waives a check. A changed input reverifies the affected behavior.
  Preserve candidate-bound
  evidence outside a mutable checkout before cleanup. nwdes stores no verification seals
  and has no fresh/recorded verification mode.
- **Retention and interruption:** establish quiescence and retain pending
  evidence before removing owned workspaces. Never remove principal outputs or
  external caches merely because an inherited environment names them. Prove
  ownership rather than recognizing a familiar basename.
- **Durable snapshots:** retain source and minimal evidence the named consumer
  needs. A hash or Git commit cannot recover untracked evidence; retain its bytes
  and verify every retained symlink target before removing a source checkout.
- **Delivery lanes:** create feature lanes with `nwdes lane open` in the user's
  project rather than temporary or cache directories. Preserve useful work in
  inherited lanes before authorized cleanup; never move or discard it merely
  to fit a new layout.
- **Evidence boundary:** report measured allocation before/after and remaining
  owned artifacts in existing delivery evidence. Distinguish source delivery,
  preserved evidence and physical cleanup. EXAMINE may assess supplied public
  disk/lifecycle observations when the Request promises those effects; it does
  not inspect private paths or execute cleanup. Do not create a universal disk
  quota, new manifest, automatic orchestrator or acceptance gate.

## Worktree lifecycle

Use at lane creation, inheritance, integration and resumed cleanup. Scope:
the Request's owned or explicitly inherited lanes, including temporary build
and evidence copies. Preserve other owners' work; this is no machine-wide sweep.

- **Creation** — In existing task context, name the checkout's purpose, owner
  and condition under which it is no longer needed. Keep one named scope per
  lane; place discovered work under its actual owner in the existing disposition.
- **Reconciliation** — Does the current inventory cover every owned/inherited
  lane and useful residual, or only the accepted feature? Refresh it from current
  bytes and assign each residual a disposition below before claiming closure.
  Read Git's actual worktree registrations, current tips, staged/dirty/ignored
  content and destination ancestry. Classify missing, locked and unregistered
  directories separately; a familiar directory name does not establish ownership.
  The LLM chooses integration order from actual dependencies and observations.
- **Completion assertion** — Before claiming integration, establish the named
  revision's ancestry at its destination. `nwdes lane integrate` refuses
  `LaneNotMerged` when the lane tip is not contained in the candidate; it needs no prior merge. A clean worktree is not
  delivery evidence; an unmeasurable tip stays indeterminate. Preserve content
  until integration and retention obligations are satisfied. Apply
  `delivery:completion-claims-the-destination` from `nw-cross-cutting-invariants`.

| Disposition | Required basis in existing task context |
|---|---|
| Integrated | Destination and integration evidence for the exact revision. |
| Superseded | Legitimate replacement reference and verified retained replacement bytes. |
| Transferred | Named backlog item plus a verified recoverable artifact outside the checkout, bound to the exact revision. Transfer leaves the work unfinished. |
| Unfinished | Concrete residual, owner and next action; keep required checkout bytes until a verified destination exists. |

- **Cleanup** — Have all useful current revisions survived outside the checkout,
  and has active use ended, or are you relying on an old archive receipt? Verify
  actual destination bytes for current work, including dirty/untracked work and
  needed evidence, or its legitimate retained replacement, immediately before
  removal. Bind that observation to the current revision. Edits invalidate
  verification for the changed revision; refresh preservation and verification.
  Establish no active users/writers and keep the checkout quiescent through
  removal; if this cannot be established, retain it and state the next action.
- **Removal** — `nwdes lane integrate` fast-forwards trunk to CANDIDATE, then
  deletes declared disposable files and removes the integrated feature lane without
  force. One pass refuses every problem, including unmerged work; never work around a refusal. For dirty/superseded historical
  lanes or archive-only copies, use explicitly authorized caller cleanup after
  verified preservation. Report archive disposition, never invented integration.
  Name every remaining checkout's purpose and next action.
- **Resume** — After interruption, resume the existing inventory/dispositions;
  reobserve bytes, destinations and active use before the next cleanup action.
  Report feature acceptance separately from residual completion and checkout
  removal. Use existing task context; no new ledger, document or runtime gate.

Incident anchor: `docs/analysis/2026-09-26-worktree-reconciliation.md` — selected
integration left mixed residual work; evidence copies had separate retention
purposes. Feature closure alone did not reconcile those checkouts.

## Batch candidate owner

For a batch of approved changes on one composed candidate, name one existing executing crafter that has execution tools as candidate owner. It composes settled owner contributions, generates required derived data, owns the existing native verification, and handles demonstrated corrections with their owners. Owners coordinate related callers, supports and docs directly under `flow:findings-go-to-the-owner-directly`; the candidate owner never takes another role's artifact. The candidate owner is not a compulsory peer-message relay, a permanent coordinator, a substitute reviewer or a second trunk writer. Root keeps path, scope and trade-off decisions, real unresolved blocks, the final independent review, EXAMINE and trunk integration.

## Feature record before cleanup

Read `nw-nwdes` for the feature lane route. Compose once the lane's implementation is
stable: `nwdes lane compose` merges trunk into the lane and retains its printed
EXPECTED/CANDIDATE identities. Independent implementation and verification may run in
parallel before composition; no speculative final EXAMINE runs. On the composed
candidate, the final whole-candidate independent review runs first; once it accepts,
the source-blind EXAMINE runs, then `nwdes lane integrate` with those exact identities.
If trunk moves, compose again and obtain the evidence applicable to the new candidate.

The feature handoff and product brief are its durable record; no separate
evolution constructor, input or generated evolution document is needed.
Preserve useful evidence before integration, and commit authorized changes
with `git commit`; `nwave-ai attribution` governs the trailer.

Cleanup follows integration: residual checkouts are reconciled after `nwdes lane integrate`,
never on the critical path before the final review or EXAMINE. `nwdes lane integrate`
fast-forwards trunk, then removes the lane; one pass refuses every problem and changes
nothing, so rerun it after a refusal.
The LLM revises S/M/L, applicability and upstream corrections from evidence;
nwdes never uses a size label to route or execute work.
