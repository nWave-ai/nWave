# ADR-PKT-001: Self-driven kata TDD cycle in pi — driving mechanism, step model, CLI reachability, and commit-boundary context

## Status
Accepted (2026-06-24). Resolves the four headline DESIGN decisions for
`pi-kata-tdd-flow` (K3). Builds on ADR-PI-001/002/003 and reuses the shipped
pi-harness extension + installer plugin + DES commit gate UNCHANGED in
`src/des/**` (K2).

## Context
pi-harness shipped the *verification* layer: a thin TS extension translates pi
lifecycle events to the Claude Code JSON hook protocol and relays the unchanged
Python DES engine's verdict (write/edit → `pre-write` RED gate; bash `git commit`
→ `subagent-stop` step-completion gate; bash test-run `tool_result` →
`post-tool-use` suite recording; `session_start` → health line). pi has no
subagents, no orchestrator, and no slash commands.

pi-kata-tdd-flow adds the *driving* layer: a single pi agent must self-bootstrap
a DES-tracked session, self-decompose a kata into one-test-per-step increments,
drive RED→GREEN→COMMIT, and record each phase via `des-log-phase` — with no
orchestrator and no `roadmap.json`. The shipped commit gate then verifies.

Two engine facts discovered by reading the shipped code drive every decision
below and are the load-bearing constraints for K2:

1. **`des-init-log` / `des-log-phase` are standalone CLIs** over a `--project-dir`
   (`src/des/cli/init_log.py`, `log_phase.py`). They have no orchestrator
   dependency — any process that can run python with the DES lib on `PYTHONPATH`
   can call them. `des-init-log` refuses only under `workflow.mode: atdd_pure`;
   an absent `.nwave/config.yaml` is treated as `classic` (the kata default).

2. **The shipped pi commit gate currently always ALLOWS.** The extension's
   `subagent-stop` spawn passes `{cwd, tool_name:"Bash", tool_input:{command}}`.
   In the engine handler (`subagent_stop_handler._resolve_des_context`) this
   matches NEITHER protocol: it has no `executionLogPath/projectId/stepId` (the
   *direct* protocol) and no `agent_transcript_path` (the *Claude Code* protocol),
   so `des_context is None` → `{"decision":"allow"}`. The pi-harness gate is wired
   but inert for step-completion until a driving layer supplies DES context. This
   feature is exactly the layer that activates it.

A further engine fact decides HOW context is supplied without an engine change:
the direct protocol returns `effective_cwd = ""` (handler line 186), and
`SubagentStopService.validate()` runs commit verification only
`if context.cwd and self._commit_verifier` (service line 200). **The direct
protocol therefore validates phase completeness but SKIPS commit verification.**
Making the direct protocol honor a `cwd` field would be an `src/des/**` change →
forbidden by K2. The Claude Code protocol, by contrast, reads `cwd` from the hook
input and (line 204) sets `effective_cwd = cwd`, enabling the full
phase-completeness + `Step-Id`/`Task-Id` commit check — provided DES context is
present in an `agent_transcript_path`.

## Decision

### D-PKT-1 — Driving / bootstrap mechanism: hybrid (registered command bootstraps, skill drives)
A pi **registered command** (via the extension's `pi.registerCommand`, e.g.
`kata`/`deliver-kata`) performs the deterministic bootstrap: resolve a kata id,
run `des-init-log`, write a lightweight **kata manifest** + a **deliver-session
marker**, then hand control to the crafter skill which drives the cycle and
records phases. Rationale: a single agent cannot be relied on to run multi-step
bootstrap from prose alone (reliability risk R-PKT-1); a command makes
bootstrap deterministic and idempotent, while the skill owns the open-ended TDD
loop. The skill is reused (ADR-PI-003); the command is new behavior inside the
**already-shipped extension** (EXTEND, not a new artifact). See alternatives.

### D-PKT-2 — Self-decomposition + step-id origin: convention + manifest, no roadmap.json
The crafter self-decomposes the kata into one-test-per-step increments using the
3-phase canon discipline from `nw-tdd-methodology` (no architect, no
`roadmap.json` — explicitly out of scope per the feature delta). `project-id`
= the kata id (kebab-case, e.g. `fizzbuzz`), written once by the bootstrap
command into the kata manifest. `step-id` follows the existing `NN-NN`
convention: a single kata slice `01`, incrementing the second field per tiny
test (`01-01`, `01-02`, …). The crafter reads the current step-id from the
manifest, increments it at each new RED, and records it via `des-log-phase`. The
manifest is the single source of `(project-id, current step-id, deliver-dir)` for
both the skill (recording) and the commit gate (verification context).

