# Feature: pi-harness — nWave software-crafter on the pi coding agent

> DISCUSS wave output (Tier-1 [REF], lean density). Greenfield feature; SSOT bootstrapped alongside.
> Provenance: `/nw-discuss` 2026-06-22. Research-grounded against pi docs (earendil-works/pi, @mariozechner/pi-coding-agent).

## Wave: DISCUSS / [REF] Pre-requisites

- **pi installed** — `@mariozechner/pi-coding-agent` available on PATH as `pi`. pi runs in interactive, print/JSON, RPC, and SDK modes; this feature targets the bare **interactive** mode (`$ pi`, no options).
- **SPIKE-0 passed** — a timeboxed `/nw-spike` MUST confirm pi's `tool_call` event can block a production-code `write`/`edit` and that the extension can reach the Python DES adapter via subprocess. This de-risks the single central assumption before DESIGN. (User decision 2026-06-22: "SPIKE first".)
- **Existing DES surfaces present** — the shared Python adapter `des.adapters.drivers.hooks.claude_code_hook_adapter` (JSON-stdin → decision-stdout), the JSONL audit-log writer, and git commit `Step-Id:` trailers already exist and are reused unchanged.
- **Installer precedent** — Codex (`codex_des_plugin.py`) and OpenCode (`opencode_des_plugin.py`) plugins already wire the shared adapter into non-Claude harnesses. pi follows the same plugin pattern.

## Wave: DISCUSS / [REF] Persona ID

**Devon — the polyglot agent user.** A developer who runs more than one coding-agent harness and wants identical, verifiable TDD discipline across all of them. Prefers pi for its minimalism but refuses to trade away the test-first provenance guarantees nWave gives them in Claude Code. (Full profile: `docs/product/personas/pi-crafter-user.yaml`.)

## Wave: DISCUSS / [REF] JTBD one-liner

When I implement something with pi (a minimal, subagent-less harness), I want the crafter forced into canonical TDD — one test, minimal implementation, green, refactor, repeat — so I can trust the code is genuinely test-first without policing every step myself.

(Job record + dimensions + four forces: `docs/product/jobs.yaml#pi-tdd-enforced-crafter`.)

## Wave: DISCUSS / [REF] Locked decisions

| ID | Decision | Verdict | Rationale / source |
|----|----------|---------|--------------------|
| D1 | Crafter is exposed as a **pi skill** (`/skill:software-crafter`) contributed via the nWave pi extension's `resources_discover` event | LOCKED | Idiomatic pi (skills = capability packages, progressive disclosure); maps 1:1 to nWave's existing skill assets. Research-resolved (user deferred to "best practice in pi.dev"). |
| D2 | Enforcement = **full RED→GREEN→REFACTOR gating**, not a single gate | LOCKED | User decision 2026-06-22. Honors DoD "if the crafter skips a step it shouldn't be allowed". |
| D3 | Verification surface = **reuse existing DES surfaces** (JSONL audit log + git `Step-Id` trailers) | LOCKED | User decision 2026-06-22. No new artifact formats; consistency across harnesses. |
| D4 | pi hook unknown handled by **SPIKE first** (pre-WS probe) | LOCKED | User decision 2026-06-22. `tool_call` interception + adapter reachability is the one make-or-break assumption. |
| D5 | pi extension is a **thin TS translator** to the Claude Code JSON hook protocol; **zero fork** of the Python adapter | LOCKED | Mirrors the proven OpenCode shim. Keeps one canonical enforcement engine. |
| D6 | `SubagentStop` (step-completion) enforcement is **re-grounded on commit boundaries** (`Step-Id` trailer) and/or `agent_end`/`turn_end`, since pi has no subagents | PROVISIONAL → DESIGN | pi emits no `SubagentStop`. The mapping PreToolUse→`tool_call`, PostToolUse→`tool_result` is firm; the step-completion analog is a DESIGN decision. |
| D7 | Scope is **DELIVER/crafter only** — no other waves, no other agents, no roadmap orchestration in pi | LOCKED | "Start really thin." Everything else is out-of-scope (below). |

## Wave: DISCUSS / [REF] Out of scope

- Any nWave wave other than DELIVER, and any agent other than `software-crafter`, running under pi.
- Subagent emulation / multi-agent orchestration inside pi.
- Multi-step `roadmap.json` orchestration and `/nw-deliver` end-to-end flow under pi.
- Publishing the pi extension to the public npm registry (install is via the nWave installer for this slice).
- Modifying the Python DES adapter, the audit-log schema, or the `Step-Id` trailer convention.
- Cross-platform pi packaging concerns beyond what the nWave installer already handles.

## Wave: DISCUSS / [REF] WS strategy

**Strategy A — greenfield thin end-to-end slice**, preceded by a de-risking SPIKE (Mandate 5). The walking skeleton is the thinnest path that still proves the full DoD for a single kata: install → `$ pi` → `/skill:software-crafter` → implement a kata → DES blocks any step-skip → verify strict cycle via the existing execution log + commit history. "Thin" = narrow surface (one agent, one harness, reused adapter), **not** partial enforcement.

