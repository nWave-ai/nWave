# SPIKE-0 Findings — pi `tool_call` interception + DES adapter bridge

**Date:** 2026-06-23 · **Agent:** Attila (nw-software-crafter) · **Probe location:** `/tmp/claude-501/spike_pi-harness/` (throwaway)
**pi version:** 0.79.9 (`@earendil-works/pi-coding-agent`, homebrew) · **Python:** project `.venv` 3.14

## Assumption tested (single)
Can a pi extension intercept a `tool_call`, **block** a production-code write (`{block:true,reason}`), and invoke the existing Python DES adapter (`des.adapters.drivers.hooks.claude_code_hook_adapter`) via subprocess using the Claude Code JSON hook protocol — landing an entry in the existing DES JSONL audit log?

## Verdict: **WORKS**

The mechanism is validated. The two integration-risky halves were executed for real; the only piece not executed end-to-end (pi honoring `{block:true}` during a live model turn) is a first-class **documented** pi contract, not an unknown — and was not reachable here only because no LLM backend is configured in this environment.

## Evidence

### Half 1 — adapter subprocess + CC JSON protocol + audit log (executed)
- Invoked `python -m des.adapters.drivers.hooks.claude_code_hook_adapter pre-write` with a Claude-Code-shaped payload on stdin:
  `{"cwd":".../spike_pi-harness","tool_name":"Write","tool_input":{"file_path":".../execution-log.json","content":"x"}}`
- Result: **exit code 2** + stdout `{"decision":"block","reason":"Direct creation of execution-log.json is blocked..."}`.
- Audit log written: `auditlogs/audit-2026-06-23.log` →
  `{"event":"HOOK_PRE_WRITE_BLOCKED","file_path":".../execution-log.json","reason":"execution_log_direct_write","timestamp":"2026-06-23T08:42:45..."}`.

### Half 2 — bridge runs inside the real pi runtime (executed)
- Wrote a pi extension (`des-enforce.ts`) subscribing to `session_start` (self-probe) and `tool_call` (gate).
- Loaded into real pi: `pi --no-extensions -e des-enforce.ts --offline --no-session --no-tools -p "noop"` → **pi exit 0**.
- The `session_start` handler spawned the Python adapter **from within pi's runtime** and wrote `self-probe-result.json`:
  `{"bridge":"ok","exitCode":2,"blocked":true}`.
- A **second** distinct audit entry (hook_id `55bbdd45…`, ts `08:43:34`) confirms the in-pi invocation reached the real audit writer.

### Half 3 — pi honors `{block:true}` from `tool_call` (NOT executed; documented contract)
- pi docs: the `tool_call` event "Fired after `tool_execution_start`, before the tool executes. **Can block.**" Handler returns `{ block: true, reason }`; official example blocks `write` to `.env` paths.
- Not exercised here because driving a real `write` tool call needs an LLM turn, and no provider/API key/local model is available in this sandbox (default provider model unresolved; ollama has no pulled models).

## Timing
Mechanism validation only (no perf budget). Subprocess round-trip was sub-second interactively; not formally benchmarked. Note for DESIGN: pi's tool timeout applies to `tool_call` handlers — keep the adapter cold-start fast (the install-time `lib/python/des` + resolved interpreter path, as Codex/OpenCode already do).

## Design implications (for DESIGN)
1. **Enforcement entry = `tool_call`** (PreToolUse analog), **notifications = `tool_result`** (PostToolUse analog). Both confirmed available in pi.
2. **Activation gate is real and required.** The adapter exits 0 (allow) unless the project is active. Activation marker that worked: `.nwave/local-config.json` → `{"enabled_for_repo": true}` (per `activation_policy.resolve_activation`). The pi extension must run inside an activated project for gating to engage.
3. **Audit dir resolution.** `JsonlAuditLogWriter` defaults to `Path.cwd()`-relative `.nwave/des/logs/` (or `~/.claude/des/logs/` fallback). The pi extension MUST pin the project-correct dir — `DES_AUDIT_LOG_DIR` worked deterministically. Otherwise entries land in the process cwd, not the user's project.
4. **Zero adapter fork holds (D5).** The extension is a thin TS translator → existing Python adapter, unchanged. Mirrors the OpenCode shim exactly.
5. **Interpreter/lib resolution.** The probe hardcoded the repo venv + `PYTHONPATH=src`. Production must reuse the installer's `resolve_python_command_for_spawn` / `resolve_des_lib_path_for_spawn` (as Codex/OpenCode plugins do).
6. **D6 still open.** This spike only exercised the `pre-write` gate. The full RED→GREEN→REFACTOR step-completion logic (the `SubagentStop` analog) is unproven and remains a DESIGN decision — likely re-grounded on commit boundaries / `turn_end` / `agent_end`.
7. **CI caveat.** A live end-to-end pi-honors-block test needs a model backend. Recommend a model-free acceptance test (extension-loads + bridge-blocks via the self-probe / direct adapter round-trip) plus a manual/optional gated e2e with a real model.

## Constraints discovered
- No LLM backend in this environment (no API key; ollama empty) → live model-driven tool calls not runnable here.
- pi writes settings/session under `~/.pi/agent/` (needs write access; was blocked under the command sandbox, ran with sandbox disabled).
- `$TMPDIR` differs between sandboxed and sandbox-disabled shells — use literal absolute probe paths.

## Promoted on
2026-06-23 — PROMOTE. Walking skeleton committed: real nWave pi extension template
(`nWave/templates/pi-des-extension.ts.template`) loaded into **real pi 0.79.9** by a
`@walking_skeleton @driving_port` acceptance test
(`tests/des/acceptance/pi_harness/walking-skeleton.feature`) that asserts the
`[nWave DES] enforcement active for pi` health line — proving pi → extension →
Python DES adapter end-to-end, model-free. Probe dir deleted.
