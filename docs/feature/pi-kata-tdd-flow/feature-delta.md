# Feature: pi-kata-tdd-flow — self-driven nWave TDD cycle for a kata in pi

> DISCUSS wave output (Tier-1 [REF], lean). Builds on `pi-harness`
> (`docs/feature/pi-harness/feature-delta.md`). Closes the original DoD: invoke the
> crafter in pi, it solves a kata by strict canonical TDD, verified by execution log
> + commit history. Provenance: `/nw-discuss` 2026-06-24.

## Wave: DISCUSS / [REF] Pre-requisites

- **pi-harness shipped** — the pi DES extension relays write→`pre-write`, `git commit`→`subagent-stop` (step-completion gate), test-run→`post-tool-use`, `session_start`→health; the installer plugin places the extension + crafter skill. This feature adds the *driving* layer on top of that *verification* layer.
- **DES engine REUSED UNCHANGED** — the commit-boundary `subagent-stop` validation (`SubagentStopService` over `execution_log_path/project_id/step_id/cwd` + `GitCommitVerifier`), `des-init-log`, `des-log-phase`, audit log, `Step-Id`/`Task-Id` trailers already exist and are reused. No engine change (PD-strictness below).
- **Live pi model backend** — running an actual kata needs a model turn; the gate/recording wiring is asserted model-free, the full kata demo is gated on a backend (DoD item 9).

## Wave: DISCUSS / [REF] Persona ID

**Devon — the polyglot agent user** (`docs/product/personas/pi-crafter-user.yaml`, reused). Wants to hand pi a kata and get strict, auditable test-first discipline without manual DES setup.

## Wave: DISCUSS / [REF] JTBD one-liner

When I hand the crafter a kata in pi, I want it to drive itself through strict canonical TDD — one tiny test, minimal impl, green, refactor, commit, repeat — and record every phase, so I can verify the discipline from the execution log and commit history without orchestrating it myself.

Traces to `docs/product/jobs.yaml#pi-tdd-enforced-crafter` (reused; this feature delivers its "functional" dimension end-to-end).

## Wave: DISCUSS / [REF] Locked decisions

| ID | Decision | Verdict | Source |
|----|----------|---------|--------|
| K1 | **Strictness = commit-boundary verified** — the crafter self-drives RED→GREEN→COMMIT and records phases; the existing commit gate BLOCKS an incomplete/unverified step. Within-cycle ordering (test-before-impl) is crafter-skill discipline, **not** a keystroke-level hard block. | LOCKED | User 2026-06-24 |
| K2 | **No shared DES engine change** — the test-first write-gate (hard within-cycle block) is explicitly OUT; reuse the engine's existing decisions exactly as Claude Code/Codex/OpenCode do. | LOCKED | User 2026-06-24 (reverted test-first-write-gate) |
| K3 | **Driving/bootstrap mechanism deferred to DESIGN** — whether a pi-registered command, skill-only, or other; DISCUSS captures the requirement, DESIGN chooses. | LOCKED | User 2026-06-24 |
| K4 | **Scope = the DELIVER TDD cycle for a kata**, not the full 6-wave flow. A kata is an implementation exercise; the "nWave flow" here is strict Outside-In TDD with DES phase recording + commit verification. | LOCKED | Interpretation, 2026-06-24 |

## Wave: DISCUSS / [REF] Out of scope

- **Hard within-cycle write-block** (block production write when no failing test) — the reverted test-first-write-gate; needs a shared-engine change (K2).
- The full DISCOVER→…→DISTILL wave flow for the kata; multi-step `roadmap.json` + an architect creating it (the crafter self-decomposes tiny steps).
- Automating the live-model kata in CI (`@requires_external`); other agents/harnesses.
- Any modification to `src/des/**`.

## Wave: DISCUSS / [REF] WS strategy

**Extend the existing walking skeleton** (Mandate 5). The pi-harness `@walking_skeleton` (real `pi -e`, enforcement-active health line) stands; this feature adds the driving layer on top. No new walking skeleton — the thinnest e2e here is Slice 01 (self-bootstrap a DES-tracked session on crafter invocation).

## Wave: DISCUSS / [REF] Driving ports