### D-PKT-3 — Phase-recording reachability: reuse the install-time resolved interpreter + PYTHONPATH
`des-init-log` / `des-log-phase` are reached exactly as the extension already
reaches the adapter: the **install-time-resolved** absolute python path
(`resolve_python_command_for_spawn`) + `PYTHONPATH` to the DES lib
(`resolve_des_lib_path_for_spawn`), invoked as
`python -m des.cli.init_log …` / `python -m des.cli.log_phase …`. The bootstrap
command and the recording instructions use these resolved values (rendered into
the extension template / a thin recorded marker the plugin writes), NOT a bare
`des-init-log` console script on PATH (console-script availability post-wheel is
unconfirmed and environment-dependent) and NOT this repo's dev form
(`PYTHONPATH=src .venv/bin/python -m des.cli.<mod>`). This mirrors the proven
adapter-spawn path and reuses the same `install_paths` resolvers — zero new
reachability mechanism.

### D-PKT-4 — Commit-boundary context: synthesized transcript via the Claude Code protocol (zero engine change)
At the `git commit` boundary the extension already routes to `subagent-stop`. To
make the **shipped** gate validate the right step WITH commit verification and
WITHOUT an engine change, the extension supplies DES context through the
engine's **existing Claude Code protocol**: it writes a minimal one-line JSONL
**synthesized transcript** to a temp file whose `message.content` carries the
markers the engine already parses —
`<!-- DES-VALIDATION : required -->`, `<!-- DES-PROJECT-ID : {kata} -->`,
`<!-- DES-STEP-ID : {NN-NN} -->`, and `<!-- DES-PROJECT-ROOT : {project cwd} -->`
— and passes `{agent_transcript_path, cwd}` on the `subagent-stop` stdin. The
engine then resolves `effective_cwd = cwd`, reads phase events from the
manifest-located `execution-log.json`, and runs `GitCommitVerifier` for
`Step-Id`/`Task-Id` — exactly as in Claude Code. `project-id` doubles as
`Task-Id` (engine convention, service line 199-205). The marker values come from
the kata manifest. This is the ONLY way to get full commit verification at the pi
boundary under K2; the direct protocol cannot (it skips the commit check).

## Alternatives Considered

### D-PKT-1 alternatives
- **(b) Skill-only** — the crafter skill contains both bootstrap and cycle
  instructions, invoked via `/skill:software-crafter`. Pros: zero command
  surface, purest reuse of ADR-PI-003, most idiomatic to "a skill is a capability
  package". Cons: bootstrap is multi-step (init-log + manifest + marker) and a
  single agent skipping or fumbling one prose step strands the whole session
  unrecorded (the exact reliability risk the feature exists to remove). Rejected
  as primary; its cycle+recording instructions are still reused inside the hybrid.
- **(c) Command-only** — the command also drives the cycle. Rejected: the TDD
  loop is open-ended and model-driven; encoding it in a command duplicates the
  crafter skill and drifts from the canonical crafter source of truth.
- **(a, chosen) Hybrid** — command bootstraps deterministically, skill drives.
  Best reliability + reuse balance.

### D-PKT-4 alternatives
- **Direct DES protocol** (`executionLogPath/projectId/stepId`) — simplest to
  emit, no transcript file. **Rejected**: returns `effective_cwd=""`, so the
  shipped service skips commit verification (`if context.cwd` guard). Honoring a
  `cwd` field in the direct branch is an `src/des/**` edit → violates K2.
- **Engine change to add `cwd` to the direct protocol** — explicitly out of
  bounds (K2). Flagged as the upstream issue to escalate IF the synthesized
  transcript proves unworkable, but the transcript route makes it unnecessary.
- **turn_end-only validation** — already rejected in ADR-PI-001 (block at
  turn_end unverified); unchanged here.
- **(chosen) Synthesized transcript via the Claude Code protocol** — reuses the
  engine's existing marker parser + cwd handling verbatim. Zero engine change.

### Decision matrix (D-PKT-4)

| Criterion | Direct protocol | Engine `cwd` add | Synth transcript (chosen) |
|-----------|-----------------|------------------|---------------------------|
| Commit verification fires | No (cwd empty) | Yes | **Yes** |
| Zero `src/des/**` change (K2) | Yes | **No** | **Yes** |
| Reuses existing engine paths | Partial | n/a | **Yes (marker parser + cwd)** |
| Phase-completeness validated | Yes | Yes | **Yes** |