## Wave: DISCUSS / [REF] Driving ports

- **pi bare interactive CLI** — `$ pi` with no options (DoD step 1).
- **pi skill command** — `/skill:software-crafter` (DoD step 2; the user-invocable entry point).
- **pi `tool_call` lifecycle event** — DES RED/GREEN gate entry (block before execute).
- **pi `tool_result` lifecycle event** — DES failure-notification injection (PostToolUse analog).
- **pi commit boundary** — `Step-Id`-trailered git commits as the step-completion / provenance surface.
- **nWave installer pi target** — `nwave install` registers the pi plugins (extension + skill + DES wiring).

## Wave: DISCUSS / [REF] User stories

### Story 1 — Start pi bare and have the crafter available
**As** Devon, **I want** the nWave software-crafter to be invocable in a bare `pi` session with no flags, **so that** I can start working test-first immediately without harness ceremony.

`job_id: pi-tdd-enforced-crafter`

#### Elevator Pitch
Before: starting `pi` gives me a generic agent with no TDD discipline and no nWave crafter.
After: run `$ pi` then `/skill:software-crafter` → sees the crafter persona loaded and announcing it will work in strict RED→GREEN→REFACTOR.
Decision enabled: I decide to hand it a problem, trusting the TDD contract is now active.

#### Acceptance criteria
- Given nWave-for-pi is installed, when I run `$ pi` with no options, then pi starts normally and `/skill:software-crafter` appears in command completion.
- When I invoke `/skill:software-crafter`, then the crafter skill loads and states the 3-phase TDD contract (RED→GREEN→COMMIT/refactor) it will enforce.
- The DES extension is active in the same session (verifiable: the first tool call produces a DES audit-log entry — see Story 4).

### Story 2 — Be blocked from writing implementation before a failing test (RED gate)
**As** Devon, **I want** pi to refuse production-code edits when no failing test exists, **so that** the crafter cannot skip RED and write implementation-first.

`job_id: pi-tdd-enforced-crafter`

#### Elevator Pitch
Before: the agent can write implementation with no test behind it and I'd never know.
After: when the crafter attempts a production-code `write`/`edit` with no failing test present, pi blocks the tool call → sees a refusal message with the reason "no failing test — write the test first".
Decision enabled: I trust that every line of implementation was demanded by a failing test.

#### Acceptance criteria
- Given no failing test exists, when the crafter calls `write`/`edit` on a production-code path, then the `tool_call` is blocked with a DES reason and no file is modified.
- Given a failing test exists for the behavior, when the crafter writes the minimal implementation, then the `write`/`edit` is allowed.
- The block and the allow are both recorded in the existing DES audit log.

### Story 3 — Be held to GREEN and refactor-on-green (full cycle)
**As** Devon, **I want** pi to enforce that the next test only follows a green bar and that refactors never break tests, **so that** the loop stays one-tiny-test-at-a-time with no regressions.

`job_id: pi-tdd-enforced-crafter`

#### Elevator Pitch
Before: the agent can stack multiple tests, refactor on red, or leave broken tests behind.
After: when the crafter tries to start a new test before the suite is green, or commit with failing tests, pi blocks it → sees a reason naming the violated rule.
Decision enabled: I trust the kata was built in strict single-test increments with a clean bar at every step.

#### Acceptance criteria
- Given the suite is red, when the crafter attempts to author the next failing test, then the step is blocked with a "reach green first" reason.
- Given a refactor breaks a previously-green test, when the crafter attempts to commit, then the commit is blocked until green is restored (no-regression gate).
- Each enforced transition is recorded in the DES audit log with its phase (RED / GREEN / REFACTOR).

### Story 4 — Verify the cycle was followed via log + commit history
**As** Devon, **I want** to confirm strict RED→GREEN→REFACTOR from the execution log and git history after the kata, **so that** I have auditable provenance the discipline was real, not theater.

`job_id: pi-tdd-enforced-crafter`

#### Elevator Pitch
Before: I have only the final code and have to take the agent's word that it was test-first.
After: run `git log --format='%s %(trailers:key=Step-Id)'` and read the DES JSONL audit log → sees an ordered RED→GREEN→REFACTOR trail of `Step-Id`-trailered commits and blocked/allowed events.
Decision enabled: I decide whether to trust/merge the work based on verifiable TDD provenance.

#### Acceptance criteria
- After completing a kata, the DES audit log (existing JSONL surface) contains an ordered record of phase transitions and every block/allow decision for the session.
- Commits carry `Step-Id:` trailers in conventional-commit form, and their order reflects strict RED→GREEN→REFACTOR.
- No new bespoke log format is introduced; the surfaces are byte-compatible with what Claude Code produces (D3, D5).

