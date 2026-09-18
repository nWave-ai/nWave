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
After: run `$ pi` then `/skill:software-crafter` → sees the startup line `[nWave DES] enforcement active for pi` and the crafter announcing it will work in strict RED→GREEN→REFACTOR.
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
After: when the crafter tries to start a new test before the suite is green, or `git commit` while tests fail, pi blocks it → sees e.g. `Suite is red — reach green before the next test.` or `Regression: 1 previously-green test now fails — restore green before commit.`
Decision enabled: I trust the kata was built in strict single-test increments with a clean bar at every step.

#### Acceptance criteria
- Given the suite is red, when the crafter attempts to author the next failing test, then the step is blocked with a "reach green first" reason.
- Given a refactor breaks a previously-green test, when the crafter runs `git commit` (a `bash` tool call), then the commit is blocked until green is restored — where **"green" = the most recent test-run `bash` tool_result exited 0** (per ADR-pi-001; the no-regression gate fires at the commit `bash` tool_call, NOT at the non-blocking `turn_end`).
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

## Wave: DISCUSS / [REF] Worked examples (reference kata: FizzBuzz)

Concrete trace grounding Stories 2–4 (real paths, real commands, real reason/output strings). The crafter is asked: *"implement FizzBuzz via strict TDD."*

1. **RED allowed** — crafter writes `tests/test_fizzbuzz.py::test_returns_1_for_1` (a failing test). pi `write` `tool_call` → allowed (a failing test now exists). Audit: `HOOK_PRE_WRITE_ALLOWED`.
2. **Impl-before-test BLOCKED (Story 2)** — crafter instead tries to write `src/fizzbuzz.py` with no failing test present. pi `write` `tool_call` → **blocked**, file unchanged, crafter sees `No failing test for this behavior — write the test first.` Audit: `HOOK_PRE_WRITE_BLOCKED`.
3. **GREEN** — with the failing test present, crafter writes minimal `src/fizzbuzz.py` (`return "1"`). `write` allowed; the test-run `bash` tool_result exits 0 → phase recorded GREEN.
4. **New-test-while-red BLOCKED (Story 3)** — suite is red; crafter tries to author `test_returns_2_for_2`. Blocked: `Suite is red — reach green before the next test.`
5. **Regression-on-commit BLOCKED (Story 3)** — a refactor breaks `test_returns_1_for_1`; crafter runs `git commit -m "refactor"` (a `bash` tool call). Blocked until green: `Regression: 1 previously-green test now fails — restore green before commit.`
6. **Provenance (Story 4)** — after the kata, `git log --format='%s %(trailers:key=Step-Id)'` shows `feat: fizz for 3  Step-Id: fizzbuzz-03` ordered RED→GREEN→REFACTOR, and `.nwave/des/logs/audit-*.log` holds the matching ordered phase + block/allow entries.

## Wave: DISCUSS / [REF] Wave decisions summary

- Primary need: verifiable, enforced canonical TDD for the software-crafter inside pi, a minimal subagent-less harness.
- Walking-skeleton scope: one agent (crafter), one harness (pi interactive), reused Python adapter + audit log + git trailers; full RED→GREEN→REFACTOR gating.
- Feature type: cross-cutting (installer plugin + TS extension + DES adapter reuse + git), primary value developer-facing tooling.
- Constraints: pi has no subagents (re-ground step-completion on commit boundaries — D6); enforcement must ride pi's `tool_call`/`tool_result` events; zero adapter fork (D5); reuse existing verification surfaces (D3).
- Upstream changes: none (greenfield; no DISCOVER assumptions to revise). SSOT bootstrapped.

## Wave: DISCUSS / [REF] Handoff

**To DESIGN (nw-solution-architect)** — full artifact set; key open design item is D6 (step-completion analog without subagents) and the pi-extension↔adapter protocol translation. **To DEVOPS (nw-platform-architect)** — `Outcome KPIs` only, to drive instrumentation of block/allow + phase telemetry on the existing audit surface. **Gate:** SPIKE-0 must pass before DESIGN commits to the `tool_call`-based enforcement path.

## Wave: DESIGN / [REF] Step-completion model (D6 → D8)

D6 resolved as **Hybrid** (ADR-PI-001). The pivot: `SubagentStopService.validate()` is a pure validation over `(execution_log_path, project_id, step_id, cwd)` — the subagent boundary is only the trigger cadence, not a dependency. Mapping:
- RED ordering → pi `tool_call` (write/edit) → existing `pre-write` guard (in skeleton).
- Suite state (red/green/regression) → bash test-run `tool_result` → recorded via existing DES phase CLI (no new format, D3).
- Step completion → `git commit` `tool_call` boundary → unchanged `subagent-stop` action; failed validation returns `{block:true,reason}` so pi aborts the commit.
- `turn_end`/`agent_end` → read-only reconciliation, never blocks (block honoring unverified, R2).

