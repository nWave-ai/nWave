<!-- BEGIN nWave-beta-section (managed by nwave-ai; do not edit) -->

## nWave (beta) — How to Work in This Project

Three routes are open to a Request:
- Spine waves (whole-feature default): wave gates, independent review and
  source-blind EXAMINE where applicable; durable authorities. Evolution retains
  lasting facts; integration closes delivered work.
- Host-led nwdes steps: the root runs roles with generated prompts. Roles record
  typed values with kind verbs and close. nwdes builds and
  writes authority/run records; the host submits/retains no role reply.
  Public oracle before code; nwdes launches no model. Details: nw-nwdes skill and nwdes --help.
- Working directly: fastest; no gates, independent review or retained authority,
  so nothing attests the result.

The LLM chooses the route by what survives and the cost of late refusal,
and invokes the applicable waves. The final whole-candidate review and integration happen once per Request; embedded per-slice refinement reviews provide early feedback, not final approval.
Each Request opens with the LLM's working S/M/L assessment and why, which never decides the route.
The LLM revises it as evidence changes and suggests the fastest route that
keeps what must survive, naming what a faster one gives up; the user decides genuine scope and trade-offs.
Working directly remains open when little must survive.
Human WIP limit: 2. Finish open work before starting new work; nWave refuses
nothing by count.
When a review or EXAMINE rejects work, or new work is ready, the Lane flow
of the nw-throughput skill holds what comes next.
Whichever route this Request takes, say which one.

nWave is a spine-driven delivery framework. Wave commands (`/nw-*`) carry the
gates; skills carry on-demand knowledge; agents execute. This section is an
INDEX.

Human authority decides genuine scope/trade-offs.

| User wants... | Load / run |
|---|---|
| Validate a problem is real | `/nw-discover` |
| Compare solution directions | `/nw-diverge` |
| Clarify jobs, journeys, outcomes | `/nw-discuss` |
| Architecture, reuse, boundaries | `/nw-design` |
| Deployment / operational constraints | `/nw-devops` |
| Executable public oracle | `/nw-distill` |
| Dispatch one Request | `/nw-deliver` |
| Fix one observed defect | `/nw-bugfix` |
| Review an artifact or diff | `/nw-review` |
| Reduce a noisy test suite | `/nw-optimize-tests` |
| Explicit mutation probe | `/nw-mutation-test` |
| Resume after an interruption | Read-only: `git worktree list`, then `lanes/<feature>/docs/feature/<feature>/handoff.json` and skill `nw-nwdes` |
| Run several lanes in parallel | skill `nw-swarm` |
| Fuller S/M/L evidence, splitting a Request | skill `nw-auto` |
| Anything else — methodology, routing, "what do I do" | skill `nw-buddy` |

**Batch independent tool calls in one turn (one per turn is a violation); sequence only when one result feeds the next.**

### Asking the User a Question

Fixed shape, every time: **context** -> **recommendation** -> **options** (each
with its consequence/risk) -> one direct question. Real section headers and
bold labels — never a wall of text. User-facing output follows **ASD-STE100**
(Simplified Technical English).

Owner answer pending: independent ready work continues; only dependent work waits. Boundary and durable record: `nw-auto` §4.

### Communication

<!-- GENERATED:communication-rules START — source of truth: nwave_ai.platform.effective_config() (ADR-CFG-001 Slice 2 -- ~/.nwave/config.json + .nwave/config.json); do not hand-edit (docgen renders this region) -->
- Communication verbosity: **standard**
- Commit attribution: **enabled**
<!-- GENERATED:communication-rules END -->

### Privacy — Non-Negotiable

nWave stores workflow data locally and collects no telemetry. Jev, a remote question service, is on by default for supported questions and sends only permitted data classes; refuse it with `--jev unauthorized` or `"jev": "unauthorized"` in `~/.nwave/config.json`. `TYPESAFE_API_KEY` is only Jev's technical prerequisite, not its authorization ([PRIVACY.md](../../PRIVACY.md)). Feedback via GitHub Issues is welcome, never required.

<!-- END nWave-beta-section -->
