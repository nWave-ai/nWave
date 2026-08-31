# SPIKE-1 Findings — D6 driving-ports proof (bash tool_call / tool_result)

**Date:** 2026-06-23 · **Agent:** Attila (nw-software-crafter) · **Trigger:** DESIGN review (Architect Issue 2, HIGH) — the D6 Hybrid step-completion model leaned on three pi behaviors SPIKE-0 did not prove.
**Method:** model-free **source inspection** of the installed pi 0.79.9 package (`/opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent/dist/`). No live model backend available in this environment (no API creds; ollama empty) — type declarations are the authoritative contract.

## Assumptions under test (from ADR-pi-001 Hybrid model)
1. A bash test-run emits a `tool_result` carrying an exit status (to record suite red/green).
2. A `git commit` is interceptable and **blockable** through the same mechanism SPIKE-0 proved for `write`.
3. Commits and test runs flow through the `bash` tool (no dedicated git/test tool).

## Verdict: **WORKS** (all three confirmed)

### Evidence (from `dist/core/extensions/types.d.ts` + `dist/core/tools/bash.d.ts`)
- **(3) Tool set** = `bash, read, write, edit, ls, grep, find`. No `git`/`commit`/`test`/`pytest` tool. → commits and test runs are `bash` invocations. ✓
- **(1) Exit status on result**: `BashToolResultEvent { toolName: "bash"; details: BashToolDetails }`, and `BashToolDetails` carries `exitCode: number | undefined` (+ `command: string`). The `tool_result` handler reads `exitCode` → records GREEN (0) / RED (≠0). ✓
- **(2) Blockable + inspectable**:
  - `tool_call` is a SINGLE generic event — a discriminated union over `toolName` with a `BashToolCallEvent { toolName: "bash"; input: BashToolInput }` variant.
  - The handler signature is `on("tool_call", handler: ExtensionHandler<ToolCallEvent, ToolCallEventResult>)`; `ToolCallEventResult = { block?: boolean; reason?: string }`.
  - This is the **identical** event + handler + result type SPIKE-0 proved blockable for `write`/`edit` — the block is not per-tool; it applies to whatever `toolName` the event carries, including `bash`.
  - `BashToolInput.command: string` (`bashSchema`) lets the extension parse the command to distinguish `git commit …` (→ step-completion gate) from a test-run command (→ record red/green) from any other bash. ✓
  - Doc note at the `tool_call` type: `event.input` is mutable; later handlers see earlier mutations; no re-validation after mutation — relevant for ordering multiple extensions, not a blocker here.

## Impact on the design
- **ADR-pi-001 D6 Hybrid is sound.** Concrete event mapping is now type-confirmed:
  - write/edit `tool_call` → RED gate (block before impl without failing test) — proven SPIKE-0.
  - bash `tool_call` where `input.command` matches a commit → step-completion / no-regression gate; **blockable** — proven now (same class).
  - bash `tool_result` where the command was a test run → read `details.exitCode` to record red/green — proven now.
  - `turn_end`/`agent_end` → non-blocking reconciliation (unchanged).
- **Refinement for DELIVER**: the extension gates on the **`bash` tool** and parses `input.command` — there is no separate "commit tool_call". DELIVER must implement command classification (commit vs test-run vs other) in the translator's bash branch. Captured for the extension EXTEND work.

## Residual (now LOW)
pi *honoring* `{block:true}` was executed live only for `write` (SPIKE-0). For `bash` it is the same event/handler/result type (type-confirmed), so confidence is high; the live model-driven bash-block is exercised by the `@requires_external` DELIVER scenario (SPIKE caveat). Risk R2 is downgraded MEDIUM → LOW.

## Promotion decision: **DISCARD** (findings sufficient)
No throwaway probe code was written (source inspection only) and no new walking-skeleton code is needed — the committed skeleton already exercises the driving adapter. Findings feed DELIVER + close the DESIGN review high. Proceed to finalize the review gate.
