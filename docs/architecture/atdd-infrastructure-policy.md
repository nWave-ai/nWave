# ATDD Infrastructure Policy

Per `nw-distill` § Project Infrastructure Policy. One file per project. Apply-if-exists; write-if-absent; rewrite with `--policy=fresh`. Git history is the audit trail.

The Architecture of Reference fixes the port CLASS → test TREATMENT (real vs fake). This file records the concrete MECHANISM each treatment uses in THIS codebase.

## Driving
| Port | Mechanism | Note |
|---|---|---|
| pi extension load (bare interactive) | subprocess `pi --no-extensions -e <rendered-ext> --offline --no-session --no-tools -p "noop"` from a tmp project with `.nwave/local-config.json:{enabled_for_repo:true}` | Walking skeleton driving adapter; skips when `pi` binary absent (SPIKE-0 CI caveat). |
| pi installer plugin lifecycle | `PiDESPlugin().validate_prerequisites/install/verify/uninstall` over an `InstallContext` against a tmp pi config dir (`PI_CONFIG_DIR` override) | Mirrors `OpenCodeDESPlugin`; model-free, real filesystem I/O. |
| pi event translation (rendered extension) | direct `python -m des.adapters.drivers.hooks.claude_code_hook_adapter <action>` round-trip with constructed Claude-Code-shaped payloads, OR the rendered extension's `mapTool`/action-selection asserted by string/AST inspection | Model-free deterministic exercise of the translator contract (SPIKE-0 Half-1 pattern); no LLM turn. |

## Driven internal (real)
| Port | Mechanism | Note |
|---|---|---|
| Rendered-template filesystem install (pi config dir) | real `tmp_path` pi config dir; template rendered, manifest written, artifacts read back | `@real-io @adapter-integration`; the only writer the plugin owns (bounded-change). |
| Python DES adapter (`claude_code_hook_adapter`) | REUSED UNCHANGED — exercised via real subprocess round-trip (`pre-write` / `subagent-stop`) | Sole authoritative writer of phase/audit records; pi adds no new writer. Existing DES suite owns its contracts. |

## Driven external / non-deterministic (fake / skip)
| Port | Fake | Note |
|---|---|---|
| pi LLM backend (model turn) | skip via `@requires_external` | No model backend in CI (SPIKE-0 constraint). Live "pi honors `{block:true}` during a model turn" is a documented pi contract, asserted model-free at the adapter round-trip + manual gated e2e. |
