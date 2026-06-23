# DESIGN Decisions — pi-harness

> nw-solution-architect (Morgan), PROPOSE mode, 2026-06-23.
> Continues numbering from DISCUSS/SPIKE (D1–D7). Headline: D8 (D6 resolution).

## Key Decisions

| ID | Decision | Verdict | One-line rationale |
|----|----------|---------|--------------------|
| D8 | Step-completion model = **Hybrid** (Option C): `tool_call` gates within-cycle ordering; `git commit` `tool_call` boundary triggers the unchanged `subagent-stop` step-completion validation; `turn_end` reconciles read-only | LOCKED | Resolves D6. `SubagentStopService` is a pure validation over (log, project, step, cwd) — only the trigger cadence changes; commit `tool_call` is the proven-blockable boundary. ADR-PI-001. |
| D9 | Crafter skill **content reused** from `nWave/skills`; contributed via the extension's `resources_discover`; placed by the DES plugin (no dedicated `pi_skills_plugin.py` for the thin slice) | LOCKED | One canonical crafter; minimal install surface; promote to a skills plugin only when pi scope grows past crafter (D7). ADR-PI-003. |
| D10 | pi extension = **EXTEND the committed skeleton** to the full gate set; stays a pure translator (no decision logic) | LOCKED | D5 zero-fork; keep the skeleton's passing real-pi test green. ADR-PI-002. |
| D11 | Installer plugin **CREATE NEW** `pi_des_plugin.py` mirroring `opencode_des_plugin.py` (render→install→manifest→verify→uninstall); reuse `install_paths` resolvers | LOCKED | OpenCode is the closest analog (rendered TS file into a config dir). ADR-PI-002. |
| D12 | Suite state (red/green/regression) captured at the bash test-run `tool_result` and recorded via the existing DES phase CLI — **no new log format** | LOCKED | Honors D3; same surface Claude Code crafter uses. |
| D13 | `DES_AUDIT_LOG_DIR` pinned to project `.nwave/des/logs` on every spawn; activation via `.nwave/local-config.json` resolved by the existing Python gate | LOCKED | SPIKE implications 2 & 3; mandatory, not optional. |
| D14 | No external network integrations → **no contract tests** required for this feature | LOCKED | Only "external" surface is pi itself, exercised model-free per SPIKE-0. |

## Architecture Summary

pi-harness adds the nWave software-crafter to pi (v0.79.9, Node) as a skill and
enforces full RED→GREEN→REFACTOR TDD using the **unchanged Python DES engine**.
The only new code is protocol-translation TypeScript (extending the committed
skeleton) and a Python installer plugin. Enforcement rides three pi `tool_call`
boundaries — production write/edit (RED), test-run result (suite state), and
`git commit` (step completion, triggering the existing `subagent-stop`
validation) — with a non-blocking `turn_end` reconciliation. All three
verification surfaces (JSONL audit log, Step-Id/Task-Id commit trailers,
execution-log phase events) are reused byte-compatibly with Claude Code.

C4 L1 (System Context) and L2 (Container) are in
`docs/product/architecture/brief.md#application-architecture`. No L3 component
diagram: the enforcement "state machine" is intentionally not a new component —
it is the existing Python `SubagentStopService`/`StepCompletionValidator`
re-triggered, so a component diagram would duplicate the container view.

## Reuse Analysis (HARD GATE)