Rejected: Option A commit-only (no within-cycle ordering, fails D2); Option B turn_end-only (block-at-turn_end unproven). Full alternatives in ADR-PI-001.

## Wave: DESIGN / [REF] Components

| Component | Path | Change |
|-----------|------|--------|
| pi DES extension | `nWave/templates/pi-des-extension.ts.template` | EXTEND (skeleton → full gate set; stays pure translator) |
| pi installer plugin | `scripts/install/plugins/pi_des_plugin.py` | CREATE NEW (mirror `opencode_des_plugin.py`) |
| Plugin registration | `scripts/install/install_nwave.py` | EXTEND (register `pi-des`, deps `["des"]`, when pi detected) |
| Crafter skill | `nWave/skills` assets | REUSE (placed by DES plugin; contributed via `resources_discover`) |
| Python DES engine + verifiers + audit | `src/des/...` | REUSE UNCHANGED (zero fork, D5) |
| `install_paths` spawn resolvers | `scripts/shared/install_paths.py` | REUSE |

## Wave: DESIGN / [REF] Activation + audit-dir

Activation: `.nwave/local-config.json:{enabled_for_repo:true}` resolved by the existing Python `activation_gate` (dormant→exit 0/allow). Audit dir: extension MUST pin `DES_AUDIT_LOG_DIR` to project `.nwave/des/logs` on every spawn (`JsonlAuditLogWriter` defaults to process cwd). Both mandatory (SPIKE implications 2 & 3).

## Wave: DESIGN / [REF] Handoff (DESIGN → DISTILL)

C4 L1+L2 + ADR-PI-001/002/003 in `docs/product/architecture/`. **No external integrations → no contract tests** (D14). Open items for DISTILL/DELIVER: model-free acceptance for the commit-boundary block + red→green→regression sequence (R4); confirm pi `resources_discover` shape (R1) and extension-install location (R1, DEVOPS verify); confirm pi honors `{block:true}` on the `git commit` `tool_call`.

## Wave: DISTILL / [REF] Scenario list with tags

> Density = lean (Tier-1 only). The `.feature` files are the scenario SSOT. Built ON the inherited `@walking_skeleton` (untouched, GREEN). Test placement: `tests/des/acceptance/pi_harness/` (existing dir, DES acceptance precedent). 20 model-free scenarios + 1 `@requires_external` skip + 1 inherited skeleton.

| Scenario | Feature file | Tags | Status |
|----------|--------------|------|--------|
| Starting pi in an activated project confirms DES enforcement is live | walking-skeleton | `@walking_skeleton @driving_port` | GREEN (inherited, untouched) |
| A production write is translated to the RED gate and the engine's block is relayed verbatim | extension-translation-contract | `@US-2 @real-io @adapter-integration` | GREEN |
| An allowed write is relayed as allow | extension-translation-contract | `@US-2 @real-io @adapter-integration` | GREEN |
| A commit tool call is translated to the step-completion validation | extension-translation-contract | `@US-3 @adapter-integration` | RED |
| A test-run result is translated to the suite-state recording action | extension-translation-contract | `@US-3 @adapter-integration` | RED |
| A non-mutating read tool call is passed through untouched | extension-translation-contract | `@US-2 @adapter-integration` | GREEN |
| A translator failure never blocks a legitimate tool call | extension-translation-contract | `@US-2 @error @adapter-integration` | GREEN |
| The extension contains no allow or block decision of its own | extension-translation-contract | `@US-2 @adapter-integration` | GREEN |
| Installing into a present pi config dir places the extension and manifest | installer-plugin-lifecycle | `@US-1 @real-io @adapter-integration` | RED |
| Installing when pi is not present skips without failing | installer-plugin-lifecycle | `@US-1 @error @real-io @adapter-integration` | RED |
| Installing before the DES library is present is refused with guidance | installer-plugin-lifecycle | `@US-1 @error @real-io @adapter-integration` | RED |
| Verifying a completed install confirms the placed artifacts | installer-plugin-lifecycle | `@US-1 @real-io @adapter-integration` | RED |
| Verifying before installing reports the missing extension | installer-plugin-lifecycle | `@US-1 @error @real-io @adapter-integration` | RED |
| Reinstalling refreshes the extension without removing the operator's own pi files | installer-plugin-lifecycle | `@US-1 @real-io @adapter-integration` | RED |
| Uninstalling removes every placed artifact and leaves the operator's files | installer-plugin-lifecycle | `@US-1 @real-io @adapter-integration` | RED |
| Uninstalling when nothing was installed completes without error | installer-plugin-lifecycle | `@US-1 @error @real-io @adapter-integration` | RED |
| Writing implementation before a failing test is blocked at the write boundary | tdd-enforcement-gates | `@US-2 @real-io @adapter-integration` | RED |
| Writing the test first is allowed | tdd-enforcement-gates | `@US-2 @real-io @adapter-integration` | GREEN |
| Committing a step that did not complete its phases is blocked at the commit boundary | tdd-enforcement-gates | `@US-3 @adapter-integration` | RED |
| Committing a step that completed its phases with a trailered commit is allowed | tdd-enforcement-gates | `@US-3 @adapter-integration` | GREEN |
| A live pi model turn honors the block on a real production write | tdd-enforcement-gates | `@US-3 @requires_external` | SKIPPED |

