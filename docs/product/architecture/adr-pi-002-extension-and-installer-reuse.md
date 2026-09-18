# ADR-PI-002: pi extension is a thin translator extending the committed skeleton; installer mirrors the OpenCode plugin

## Status
Accepted (2026-06-23). Confirms D5 (thin TS translator, zero adapter fork) at the
DESIGN level and resolves the build-vs-reuse question for the extension and the
installer plugin.

## Context
A walking-skeleton pi extension is already committed
(`nWave/templates/pi-des-extension.ts.template`) and proven loading into real pi
0.79.9 by a model-free acceptance test. The Codex and OpenCode DES plugins
(`codex_des_plugin.py`, `opencode_des_plugin.py`) establish the
validate→install→verify→uninstall + `.nwave-des-manifest.json` precedent, and
`scripts/shared/install_paths.py` provides the interpreter/lib resolvers all
spawn-based shims must reuse (SPIKE implication 5).

## Decision
- **EXTEND** the committed extension template rather than create a new one. Add
  `tool_result` and `turn_end` subscriptions, cycle-state-driven action
  selection, and the mandatory `DES_AUDIT_LOG_DIR` pin. The extension remains a
  pure protocol translator: it relays the engine's exit-code-2 + `reason` and
  contains no allow/block decision logic of its own.
- **CREATE NEW** `scripts/install/plugins/pi_des_plugin.py` by mirroring
  `opencode_des_plugin.py` (it is the closest analog — a TS file rendered from a
  template into a harness config dir, vs Codex's hooks.json JSON-merge). Reuse
  `resolve_python_command_for_spawn` / `resolve_des_lib_path_for_spawn`, the
  `.nwave-des-manifest.json` shape, and the skip-silently-if-pi-absent pattern.
- **REUSE** `claude_code_hook_adapter`, `GitCommitVerifier`, `ExecutionLogReader`,
  `JsonlAuditLogWriter`, `activation_gate`, and the `PluginRegistry` unchanged.

## Alternatives Considered
- **Fork the Python adapter for pi** — rejected outright by D5 and the
  resume-driven/maintainability critique: it would create a second enforcement
  engine to keep in sync. No requirement justifies it.
- **Mirror the Codex plugin instead of OpenCode** — rejected: Codex wires a
  JSON `hooks.json` entry pointing at the adapter directly; pi (like OpenCode)
  loads a rendered TS file from a config location, so the OpenCode plugin's
  render-template-then-install-file shape is the correct mould. (Codex remains a
  reference for the manifest and resolver reuse.)
- **Generate a fresh extension from scratch in the plugin** — rejected: the
  committed skeleton is a fait accompli and already passes a real-pi test;
  extending it preserves that proof.

## Consequences
- Positive: maximum reuse; one enforcement engine; install/uninstall consistency
  across all four harnesses; the skeleton's passing test stays green.
- Positive: `pi_des_plugin.py` depends on `des` and the pi skills plugin
  (see ADR-PI-003), so the registry's topological sort installs them in order.
- Negative: the extension grows beyond the skeleton; bounded by the
  thin-translator enforcement test (no allow/block decision literal beyond
  relaying engine exit-code-2 + `reason`) and a ~150-LoC budget for the full gate
  set (tool_call, tool_result, turn_end, state read, DES_AUDIT_LOG_DIR pin,
  health line, fail-open handlers).
- Open: pi's exact extension-install location is unconfirmed (R1); the plugin
  states its assumption explicitly, emits a **non-fatal warning** when the pi
  config dir is absent (rather than silent skip), and flags it for DEVOPS
  verification.