- **crafter invocation in pi** (`/skill:software-crafter` and/or a registered kata command — exact surface is K3/DESIGN) — the entry that bootstraps + drives the cycle.
- **pi `tool_call` (write/edit, bash)** — write relays to `pre-write`; `git commit` relays to `subagent-stop` (verification gate, shipped).
- **pi `tool_result` (bash test-run)** — relays to `post-tool-use` (suite-state recording, shipped).
- **pi agent bash → `des-init-log` / `des-log-phase`** — the self-bootstrap + phase-recording surface (reachability is G4).

## Wave: DISCUSS / [REF] User stories

### Story 1 — Self-bootstrap a DES-tracked kata session
**As** Devon, **I want** invoking the crafter with a kata to set up its own DES execution log + first step automatically, **so that** the cycle is recorded and verifiable without me running any setup.

`job_id: pi-tdd-enforced-crafter`

#### Elevator Pitch
Before: there's no `/nw-deliver` in pi, so a kata has no DES session — nothing records phases and the commit gate has no step to check.
After: invoke the crafter with a kata → sees it initialize `docs/feature/<kata>/deliver/execution-log.json` and announce `step 01-01` — a DES-tracked session, zero manual setup.
Decision enabled: I trust the upcoming work will be recorded and gate-verified.

#### Acceptance criteria
- Given an activated pi project, when I invoke the crafter with a kata problem, then a DES execution log is initialized (via `des-init-log`) and a first `step-id` + project-id are established (session marker written).
- The `des-*` CLIs are reachable from pi's bash in an installed setup (G4).
- No manual `des-init-log`/orchestrator step is required.

### Story 2 — Self-driven per-test cycle with phase recording
**As** Devon, **I want** the crafter to run one tiny test at a time and record RED→GREEN→COMMIT for each, **so that** every increment leaves an auditable phase trail.

`job_id: pi-tdd-enforced-crafter`

#### Elevator Pitch
Before: nothing makes the single pi agent record DES phases — that was the orchestrator's job in Claude Code, and pi has no orchestrator.
After: the crafter writes one failing test → records `RED`; minimal impl → green → records `GREEN`; commits with `Step-Id` → records `COMMIT` → sees the ordered phases in `execution-log.json`.
Decision enabled: I can read the log and confirm each increment was a real test-first step.

#### Acceptance criteria
- Given a bootstrapped kata session, when the crafter completes a tiny increment, then RED, GREEN and COMMIT are recorded for that step via `des-log-phase`, in order.
- Each step's commit carries `Step-Id` + `Task-Id` trailers.
- The crafter self-decomposes the kata into one-test-per-step increments (no external roadmap.json).

### Story 3 — Solve a kata end-to-end, strictly verified
**As** Devon, **I want** to hand the crafter a real kata and afterwards confirm strict RED→GREEN→COMMIT from the log + git history, **so that** I have auditable proof the discipline held.

`job_id: pi-tdd-enforced-crafter`

#### Elevator Pitch
Before: I can't get an end-to-end, gate-verified TDD kata out of pi.
After: ask the crafter to "implement FizzBuzz via strict TDD" → afterwards `git log --format='%s %(trailers:key=Step-Id)'` + the DES audit log show an ordered RED→GREEN→COMMIT trail, and an attempt to commit an incomplete step was blocked.
Decision enabled: I decide to trust/merge the kata on verifiable provenance — closing the original pi-harness DoD.

#### Acceptance criteria
- After a kata, the execution log + `Step-Id`-trailered commits show strict per-step RED→GREEN→COMMIT order.
- Committing a step whose cycle is incomplete/unverified is blocked at the commit boundary (reuses the shipped `subagent-stop` gate).
- Verification uses existing DES surfaces only (no new log format).

## Wave: DISCUSS / [REF] Acceptance criteria (feature-level rollup)

Closes the original pi-harness DoD step 3: the crafter solves a kata by canonical TDD (single test → minimal impl → green → refactor → next tiny test), self-recording phases, with step-skips blocked at commit and the strict cycle verifiable from execution log + commit history.

## Wave: DISCUSS / [REF] Definition of Done (9-item)