Gate run: 8 PASSED · 12 FAILED (all `MISSING_FUNCTIONALITY`) · 1 SKIPPED. Detail: `distill/red-classification.md`.

## Wave: DISTILL / [REF] WS strategy

Walking skeleton INHERITED from SPIKE-0 (PROMOTED 2026-06-23), untouched and GREEN: `@walking_skeleton @driving_port` driving real pi 0.79.9 via subprocess `pi -e`, asserting the `[nWave DES] enforcement active for pi` health line. Per the retired-strategy model, this is the production-composition-root demo proof. DISTILL added the next layers (installer lifecycle, translation contract, gate wiring) ON the skeleton. No second walking skeleton authored.

## Wave: DISTILL / [REF] Adapter coverage table (Mandate 6)

| Driven adapter | `@real-io` scenario | Covered by |
|----------------|---------------------|------------|
| Rendered-template filesystem install (pi config dir) | YES | installer-plugin-lifecycle: install / reinstall / uninstall (real `tmp_path` pi dir, `PI_CONFIG_DIR` override) |
| Install manifest writer (`.nwave-des-manifest.json`) | YES | installer-plugin-lifecycle: "install … manifest"; uninstall removes it |
| Python DES adapter (`claude_code_hook_adapter`, REUSED UNCHANGED) | YES | extension-translation-contract + tdd-enforcement-gates: real `pre-write` / `subagent-stop` subprocess round-trips |
| pi LLM backend (external, non-deterministic) | `@requires_external` skip | tdd-enforcement-gates: "A live pi model turn honors the block" — model-free analog asserted at the adapter round-trip |

Zero `NO — MISSING` rows.

## Wave: DISTILL / [REF] Driving Adapter coverage

- **pi entry point (`pi -e` subprocess)** — covered by the inherited `@walking_skeleton @driving_port` scenario (real protocol: subprocess, exit status, stderr health line). Noted: this covers the pi driving adapter end-to-end.
- **pi installer pi target (`PiDESPlugin` lifecycle)** — driving port exercised via `validate_prerequisites/install/verify/uninstall` over a real `InstallContext` with real FS I/O.
- **pi `tool_call`/`tool_result` translation** — exercised model-free via the rendered-extension mapping contract + real DES adapter subprocess round-trip (SPIKE-0 Half-1 pattern; live-model path is `@requires_external`).

## Wave: DISTILL / [REF] Scaffolds (Mandate 7)

| Scaffold file | Marker | Methods |
|---------------|--------|---------|
| `scripts/install/plugins/pi_des_plugin.py` | `__SCAFFOLD__ = True` | `validate_prerequisites` / `install` / `verify` / `uninstall` each raise `AssertionError("…RED scaffold…")` |

`grep -r "__SCAFFOLD__" scripts/install/plugins/pi_des_plugin.py` → present. DELIVER removes the marker when the plugin is implemented (GREEN). The extension template (`pi-des-extension.ts.template`) is the committed skeleton — EXTENDED in DELIVER, not scaffolded (it already exists and passes the skeleton test).

## Wave: DISTILL / [REF] Test placement

`tests/des/acceptance/pi_harness/` (existing dir; the inherited skeleton lives here). Precedent: DES acceptance tests under `tests/des/acceptance/`. Three new `.feature` files + matching `steps/test_*.py`; markers registered in the existing `conftest.py`.

## Wave: DISTILL / [REF] Pre-requisites

- DESIGN driving ports (brief.md): pi `tool_call`/`tool_result`, `git commit` boundary, `session_start`, `/skill:software-crafter`, nWave installer pi target. ADR-pi-001 (D6 Hybrid) is the spec for the gate scenarios.
- DES engine REUSED UNCHANGED (`claude_code_hook_adapter` actions `pre-write` / `post-tool-use` / `subagent-stop` / `session-start`); zero fork (D5).
- Env matrix: no DEVOPS wave → default `clean | with-pre-commit | with-stale-config` (WARN). Tests are env-agnostic (tmp_path + `PI_CONFIG_DIR` override + `DES_AUDIT_LOG_DIR` pin).
- Infrastructure policy bootstrapped: `docs/architecture/atdd-infrastructure-policy.md`.
- Deferred: outcomes registry (`OUT-PI-1`, schema.json absent); `@requires_external` live-model e2e; R1 pi config-dir confirmation; C7b interruption AT (LOW). See `distill/wave-decisions.md`.

