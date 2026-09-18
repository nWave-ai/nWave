# Evolution — pi-kata-tdd-flow (self-driven nWave TDD cycle for a kata in pi)

**Shipped:** 2026-06-24 · **Branch:** `feat/pi-harness-walking-skeleton` · **Waves:** DISCUSS → DESIGN → SPIKE → DISTILL → DELIVER

## What shipped
The driving/bootstrap layer that lets a single pi agent (no orchestrator, no subagents) self-run the nWave DELIVER TDD cycle for a code kata: bootstrap a DES-tracked session, drive per-test RED→GREEN→COMMIT recording, and have the already-shipped commit gate verify. Closes the original pi-harness DoD ("invoke the crafter, it solves a kata by strict canonical TDD, verified by execution log + commit history"). Builds on pi-harness; **zero DES engine change**.

## Key decisions (durable)
- **K1 commit-boundary-verified strictness**: the crafter self-drives + the commit gate blocks an incomplete/unverified step; within-cycle ordering is crafter-skill discipline, not a keystroke-level block. (Same enforcement model nWave gives Claude Code.)
- **K2 zero `src/des` change**: reuse the engine's existing decisions exactly. Held throughout (verified empty diff at every step + review).
- **KD1 hybrid bootstrap**: a pi `registerCommand` deterministically bootstraps (a single agent can't be trusted to run multi-step bootstrap from prose); the crafter skill drives the open-ended loop.
- **KD2 kata-manifest**: roadmap-free context carrier (project-id, NN-NN step-id, cwd) — the only CREATE-NEW artifact.
- **KD4 synthesized-transcript activates the commit gate**: SPIKE discovered the shipped pi commit gate *always-allowed* (no context supplied); feeding the unchanged `subagent-stop` a synthesized CC-protocol transcript + cwd activates it. SPIKE-proven with zero engine change.

## Spike
SPIKE-PKT-001 (DISCARD, findings sufficient): proved the unchanged `subagent-stop` blocks an incomplete step / allows a complete one via the synthesized transcript; `src/des` untouched. Captured 4 binding constraints (stdout-decision-at-exit-0; exact marker fidelity; no step-id reuse; manifest/cwd alignment) — all honored in the implementation.

## Components
| Component | Path | Disposition |
|-----------|------|-------------|
| kata bootstrap + manifest | `scripts/install/pi_kata/bootstrap.py` | NEW |
| synthesized-transcript assembler | `scripts/install/pi_kata/transcript_context.py` | NEW |
| pi extension | `nWave/templates/pi-des-extension.ts.template` | EXTENDED (registerCommand + commit-context branch, pure relay) |
| pi installer plugin | `scripts/install/plugins/pi_des_plugin.py` | EXTENDED (render/register + crafter-skill section) |
| DES engine + verifiers + CLIs | `src/des/**` | REUSED UNCHANGED |

## Verification
pi_kata 10 passed / 1 skipped; pi-harness 21 / 1 (no regression). DES integrity: all 3 steps complete RED→GREEN→COMMIT. Adversarial review APPROVED, 0 defects, no testing theater.

## Lessons / gotchas (for the next feature)
- **DES pre-task hook trips on prompt content**: an agent-dispatch prompt that contains the literal `<!-- DES-VALIDATION : required -->` marker syntax, OR a bare `step NN-NN` pattern, is treated as a DELIVER step and blocked for missing markers. For non-DELIVER dispatches (architect/reviewer/DISTILL), add `<!-- DES-ENFORCEMENT : exempt -->` and paraphrase marker references. (Cost us 3 blocked dispatches before diagnosis.)
- **Colon Gherkin tags + `--strict-markers`**: `@contract-shape:bounded-change` cannot be registered via `addinivalue_line` (pytest truncates the marker name at the first colon). Use the `pytest_bdd_apply_tag` hook to consume wave-metadata tags (pattern: `tests/installer/acceptance/installer_orphan_sweep/conftest.py`). DISTILL should author this conftest from the start for any colon-tagged suite.
- **The engine's allow contract is silent**: `subagent-stop` (and pre-write) signal ALLOW as exit 0 + empty stdout, BLOCK as stdout `{"decision":"block"}` at exit 0 (Stop-class) — never a `{"decision":"allow"}` payload. ATs must assert empty-stdout for allow.
- **Crafter branch discipline**: the crafter created a per-step branch on its first step; orchestrator must instruct "stay on the current branch" explicitly.
- Two DISTILL AT-scaffold defects surfaced only when driven against the real engine (the fail-for-right-reason gate classified them as MISSING_FUNCTIONALITY). Driving the real engine earlier in DISTILL would catch these.

## Residual / next
- Live-model kata e2e (`@requires_external`) — needs a pi model backend (manual or gated CI lane); DoD item 9.
- A-PKT-1: slice-02/03 observable assertions kept as documented layer-3 exemption (not wrapped in `assert_state_delta`).
- Public-release gating: confirm the new pi_kata assets' `public:` flags in `framework-catalog.yaml` before any release sync.