| Existing component | Verdict | Justification |
|--------------------|---------|---------------|
| `opencode_des_plugin.py` | EXTEND (as mould → new file) | Closest analog (rendered TS → config dir). New `pi_des_plugin.py` mirrors its structure; cannot literally extend (different harness paths/filenames). |
| `codex_des_plugin.py` | REUSE (reference) | Manifest shape + resolver-reuse reference; not the structural mould (JSON-merge vs file-render). |
| `pi-des-extension.ts.template` | EXTEND | Committed skeleton; add tool_result/turn_end + action selection + DES_AUDIT_LOG_DIR pin; stays a translator. |
| `claude_code_hook_adapter` + handlers (`pre_write`, `post_tool_use`, `subagent_stop`) | REUSE (unchanged) | Zero fork (D5). The subagent-stop handler is invoked at the commit boundary; its validation is subagent-independent. |
| `SubagentStopService` / `StepCompletionValidator` / `GitCommitVerifier` | REUSE (unchanged) | Pure step-completion validation; the engine of D6. |
| `JsonlAuditLogWriter` | REUSE (unchanged) | Dir pinned via `DES_AUDIT_LOG_DIR` (D13). |
| `activation_gate` / `activation_policy` | REUSE (unchanged) | Dormant-unless-activated semantics; extension does not re-implement. |
| `install_paths.resolve_*_for_spawn` | REUSE | Mandatory for interpreter/lib resolution (SPIKE impl. 5). |
| `PluginRegistry` + `base.InstallationPlugin` | REUSE | Register `pi-des` with deps `["des", <skill placement>]`; topological order. |
| `opencode_skills_plugin.py` | NOT REUSED NOW (deferred) | Single crafter skill placed by the DES plugin; promote to `pi_skills_plugin.py` only when ≥2 skills enter pi scope (D9, evidence-gated CREATE NEW). |
| `opencode_agents_plugin.py` | NOT REUSED | D1/D7: crafter is a skill, no agents in pi. |

## Contract Shape Classification (Principle 12)

| Component | Shape | Universe | Mechanism |
|-----------|-------|----------|-----------|
| pi event translator (TS) | pure-function (event+state → Decision) | reads cycle-state + event; writes none of its own | thin-translator AST/string test; ~150 LoC budget |
| cycle-state reader (TS) | pure-function (state → action enum) | reads `.nwave/des/*`; writes none | unit assertion: no writes |
| DES adapter + services (Py, unchanged) | unbounded-preservation | reads execution-log + git + config; writes audit + phase records | existing DES suite (sole authoritative writer) |
| pi installer plugin (Py) | bounded-change | writes pi config: extension + skill + manifest only | manifest install→verify→uninstall reconciliation |

The translator exposes no write capability; the Python engine is the sole
authoritative writer. Full table + rationale in `brief.md#contract-shape-classification`.

## Tech Stack

- pi 0.79.9 (`@earendil-works/pi-coding-agent`), Node runtime, TypeScript extension.
- Python DES engine — unchanged.
- Installer plugin — Python (OOP, project standard).
- No new third-party deps; no proprietary tech; no external integrations.

## Constraints (carried + added)

- D5 zero adapter fork (carried, reaffirmed by D10/D11).
- D3 reuse existing verification surfaces (carried, reaffirmed by D12).
- SPIKE: enforce on `tool_call`/`tool_result`; `.nwave/local-config.json`
  activation required; `DES_AUDIT_LOG_DIR` must be pinned; reuse spawn resolvers;
  pi on Node with `spawnSync` (carried into D13).
- Enforcement gate must ride a proven-blockable event (`tool_call`); `turn_end`
  block honoring is unverified → reconciliation only (added, R2).

## Upstream Changes

- **None to DISCUSS/SPIKE decisions.** D6 is resolved (was PROVISIONAL), not
  revised. No DISCOVER assumptions exist (greenfield).
- SSOT bootstrapped: `docs/product/architecture/brief.md` created with the
  `## Application Architecture` section; ADR-PI-001/002/003 added.

## Open Questions (deferred)

- **DISTILL/DELIVER**: exact pi `resources_discover` return shape (`skillPaths`)
  and pi's skill-directory expectation; confirm against pi 0.79.9 docs (R1).
- **DELIVER/DEVOPS verify**: pi's extension-install location (`~/.pi/agent/`
  git/npm vs local `.pi/` vs a `pi install`/`-e` settings registration). Plugin
  states its assumption; DEVOPS confirms (R1).
- **DISTILL**: acceptance scenarios for the commit-boundary block and the
  red→green→regression sequence must be model-free (SPIKE CI caveat, R4) — a
  direct adapter round-trip at the commit boundary + a manual gated model e2e.
- **DELIVER**: confirm pi honors `{block:true}` on the bash `git commit`
  `tool_call` specifically (proven for write/edit; same contract, exercise it).