1. Invoking the crafter with a kata self-initializes a DES execution log + first step (no manual setup).
2. The crafter drives one-tiny-test-at-a-time RED→GREEN→COMMIT, self-decomposing steps.
3. Each phase is recorded via `des-log-phase` from within pi (CLIs reachable).
4. Each step commits with `Step-Id` + `Task-Id` trailers.
5. Committing an incomplete/unverified step is blocked (reuse the shipped commit gate).
6. Execution log + git history show the strict ordered cycle for the kata.
7. Zero shared DES engine change (K2); strictness = commit-boundary verification (K1).
8. The driving/bootstrap mechanism is installed by the pi plugin (extends the pi-harness install).
9. A documented real kata (e.g. FizzBuzz) run in pi reproduces the full flow end-to-end.

## Wave: DISCUSS / [REF] Outcome KPIs

| KPI | Target | Measurement |
|-----|--------|-------------|
| Cycle completeness | 100% of kata steps show recorded RED→GREEN→COMMIT | Parse execution-log phases per step |
| Step-skip block rate | 100% of incomplete-step commits blocked | Count blocked commits in audit log |
| Zero-setup bootstrap | crafter inits the DES session in ≤1 invocation, 0 manual commands | Manual/e2e observation |
| Provenance order | 0 out-of-order phase transitions in a completed kata | `Step-Id` commit order + audit phase sequence |

## Wave: DISCUSS / [REF] Scope Assessment

**PASS (right-sized).** Stories = 3; bounded contexts/tech = pi extension/command (TS) + crafter skill (md) + DES CLIs (reuse) — the only genuinely new surface is the driving/bootstrap layer (DESIGN picks the mechanism). Effort ≈ a few days. No engine change (K2). Decomposed into 3 thin slices.

## Wave: DISCUSS / [REF] Slices (story-map backbone)

Backbone: **Bootstrap → Drive+record one step → Full kata verified.**

- **Slice 01** — self-bootstrap a DES-tracked session on crafter invocation (Story 1; G1+G4). → `slices/slice-01-bootstrap.md`
- **Slice 02** — self-driven single TDD step with RED→GREEN→COMMIT recording (Story 2; G2). → `slices/slice-02-self-driven-cycle.md`
- **Slice 03** — full multi-step kata, strictly verified by log + commits (Story 3; G3 + DoD). → `slices/slice-03-full-kata.md`

Each slice ships observable value; the original DoD lands at the end of Slice 03.

## Wave: DISCUSS / [REF] Wave decisions summary

- Primary need: a driving/bootstrap layer so a single pi agent self-runs the nWave DELIVER TDD cycle for a kata and records phases; the shipped commit gate verifies.
- Strictness: commit-boundary verified, no engine change (K1/K2).
- Feature type: cross-cutting (pi command/skill + crafter-skill content + DES CLI reuse), developer-facing tooling.
- Constraints: pi has no subagents/orchestrator/slash-commands; reuse DES engine + commit gate unchanged; CLIs must be reachable from pi bash.
- Open for DESIGN (K3): the exact bootstrap/driving mechanism (registered pi command vs skill-only vs other); how the crafter self-decomposes steps; how `des-*` reachability is guaranteed post-install.
- Upstream changes: none; SSOT job/persona/journey reused.

## Wave: DISCUSS / [REF] Handoff

**To DESIGN (nw-solution-architect)** — choose the driving/bootstrap mechanism (K3), the per-test step model, and `des-*` reachability; reuse the pi-harness extension + commit gate. **Gate:** no `src/des/**` change (K2). DEVOPS: KPIs only.

## Wave: DESIGN / [REF] Driving mechanism (K3 → KD1–KD4)

Full ADR: `docs/product/architecture/adr-pkt-001-kata-driving-and-commit-context.md`. Decisions: `design/wave-decisions.md`. Brief: `docs/product/architecture/brief.md` `### Feature: pi-kata-tdd-flow`.

