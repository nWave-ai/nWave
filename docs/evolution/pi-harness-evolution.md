# Evolution — pi-harness (nWave software-crafter on the pi coding agent)

**Shipped:** 2026-06-24 · **Branch:** `feat/pi-harness-walking-skeleton` · **Waves:** DISCUSS → SPIKE-0 → DESIGN → DISTILL → SPIKE-1 → DELIVER

## What shipped
pi (pi.dev) is now a fourth nWave harness (after Claude Code, Codex, OpenCode). The nWave installer wires DES TDD enforcement into pi via a thin TS extension that relays verdicts from the unchanged Python DES engine. Scope was deliberately thin (D7): one agent (software-crafter), DELIVER-only, reused engine.

## Key decisions (durable)
- **D5 / zero adapter fork**: the pi extension is a pure protocol translator → existing `claude_code_hook_adapter`. One canonical enforcement engine across all harnesses. `src/des/**` unchanged.
- **D6 Hybrid (ADR-pi-001)**: pi has no `SubagentStop`, so step-completion re-grounds on the `git commit` bash `tool_call` boundary (relaying the unchanged `subagent-stop` validation); within-cycle RED on write/edit `tool_call`; suite red/green on bash test-run `tool_result`; `turn_end` non-blocking. The pivot: `SubagentStopService.validate()` was already a pure function of `(execution_log, project_id, step_id, cwd)` — the subagent boundary was only its trigger.
- **Commits & tests run through pi's `bash` tool** (no dedicated git/test tool) — the translator classifies by `input.command` (SPIKE-1).

## Spikes (de-risking)
- **SPIKE-0** (WORKS, promoted): proved pi's `tool_call` can block + reach the Python adapter; produced the walking skeleton.
- **SPIKE-1** (WORKS, source-inspection): confirmed pi 0.79.9 types — bash `tool_call` is the same blockable event class as write, `BashToolInput.command` inspectable, `tool_result` carries `exitCode`. Resolved the DESIGN-review HIGH on unproven driving ports.

## Components
| Component | Path | Disposition |
|-----------|------|-------------|
| pi installer plugin | `scripts/install/plugins/pi_des_plugin.py` | NEW (mirrors `opencode_des_plugin.py`) |
| pi DES extension | `nWave/templates/pi-des-extension.ts.template` | NEW→EXTENDED (thin translator) |
| Plugin registration | `scripts/install/install_nwave.py` | EXTENDED |
| Python DES engine + verifiers + audit | `src/des/**` | REUSED UNCHANGED |

## Verification
21 passed / 0 failed / 1 skipped (`@requires_external` live model). DES integrity: all 3 steps complete RED→GREEN→COMMIT. Adversarial review APPROVED, 0 defects, no testing theater.

## Residual / next slices
- Live-model kata e2e (`@requires_external`) — needs a pi model backend; run manually or in a gated CI lane (DoD item 9).
- pi config-dir location (R1) — plugin uses `PI_CONFIG_DIR` override + `~/.pi/agent` default with a non-fatal warning; confirm in a real pi install / DEVOPS.
- Outcomes registry `OUT-PI-1` deferred (schema.json absent).
- Public-release gating: confirm pi assets' `public:` flags in `framework-catalog.yaml` before any release sync.
