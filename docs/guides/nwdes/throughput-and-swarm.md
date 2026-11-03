# Running multiple features in parallel: throughput and swarm on one box

*Type mapping (DIVIO):* primary **how-to** (perform parallel delivery of several
Requests on one shared machine); the "auto" section at the end is a short
**explanation** of how S/M/L sizing works. It is not a tutorial and not a
command reference — for verb options see the [lane reference](reference/lane.md).

**Audience.** This page is for the root assistant — the session you talk to — that coordinates parallel delivery on the machine: it opens lanes, admits test runs by capacity, and integrates them. The person decides which Requests are worth parallel capacity and the other scope and trade-off calls, and points the assistant at this guide — see [For your assistant](../README.md#for-your-assistant).

More than one Request is ready to deliver and they share one machine. This guide shows when
to open parallel lanes, how to admit test runs safely against shared memory, how
work flows through lanes, and how to integrate and close each feature.

Resident contracts that already govern the development repository — the
single-trunk-writer rule, the stash ban, and the scratchpad prefix rule — are
kept in its resident project rules; this guide does not repeat them.

## When you need lanes

Open parallel lanes when two or more Requests can proceed independently —
disjoint values, no shared files you must both mutate. If your work is a single
isolated checkout or bugfix, skip lanes: [use-lanes](use-lanes.md) explains the
lane-free path. Lanes isolate work; they do not create machine capacity. The
binding constraint is usually the shared box (often memory, then CPU), not the
number of agents — measure which resource saturates and stop adding lanes when
contention increases end-to-end wall time
(`nWave/skills/nw-throughput/SKILL.md`, § Constraint).

## Opening a lane

Create one lane per feature with `nwdes lane open --feature <ID>` from the main
worktree's top level. You get a worktree at `lanes/<ID>` on branch `lane/<ID>`;
work on feature write commands happens inside the lane
([use-lanes.md](use-lanes.md), steps 1–3). `lanes.trunk` in the project's nWave
configuration must name the actual trunk branch before the first open. Create
lanes in the user's project, never in temporary or cache directories
(`nWave/skills/nw-throughput/SKILL.md`, "Disk ownership and retention" →
Delivery lanes).

## Admitting local runs by capacity

Never run the whole suite locally. Before each local test run, the operator
checks box-wide load — including launchers outside any queue — and gates on
`MemAvailable` (not `MemFree`, not load): judge whether current capacity
covers the run alongside work already running on the box, and whether any
shared cap on the lanes keeps enough headroom for it. Starving the box kills
other lanes' work and can corrupt `.git`. An OOM-killed run is
INDETERMINATE, never a red
(`nWave/skills/nw-throughput/SKILL.md`, § Strategy rule 3).

Admission is operator practice, not an atomic reservation: one operator
coordinates admissions across lanes, and independent operators must coordinate
before launching. Defer CPU-saturating work when it would slow
focused runs. Broad runs that exceed local capacity go to CI as one complete
run; never narrow the selection to fit (`nWave/skills/nw-throughput/SKILL.md`,
§ Strategy rules 3 and 5). The full admission rule text is in the throughput
skill; this guide states only the shape.

The operator orders waiting runs shortest first (focused before broad), with an
aging bound after which a long-waiting broad run goes next; never preempt a
running test (`nWave/skills/nw-throughput/SKILL.md`, § Strategy rule 4).

## Lane flow

- **Rework before new work.** Finish rework of an open lane before opening new
  work. After two consecutive rework services, one admissible new lane may
  open; rework never skips verification, the final whole-candidate review, or
  source-blind EXAMINE (`nWave/skills/nw-throughput/SKILL.md`, Lane flow →
  Rework before new work).
- **Unintegrated lanes are a WIP count, not an admission limit.** Counting open
  lanes describes the box; box capacity (above) remains the admission authority
  (`nWave/skills/nw-throughput/SKILL.md`, Lane flow).
- **CI gates the push, not integration.** Full-matrix CI before push is
  required and gates only trunk push; it never blocks local lane integration.
  A red also present on trunk belongs to one short-lived CI-recovery lane with
  a named owner (`nWave/skills/nw-throughput/SKILL.md`, Lane flow and §
  Strategy rule 5).
- **Peer questions travel directly.** When native agent messaging is available,
  subagents contact the responsible role directly and root receives the outcome
  or blockage; where it is genuinely absent, the root-mediated path remains
  (`docs/feature/swarm-default-for-all-agents/handoff.json`, fact F588;
  cooperation-by-default on every host is fact F589). No nWave inbox, transport,
  registry, or protocol is introduced
  (`docs/feature/swarm-default-for-all-agents/architecture.md`, decision D53
  and constraint K13).

## Integrating and closing a feature

Each feature follows the standard delivery order
([deliver-feature.md](deliver-feature.md)): compose the lane, obtain the fresh
independent final whole-candidate review, then source-blind EXAMINE, then
integrate. `nwdes lane compose` merges trunk into the lane and prints the
EXPECTED and CANDIDATE identities; keep them exactly. If trunk moves after
compose, compose again. `nwdes lane integrate` fast-forwards trunk to the
candidate, removes the lane without force, and refuses every problem in one
pass before changing anything — rerun the same command after a refusal
([use-lanes.md](use-lanes.md), steps 5–9). Preserve useful lane files and
evidence before integration; cleanup reconciles residual checkouts after
integrate, never on the critical path before review or EXAMINE
(`nWave/skills/nw-throughput/SKILL.md`, Worktree lifecycle and "Feature record
before cleanup").

With several lanes live, integrate in dependency order and keep other lanes
moving while one batch's broad run is red on CI; a red broad run names its
failing tests and never ends by being ignored
(`nWave/skills/nw-throughput/SKILL.md`, § Strategy rule 5).

## Choosing S/M/L ("auto")

Every Request starts with the LLM's working S, M, or L assessment and its
reason, based on the outcome, the number and coupling of values, durable
authority boundaries, correction radius, and the cost of a late refusal. The
label is a judgment to revise from evidence — it never decides the route, and
nwdes never routes or executes by size label. The LLM suggests the fastest
route that keeps what the Request must leave behind and says what a faster
route gives up; the user decides genuine scope and trade-offs
(`nWave/skills/nw-auto/SKILL.md`, § 6, and its route table). When values need different durable authorities, or a late refusal
would throw away more than one value, split the Request. For the full
decision procedure and lane advice, read the `nw-auto` skill; this guide only
orients you.