- **KD1 — Bootstrap/driving = Hybrid.** A pi `registerCommand` (kata command) deterministically bootstraps (`des-init-log` + kata manifest + session marker), then hands to the reused crafter skill which drives the cycle + records phases. Rationale: a single agent can't be trusted to run multi-step bootstrap from prose; the command makes it deterministic, the skill owns the open-ended loop.
- **KD2 — Step model = convention + manifest, no roadmap.json.** `project-id` = kata id; `step-id` = `NN-NN` (`01-01`, `01-02`…) incremented per tiny test. The `kata-manifest.json` (under `docs/feature/{kata}/deliver/`) is the single source of `(project-id, current step-id, cwd)`.
- **KD3 — CLI reachability = install-time-resolved python + PYTHONPATH** (`python -m des.cli.init_log/log_phase` via `install_paths` resolvers) — mirrors the proven adapter-spawn path; not console-script-on-PATH, not the dev `PYTHONPATH=src .venv` form.
- **KD4 — Commit-boundary context = synthesized transcript via the Claude Code protocol** (DES markers + `cwd`). The direct protocol returns `effective_cwd=""` and the service skips commit verification (`if context.cwd`); enabling it there is an `src/des/**` change (K2). The transcript route reuses the engine's marker parser + cwd handling verbatim — zero engine change. KEY: the shipped pi commit gate currently always-allows (supplies neither protocol's context); this feature is what activates it.

## Wave: DESIGN / [REF] Components

| Component | Path | Change |
|-----------|------|--------|
| kata bootstrap command + commit-context assembler | `nWave/templates/pi-des-extension.ts.template` | EXTEND (pure relay preserved) |
| crafter pi-runnable cycle+recording section | crafter skill asset | EXTEND (ADD) |
| plugin render of resolved python/PYTHONPATH + command registration | `scripts/install/plugins/pi_des_plugin.py` | EXTEND |
| kata manifest | `docs/feature/{kata}/deliver/kata-manifest.json` | CREATE NEW (roadmap-free context carrier) |
| DES CLIs / gate / verifier / marker parser / audit / resolvers | `src/des/**`, `scripts/shared/install_paths.py` | REUSE UNCHANGED (K2) |

## Wave: DESIGN / [REF] SPIKE recommendation + K2 flag

SPIKE-PKT-001 is a **HARD GATE** before DISTILL entry (post-review hardening, Atlas 2026-06-24): model-free, cheap, SPIKE-0 Half-1 pattern. Probe: *given a synthesized one-line transcript with the four DES markers + a `cwd` on a real temp git repo, does the unchanged `subagent-stop` adapter allow/block (COMMIT_VERIFIED / COMMIT_NOT_VERIFIED) for complete vs incomplete logs — with `git diff --stat src/des/` empty?* A pass must produce a handoff artifact (round-trip output + git trace + audit excerpt). On fail, escalate the engine `cwd`-in-direct-protocol gap to the user as a K2 upstream issue — do NOT design the change. K2 is at risk only at KD4; the chosen route keeps the engine untouched.

## Wave: DESIGN / [REF] Post-review conditions (3 HIGH, resolved → DISTILL/DELIVER)

Atlas conditional approval (0 critical, 3 high — specification/robustness, not architecture). Resolved in ADR-PKT-001 "Post-review hardening":
- **H1** SPIKE-PKT-001 is a hard gate before DISTILL (above), with a required pass artifact.
- **H2** Crafter decomposition is a behavioral contract: structured kata intake; an ordered step-decomposition plan recorded in the manifest before the first RED; each step's RED exercises one plan increment. DISTILL authors the AC.
- **H3** Manifest writes are atomic (temp-then-move) + re-read-asserted after each increment; stale/partial manifest surfaces as a blocked commit, never a silent allow. DELIVER adds a reverted-manifest observation test.

## Wave: DESIGN / [REF] Handoff (DESIGN → DISTILL)

C4 L1 (inherited) + L2 + cycle sequence in `brief.md`; ADR-PKT-001 is the gate spec. **No external integrations → no contract tests.** Open for DISTILL/DELIVER: SPIKE on KD4; confirm pi `registerCommand` shape (source inspection); `kata-manifest.json` schema; standalone `des-log-phase` schema-loader path; `@requires_external` live-model full kata (DoD item 9).

## Wave: DISTILL / [REF] Scenario list with tags