## Consequences
- Positive: full step-completion + commit verification at the pi commit boundary
  with ZERO engine change; provenance byte-identical to Claude Code (same
  markers, same `GitCommitVerifier`, same audit events).
- Positive: bootstrap is deterministic and idempotent (command), the cycle stays
  with the canonical crafter skill (reuse), recording rides the proven spawn path.
- Positive: the feature is what finally *activates* the shipped-but-inert pi
  commit gate (the always-allow gap above) — closing the original DoD.
- Negative: the extension now writes a transient transcript file and a manifest;
  both are declared, bounded mutations (contract-shape `bounded-change`), and the
  transcript is the engine's own documented input format, not a new log format.
- Negative: the extension grows a `registerCommand` handler and a
  commit-context-assembly branch; both stay pure relays (no allow/block decision
  of their own) — enforced by the existing thin-translator AST/string test.
- Trade-off (sensitivity point): correctness of the commit gate now depends on
  the manifest's `(project-id, step-id, cwd)` being accurate at commit time. The
  manifest is written by the deterministic bootstrap and incremented by the
  crafter; a stale/missing step-id surfaces as a `COMMIT_NOT_VERIFIED` block (the
  engine's existing failure mode), which is safe (fail-closed inside the engine).

## Post-review hardening (Atlas review, 2026-06-24 — 3 HIGH resolved)

These tighten the design without changing any decision; they convert three
specification/robustness gaps the reviewer flagged into binding contracts.

- **H1 — SPIKE-PKT-001 is a HARD GATE, not "warranted".** DISTILL entry is BLOCKED
  until SPIKE-PKT-001 passes (the probe below). A passing SPIKE must produce a
  handoff artifact: the model-free adapter round-trip output + a git commit trace
  + an audit-log excerpt showing `COMMIT_VERIFIED` (complete log) and
  `COMMIT_NOT_VERIFIED` (incomplete log) — with `git diff --stat src/des/` empty.
  On failure: escalate the engine `cwd`-in-direct-protocol gap to the user as a
  K2 upstream issue; do NOT design the engine change.
- **H2 — Crafter decomposition intake is a behavioral contract (D-PKT-2 refinement).**
  The kata problem reaches the crafter as a structured intake (problem statement
  + optional expected step-count hint), NOT free prose alone. Before the first
  RED, the crafter MUST produce a step-decomposition plan (each step ≤ ~20 lines,
  one observable behavior, semantically independent) and record it in the kata
  manifest. Behavioral AC for DISTILL (WHAT, not HOW): *"Given a kata problem,
  the crafter produces an ordered step-decomposition plan recorded in the
  manifest before authoring the first RED test, and each subsequent step's RED
  exercises exactly one increment of that plan."* Worked anchor: FizzBuzz →
  `01-01` returns 1, `01-02` returns 2, `01-03` fizz for 3, `01-04` buzz for 5,
  `01-05` fizzbuzz for 15 (refactor folded into COMMIT).
- **H3 — Manifest write robustness (D-PKT-2 / KD4 safety).** Manifest updates use
  write-temp-then-atomic-move; after each step-id increment the crafter re-reads
  the manifest and asserts the new step-id is present before the next RED. A
  partially-written / stale manifest must surface as a blocked commit
  (`COMMIT_NOT_VERIFIED` from the engine when the trailer step-id and the
  validated step disagree), never as a silent allow. DELIVER adds an observation
  test: a manually-reverted manifest step-id mid-kata causes the next commit to
  block.

## Probe / Earned-Trust note (Principle 13)
The single make-or-break empirical unknown is **D-PKT-4**: does the shipped
engine, fed a synthesized one-line transcript with the four markers + `cwd`,
actually run `GitCommitVerifier` and block an incomplete step / allow a complete
one — model-free, via a direct `subagent-stop` subprocess round-trip? This is
cheaply probeable WITHOUT a pi model backend (a python subprocess test against
the unchanged adapter, mirroring SPIKE-0 Half-1). A timeboxed SPIKE is
**warranted** before DELIVER commits to the transcript route. One probe question:
*"Given a synthesized transcript carrying DES-VALIDATION/PROJECT-ID/STEP-ID/
PROJECT-ROOT and a `cwd` on a real temp git repo with a complete vs incomplete
execution-log, does the unchanged `subagent-stop` adapter return allow vs block
with COMMIT_VERIFIED / COMMIT_NOT_VERIFIED — with zero `src/des/**` change?"*
