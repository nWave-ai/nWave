# SPIKE-0 — pi `tool_call` interception + DES adapter reachability

**Type:** timeboxed PROBE (pre-walking-skeleton). Run via `/nw-spike`.
**Timebox:** ≤ half a day.

## Goal
Prove the one make-or-break assumption: a pi extension can intercept a `tool_call`, **block** a production-code `write`, and invoke the existing Python DES adapter (`des.adapters.drivers.hooks.claude_code_hook_adapter`) via subprocess — exchanging the Claude Code JSON hook protocol.

## Core assumption under test
pi's `tool_call` lifecycle event fires before execution and a handler returning `{ block: true, reason }` actually prevents the file write, AND a Node subprocess can feed the adapter JSON-on-stdin and read its decision-on-stdout within pi's tool timeout.

## IN scope
- Minimal pi extension that subscribes to `tool_call`.
- On a `write`/`edit` to a marked path, shell out to the Python adapter with a hand-built PreToolUse JSON payload.
- Block or allow based on the adapter's stdout decision.
- Confirm an entry lands in the existing DES JSONL audit log.

## OUT scope
- The actual RED/GREEN/REFACTOR logic (slices 02–03).
- Skill loading / installer wiring (slice 01).
- Any UX polish.

## Learning hypothesis
**Disproves** the `tool_call`-based enforcement path if: the event cannot block, the block doesn't stop the write, the subprocess can't reach the adapter, or the round-trip exceeds pi's tool timeout. If disproved → DESIGN must find an alternative (e.g. `user_bash` gating, SDK-mode wrapper, or RPC-mode supervisor).

## Acceptance criteria
- A `write` to the marked path is demonstrably prevented (file unchanged) with a reason surfaced to the agent.
- A `write` to an allowed path proceeds.
- The adapter is invoked unmodified and its decision drives the outcome.
- One real audit-log entry is produced.

## Promote
If GREEN, the spike's extension skeleton + subprocess bridge promote directly into Slice 01 (walking skeleton). Use production paths/data, not synthetic stubs, for the promote step.

## Dependencies
pi installed; Python DES adapter + audit writer present (already in repo).