Test SSOT = the three `.feature` files under `tests/des/acceptance/pi_kata_tdd_flow/`.
Density = lean (Tier-1). All scenarios layer 3 (`@adapter-integration`), example-only.

| Scenario | Slice | Tags |
|----------|-------|------|
| Bootstrapping a kata establishes a recorded, gate-ready session | 01 | @US-1 @real-io @contract-shape:bounded-change |
| Bootstrapping outside an activated project leaves the project untouched | 01 | @US-1 @real-io @error @contract-shape:unbounded-preservation |
| Re-bootstrapping an existing session preserves the recorded history | 01 | @US-1 @real-io @contract-shape:unbounded-preservation |
| Recording a completed increment leaves an ordered phase trail | 02 | @US-2 @real-io @contract-shape:bounded-change |
| A completed increment with a trailered commit is accepted at the boundary | 02 | @US-2 @real-io @contract-shape:unbounded-preservation |
| An incomplete increment is blocked at the commit boundary with a reason | 02 | @US-2 @real-io @error @contract-shape:unbounded-preservation |
| A malformed commit-context transcript is treated as no DES context | 02 | @US-2 @real-io @error @contract-shape:unbounded-preservation |
| A multi-step kata records each step's cycle in plan order | 03 | @US-3 @real-io @contract-shape:bounded-change |
| Skipping a step in a multi-step kata is blocked at the commit boundary | 03 | @US-3 @real-io @error @contract-shape:unbounded-preservation |
| A reverted step-id in the manifest surfaces as a blocked commit | 03 | @US-3 @real-io @error @contract-shape:unbounded-preservation |
| A live pi model solves a real kata end-to-end with a verified trail | 03 | @US-3 @requires_external @contract-shape:bounded-change |

Error/edge ratio: 6/11 ≈ 55% (≥40% target met). Story coverage: US-1, US-2, US-3 all
mapped. Every scenario carries a `@contract-shape:` tag (2026-05-15 mandate).

## Wave: DISTILL / [REF] WS strategy

**Inherits the pi-harness walking skeleton** (Mandate 5; DISCUSS WS decision). No new
`@walking_skeleton` scenario — the pi-harness `@walking_skeleton` (real `pi -e`,
enforcement-active health line) stands as the e2e wiring proof. This feature's thinnest
observable value is Slice 01 (`@US-1 @real-io`), which builds the *driving* layer on top
of the inherited skeleton. The single live-model end-to-end run (Slice 03) is
`@requires_external` and skipped by default; its deterministic analog is asserted
model-free.

## Wave: DISTILL / [REF] Adapter coverage (Mandate 6)

| Adapter | @real-io scenario | Covered by |
|---------|-------------------|------------|
| Reused `des-init-log` (execution-log writer) | YES | Slice 01 bootstrap (real FS init under tmp deliver dir) |
| NEW kata-manifest writer (`pi_kata.bootstrap`) | YES | Slice 01 bootstrap + re-bootstrap idempotency (real FS, atomic write) |
| Reused `des-log-phase` (phase recorder) | YES | Slice 02/03 record-cycle (real FS append, real UTC timestamp) |
| Reused `subagent-stop` adapter (commit gate) | YES | Slice 02/03 validate-at-commit-boundary (real subprocess round-trip) |
| NEW transcript-context assembler (`pi_kata.transcript_context`) | YES | Slice 02/03 boundary scenarios (real synthesized transcript + real adapter) |
| Real git repo (`GitCommitVerifier` input) | YES | Slice 02/03 commit-with-trailers (real `git init`/`commit` under tmp_path) |

Zero "NO — MISSING" rows. Costly external (pi LLM backend) = `@requires_external` skip
per the infra policy "Driven external" row.

## Wave: DISTILL / [REF] Driving Adapter coverage

| Driving entry (DESIGN) | Scenario exercising it via its protocol |
|------------------------|------------------------------------------|
| Kata bootstrap (KD1 command → `pi_kata.bootstrap`) | Slice 01 — real FS + reused `des-init-log` subprocess |
| `git commit` → `subagent-stop` (KD4 synthesized transcript) | Slice 02/03 — real adapter subprocess round-trip with the four DES markers + cwd |
| Per-test phase recording → `des-log-phase` | Slice 02/03 — real CLI subprocess |
| Live crafter invocation in pi (model turn) | Slice 03 `@requires_external` (skipped; deterministic analog asserted) |