## Wave: DELIVER / [REF] Implementation summary

The pi harness now installs and enforces DES end-to-end. The nWave installer renders the pi DES extension into pi's config dir (manifest-tracked, clean uninstall); the extension is a thin TS translator that maps pi lifecycle events to the unchanged Python DES engine — write/edit `tool_call` → `pre-write` RED gate, bash `git commit` `tool_call` → `subagent-stop` step-completion gate, bash test-run `tool_result` → `post-tool-use` suite-state recording, `session_start` → engine-reachability health line. Zero adapter fork (D5): the engine renders every verdict; the extension owns exactly one block decision (a verbatim relay). Delivered via 3 TDD steps (RED→GREEN→COMMIT each, DES-verified).

## Wave: DELIVER / [REF] Files modified

- **Production**: `scripts/install/plugins/pi_des_plugin.py` (NEW — installer plugin, mirrors `opencode_des_plugin.py`); `scripts/install/install_nwave.py` (register `PiDESPlugin`, deps `["des"]`, pi-gated); `nWave/templates/pi-des-extension.ts.template` (EXTENDED skeleton → full gate set).
- **Tests**: `tests/des/acceptance/pi_harness/{installer-plugin-lifecycle,extension-translation-contract,tdd-enforcement-gates}.feature` + matching `steps/test_*.py` (+ A2 out-of-harness scenario).
- **DES audit**: `docs/feature/pi-harness/deliver/{roadmap.json,execution-log.json}`.
- **REUSE UNCHANGED**: `src/des/**` (engine, `SubagentStopService`, `GitCommitVerifier`, audit writer, activation gate) — zero fork verified.

## Wave: DELIVER / [REF] Scenarios green

`tests/des/acceptance/pi_harness/` — **21 passed / 0 failed / 1 skipped** (2026-06-24). The 1 skip is `@requires_external` (live pi model backend, SPIKE CI caveat). `@walking_skeleton` green (real `pi -e` subprocess).

## Wave: DELIVER / [REF] DoD check

1. `$ pi` launches with extension + crafter skill active — ✅ (walking skeleton + installer plugin).
2. `/skill:software-crafter` loads + states TDD contract — ✅ (skill placed by plugin; `resources_discover`, A3 confirmed).
3. Production-code edits blocked when no failing test — ✅ (write/edit→`pre-write` gate).
4. New-test-before-green / regression-on-commit blocked — ✅ (commit→`subagent-stop` gate; suite-state recording).
5. Block/allow + phases in DES JSONL audit log — ✅ (`DES_AUDIT_LOG_DIR` pinned).
6. Commits carry `Step-Id` trailers, ordered RED→GREEN→REFACTOR — ✅ (engine `GitCommitVerifier`; A2 catches out-of-harness).
7. Thin translator; Python adapter unmodified — ✅ (review-verified, `src/des/**` unchanged).
8. Installer installs/uninstalls cleanly, manifest-tracked — ✅ (8 lifecycle scenarios).
9. Documented kata run demonstrates DoD — ⏳ live-model kata is `@requires_external` (deferred per CI caveat); model-free wiring fully asserted.

## Wave: DELIVER / [REF] Demo Evidence — 2026-06-24

Story 1 Elevator Pitch (`$ pi` → enforcement active) executed against real pi 0.79.9:
```
$ pi --no-extensions -e <rendered-ext> --offline --no-session --no-tools -p "noop"
[nWave DES] enforcement active for pi      (exit 0)
```
Stories 2–4 gate demos require a live model turn (`@requires_external`, skipped per SPIKE CI caveat); their enforcement wiring is asserted model-free in the acceptance suite.

## Wave: DELIVER / [REF] Quality gates

- DES integrity: ✅ "All 3 steps have complete DES traces" (RED→GREEN→COMMIT, `Step-Id`+`Task-Id` trailers).
- Adversarial review (`@nw-software-crafter-reviewer`): ✅ APPROVED, 0 defects; testing-theater = none (real engine via subprocess); thin-translator invariant verified.
- Refactor (L1-L6): assessed clean (no high-value refactors).
- Mutation: SKIPPED (`nightly-delta` strategy — CI nightly).
- Commits: `827cd6c` (01-01), `209c4bd` (01-02), `0900abc` (01-03).