## Wave: DISCUSS / [REF] Acceptance criteria (feature-level rollup)

- DoD step 1: `$ pi` (no options) starts and the crafter is reachable.
- DoD step 2: the crafter is invoked and accepts a problem statement.
- DoD step 3: the crafter solves it via canonical TDD; any attempt to skip a step (impl-before-test, new-test-before-green, regression-on-commit) is **blocked**, and the strict cycle is verifiable from the execution log + commit history.

## Wave: DISCUSS / [REF] Definition of Done (9-item)

1. `$ pi` with no options launches with the nWave pi extension + crafter skill active.
2. `/skill:software-crafter` loads the crafter and states the enforced TDD contract.
3. Production-code edits are blocked when no failing test exists (RED gate).
4. New-test-before-green and regression-on-commit are blocked (GREEN + refactor gates).
5. All block/allow decisions and phase transitions are written to the existing DES JSONL audit log.
6. Commits carry `Step-Id:` trailers; their order reflects strict RED→GREEN→REFACTOR.
7. The pi extension is a thin translator; the Python DES adapter is unmodified (zero fork).
8. nWave installer installs/uninstalls the pi target cleanly (manifest-tracked, like Codex/OpenCode).
9. A documented kata run demonstrates the full DoD end-to-end and is reproducible.

## Wave: DISCUSS / [REF] Outcome KPIs

| KPI | Target | Measurement |
|-----|--------|-------------|
| Step-skip block rate | 100% of attempted skips blocked on the kata scenario set | Count blocked vs. attempted skip events in the DES audit log |
| Provenance verifiability | 0 out-of-order phase transitions in a completed kata | Parse `Step-Id` commit order + audit-log phase sequence |
| Zero-config start | crafter invocable in ≤1 command after bare `$ pi` | Manual/e2e: `$ pi` → `/skill:software-crafter` |
| Adapter reuse | 0 forks / 0 edits to the Python DES adapter | Diff against `des.adapters.drivers.hooks.*` |
| Clean install/uninstall | 100% of installed pi artifacts removed on uninstall | Manifest reconciliation (`.nwave-des-manifest.json`) |

## Wave: DISCUSS / [REF] Scope Assessment

**PASS (right-sized after split).** Oversized signals checked: stories = 4 (≤10 ✓); bounded contexts/technologies = pi-TS-extension + Python-DES-adapter + installer-plugins + git (≥3 — flagged); integration points for WS = pi events + adapter subprocess + audit log + git (manageable); effort ≈ 1–1.5 weeks incl. SPIKE. The ≥3-technology signal is mitigated by reusing the proven OpenCode-shim pattern (no new enforcement engine). Decomposed into a SPIKE + 3 thin slices (see slice briefs). User-approved framing: "start really thin."

## Wave: DISCUSS / [REF] Slices (story-map backbone)

Backbone: **Install → Launch → Enforce (RED) → Enforce (GREEN/REFACTOR) → Verify.**

- **SPIKE-0** (pre-slice, timeboxed) — pi `tool_call` can block a production `write` and reach the Python adapter. → `docs/feature/pi-harness/slices/slice-00-spike-pi-toolcall.md`
- **Slice 01 (Walking Skeleton)** — install + bare-`pi` crafter skill + DES extension fires into the existing audit log. → `slice-01-walking-skeleton.md`
- **Slice 02** — RED gate (block impl-before-failing-test). → `slice-02-red-gate.md`
- **Slice 03** — GREEN + refactor/regression gates + `Step-Id` provenance, completing the DoD. → `slice-03-green-refactor-provenance.md`

Each slice ships observable value; the full DoD demo lands at the end of Slice 03. Full-cycle gating (D2) is delivered cumulatively across 02–03.

## Wave: DISCUSS / [REF] Wave decisions summary

- Primary need: verifiable, enforced canonical TDD for the software-crafter inside pi, a minimal subagent-less harness.
- Walking-skeleton scope: one agent (crafter), one harness (pi interactive), reused Python adapter + audit log + git trailers; full RED→GREEN→REFACTOR gating.
- Feature type: cross-cutting (installer plugin + TS extension + DES adapter reuse + git), primary value developer-facing tooling.
- Constraints: pi has no subagents (re-ground step-completion on commit boundaries — D6); enforcement must ride pi's `tool_call`/`tool_result` events; zero adapter fork (D5); reuse existing verification surfaces (D3).
- Upstream changes: none (greenfield; no DISCOVER assumptions to revise). SSOT bootstrapped.

## Wave: DISCUSS / [REF] Handoff

**To DESIGN (nw-solution-architect)** — full artifact set; key open design item is D6 (step-completion analog without subagents) and the pi-extension↔adapter protocol translation. **To DEVOPS (nw-platform-architect)** — `Outcome KPIs` only, to drive instrumentation of block/allow + phase telemetry on the existing audit surface. **Gate:** SPIKE-0 must pass before DESIGN commits to the `tool_call`-based enforcement path.