The shipped pi extension template + `pi_des_plugin` are EXTENDED (not scaffolded) — the
TS `registerCommand` + commit-context branch render behavior is asserted indirectly via
the Python helpers' contract. SPIKE constraint 1 (stdout decision=block at exit 0) is
asserted by the Slice 02/03 reject scenarios reading the engine's JSON decision.

## Wave: DISTILL / [REF] Scaffolds (Mandate 7)

NEW Python surface (RED-ready stubs, `__SCAFFOLD__ = True`, AssertionError bodies):

- `scripts/install/pi_kata/bootstrap.py` — `bootstrap_kata_session`,
  `read_kata_manifest`, `advance_step_id` (KD1/KD2 deterministic bootstrap +
  atomic manifest writer; reuses `des-init-log` UNCHANGED).
- `scripts/install/pi_kata/transcript_context.py` — `build_transcript_content`,
  `write_synthesized_transcript`, `build_subagent_stop_payload` (KD4 synthesized-
  transcript assembler emitting the four exact DES markers; feeds the UNCHANGED
  `subagent-stop` engine).

The pi extension template (`nWave/templates/pi-des-extension.ts.template`) and
`scripts/install/plugins/pi_des_plugin.py` are EXTENDED at DELIVER (committed
skeleton), NOT scaffolded. RED-classification: all 10 active scenarios fail with
the scaffold AssertionError = MISSING_FUNCTIONALITY (see
`distill/red-classification.md`).

## Wave: DISTILL / [REF] Test placement

`tests/des/acceptance/pi_kata_tdd_flow/` (new dir), mirroring
`tests/des/acceptance/pi_harness/` conventions: per-slice `.feature` + `steps/`
package, `conftest.py` marker registration, `domain_types.py` (Mandate-12),
`kata_support.py` composition root, model-free adapter round-trip + real tmp git repo.
Auto-marked `acceptance` by `tests/conftest.py` path map.

## Wave: DISTILL / [REF] Pre-requisites

- DESIGN driving ports: ADR-PKT-001 KD1 (bootstrap command), KD2 (manifest + `NN-NN`),
  KD3 (install-resolved `python -m des.cli.*`), KD4 (synthesized transcript).
- SPIKE-PKT-001 PASS (hard gate cleared) — the four binding constraints honored in
  step bodies.
- Reused UNCHANGED (K2): `des.cli.init_log`, `des.cli.log_phase`,
  `subagent_stop_handler`, `DesMarkerParser`, `GitCommitVerifier`.
- DEVOPS absent → default env matrix (WARN). Infra policy present (inherit) — the three
  pi ports cover this surface; no new row.
- State-delta port present at `tests/common/state_delta.py` (inherited).

## Wave: DISTILL / [REF] Self-completeness audit

15-item canonical checklist (no domain-extension opt-in). **Verdict: COMPLETE (14/15).**
One documented `AT_GAP_IN_DELIVERY_SCOPE`: C7a degraded-resource / partial-write FS
failure deferred to DELIVER's H3 observation test (the reverted-manifest interruption
analog is covered here). Zero `SPECIFICATION_AMBIGUITY` blockers — C2/C5/C6/C7 upstream
artifacts all present (ADR-PKT-001 + slices + SPIKE). N/A-with-rationale: C1b (no numeric
boundary), C5a/C5b (no mode flags), C7c (single agent, no concurrency claim). Full detail
+ Tier decision + Mandate-12 ratio (≈1.2× natural ceiling, config-shaped, compliant) in
`distill/wave-decisions.md`.

## Wave: DELIVER / [REF] Implementation summary

The driving/bootstrap layer ships: `scripts/install/pi_kata/bootstrap.py` (deterministic kata-session bootstrap — reused `des-init-log`, atomic `kata-manifest.json` carrying project-id/step-id/cwd, activation-gated, idempotent), `scripts/install/pi_kata/transcript_context.py` (the synthesized-transcript assembler that activates the previously-inert commit gate by feeding the UNCHANGED `subagent-stop` engine the four exact DES markers + cwd), and the EXTENDED pi extension (`pi.registerCommand` kata bootstrap + commit-context branch on the bash `git commit` tool_call, pure relay) + plugin (render/register + crafter-skill cycle section). A single pi agent can now bootstrap a kata, drive per-test RED→GREEN→COMMIT recording, and have the commit gate block any incomplete step — all via the existing engine, **zero `src/des` change** (K2).

## Wave: DELIVER / [REF] Files modified

- **Production (new)**: `scripts/install/pi_kata/bootstrap.py`, `scripts/install/pi_kata/transcript_context.py`.
- **Production (extended)**: `nWave/templates/pi-des-extension.ts.template` (registerCommand + commit-context branch), `scripts/install/plugins/pi_des_plugin.py` (render/register + crafter-skill placement + manifest).
- **Tests**: `tests/des/acceptance/pi_kata_tdd_flow/` (3 `.feature` + steps); orchestrator fixes — `conftest.py` (colon-tag handling), slice-02 (`_no_des_context` allow-contract), slice-03 (skipped-step Given content).
- **REUSE UNCHANGED**: `src/des` (des-init-log, des-log-phase, subagent-stop, GitCommitVerifier) — K2 verified empty diff.

## Wave: DELIVER / [REF] Scenarios green

`tests/des/acceptance/pi_kata_tdd_flow/` — **10 passed / 0 failed / 1 skipped** (2026-06-24). The skip is `@requires_external` (live pi model, SPIKE CI caveat). pi-harness regression: **21 passed / 1 skipped** (walking skeleton green).

## Wave: DELIVER / [REF] DoD check

1. Invoking the crafter self-initializes a DES log + first step — ✅ (`bootstrap_kata_session` → execution-log + manifest + step 01-01).
2. Drives one-tiny-test-at-a-time RED→GREEN→COMMIT, self-decomposing — ✅ (crafter-skill section + advance_step_id; multi-step scenario green).
3. Phases recorded via `des-log-phase` from pi — ✅ (reused CLI, install-resolved python).
4. Commits carry `Step-Id`+`Task-Id` trailers — ✅.
5. Committing an incomplete/unverified step blocked — ✅ (commit-context → unchanged subagent-stop blocks; slice-03 skip scenario green).
6. Execution log + git history show the strict ordered cycle — ✅ (plan-order + commit-order scenarios green).
7. Zero shared DES engine change — ✅ (K2 verified).
8. Driving/bootstrap mechanism installed by the pi plugin — ✅ (registerCommand + render).
9. Documented real kata run reproduces the flow — ⏳ live-model kata is `@requires_external` (deferred per CI caveat); model-free wiring fully asserted.

## Wave: DELIVER / [REF] Demo Evidence — 2026-06-24

Story 1 (self-bootstrap), model-free against the real Python entry point:
```
bootstrap_kata_session(project_root=<activated repo>, kata_id="fizzbuzz")
  → {"status": "bootstrapped", "project_id": "fizzbuzz", "step_id": "01-01"}
  → execution-log.json present: True ; kata-manifest.json present: True
bootstrap in an unactivated repo → {"status": "refused"}  (no session, FS untouched)
```
Stories 2–3 gate behavior (block incomplete step at the commit boundary) is asserted model-free across the slice-02/03 acceptance scenarios; the live-model end-to-end kata is `@requires_external` (skipped, needs a backend).

## Wave: DELIVER / [REF] Quality gates

- DES integrity: ✅ "All 3 steps have complete DES traces" (RED→GREEN→COMMIT; 01-03 had a legitimate escalate→unblock→re-execute, all EXECUTED).
- Adversarial review (`@nw-software-crafter-reviewer`): ✅ APPROVED, 0 defects; testing-theater = none (real engine via subprocess); 3 orchestrator test fixes all judged legitimate (not bug-masking); thin-translator + zero-fork verified.
- Refactor (L1-L6): assessed clean. Mutation: SKIPPED (`nightly-delta`).
- Commits: `5ac1494` (01-01), `96580407` (01-02), `1b4081d` (01-03) + test-infra fixes `2afa359`/`ba1c98e`/skipped-step.
